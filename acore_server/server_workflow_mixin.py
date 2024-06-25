# -*- coding: utf-8 -*-

"""
This module implements all "Workflow" mentioned in :ref:`operation-and-workflow`.
"""

import typing as T
import dataclasses
import json
import time

from boto_session_manager import BotoSesManager
from s3pathlib import S3Path
from aws_console_url.api import AWSConsole
import simple_aws_ec2.api as simple_aws_ec2
import simple_aws_rds.api as simple_aws_rds

from .logger import logger
from .utils import get_utc_now, prompt_for_confirm
from .wserver_infra_exports import StackExports


if T.TYPE_CHECKING:  # pragma: no cover
    from .server import Server


@dataclasses.dataclass
class Workflow:
    """
    因为一个 workflow 在执行过程中会有多个步骤, 有些步骤可能会失败. 为了能在执行的过程中记录下
    执行的状态, 以便能在失败重试的时候从上一个成功的地方继续执行, 我们需要一个 Workflow 类来
    记录这些状态. 我选择将 Workflow 的数据保存在 S3 上.
    """

    workflow_id: str = dataclasses.field()

    def dump(self, bsm: BotoSesManager, s3_path: S3Path):
        s3_path.write_text(
            json.dumps(dataclasses.asdict(self)),
            bsm=bsm,
            content_type="application/json",
        )

    @classmethod
    def load(cls, bsm: BotoSesManager, s3_path: S3Path, workflow_id: str):
        if s3_path.exists(bsm=bsm) is False:
            workflow = cls(workflow_id=workflow_id)
            workflow.dump(bsm=bsm, s3_path=s3_path)
        else:
            workflow = cls(**json.loads(s3_path.read_text(bsm=bsm)))
            if workflow.workflow_id != workflow_id:
                raise ValueError(
                    f"workflow_id mismatch: {workflow.workflow_id} != {workflow_id}"
                )
        return workflow


@dataclasses.dataclass
class CreateNewServerWorkflow(Workflow):
    ec2_inst_id: T.Optional[str] = dataclasses.field(default=None)
    db_inst_id: T.Optional[str] = dataclasses.field(default=None)

    def is_ec2_instance_created(self) -> bool:
        return self.ec2_inst_id is not None

    def is_db_instance_created(self) -> bool:
        return self.db_inst_id is not None


@dataclasses.dataclass
class CreateClonedServerWorkflow(Workflow):
    ec2_ami_id: T.Optional[str] = dataclasses.field(default=None)
    db_snapshot_id: T.Optional[str] = dataclasses.field(default=None)
    ec2_inst_id: T.Optional[str] = dataclasses.field(default=None)
    db_inst_id: T.Optional[str] = dataclasses.field(default=None)
    is_ec2_ami_deleted: bool = dataclasses.field(default=False)
    is_db_snapshot_deleted: bool = dataclasses.field(default=False)

    def is_fresh_start(self):
        return (
            (self.ec2_ami_id is None)
            and (self.db_snapshot_id is None)
            and (self.ec2_inst_id is None)
            and (self.db_inst_id is None)
            and (self.is_ec2_ami_deleted is False)
            and (self.is_db_snapshot_deleted is False)
        )

    def is_ec2_ami_created(self) -> bool:
        return self.ec2_ami_id is not None

    def is_db_snapshot_created(self) -> bool:
        return self.db_snapshot_id is not None

    def is_ec2_instance_created(self) -> bool:
        return self.ec2_inst_id is not None

    def is_db_instance_created(self) -> bool:
        return self.db_inst_id is not None


@dataclasses.dataclass
class CreateUpdatedServerWorkflow(Workflow):
    db_snapshot_id: T.Optional[str] = dataclasses.field(default=None)
    ec2_inst_id: T.Optional[str] = dataclasses.field(default=None)
    db_inst_id: T.Optional[str] = dataclasses.field(default=None)
    is_ec2_ami_deleted: bool = dataclasses.field(default=False)
    is_db_snapshot_deleted: bool = dataclasses.field(default=False)

    def is_db_snapshot_created(self) -> bool:
        return self.db_snapshot_id is not None

    def is_ec2_instance_created(self) -> bool:
        return self.ec2_inst_id is not None

    def is_db_instance_created(self) -> bool:
        return self.db_inst_id is not None


@dataclasses.dataclass
class DeleteServerWorkflow(Workflow):
    ec2_ami_id: T.Optional[str] = dataclasses.field(default=None)
    db_snapshot_id: T.Optional[str] = dataclasses.field(default=None)
    is_ec2_ami_available: bool = dataclasses.field(default=False)
    is_db_snapshot_available: bool = dataclasses.field(default=False)
    is_ec2_deleted: bool = dataclasses.field(default=False)
    is_db_deleted: bool = dataclasses.field(default=False)

    def is_fresh_start(self):
        return (self.ec2_ami_id is None) and (self.db_snapshot_id is None)

    def is_ec2_ami_created(self) -> bool:
        return self.ec2_ami_id is not None

    def is_db_snapshot_created(self) -> bool:
        return self.db_snapshot_id is not None


class ServerWorkflowMixin:  # pragma: no cover
    """
    Server Workflow Mixin class that contains all the server workflow methods.
    """

    @logger.emoji_block(
        msg="🆕🖥🛢Create Updated Server",
        emoji="🆕",
    )
    def create_new_server(
        self: "Server",
        bsm: "BotoSesManager",
        workflow_id: str,
        s3path_workflow: S3Path,
        ami_id: str,
        stack_exports: "StackExports",
    ):
        """
        Implement :ref:`create-new-server`.

        :param ami_id: the AMI ID to create the new EC2 instance.
        """
        aws_console = AWSConsole.from_bsm(bsm=bsm)
        workflow = CreateNewServerWorkflow.load(
            bsm=bsm,
            s3_path=s3path_workflow,
            workflow_id=workflow_id,
        )

        logger.info("Check new server configurations ...")
        if self.config.is_ready_for_create_new_server() is False:
            raise ValueError("server config is not ready for create cloned server")
        logger.info("✅ new server configuration is fine.")

        # --- create RDS
        if workflow.is_db_instance_created() is False:
            with logger.nested():
                res = self.create_rds_from_scratch(
                    bsm=bsm,
                    stack_exports=stack_exports,
                    check=True,
                    wait=True,
                )
                db_inst_id = res["DBInstance"]["DBInstanceIdentifier"]

            url = aws_console.rds.get_database_instance(db_inst_id)
            logger.info(f"🆕🛢Created DB Instance {db_inst_id!r}, preview at {url}")
            workflow.db_inst_id = db_inst_id
            workflow.dump(bsm=bsm, s3_path=s3path_workflow)
        else:
            logger.info("Skip creating DB instance, DB is already created.")

        # --- create EC2
        if workflow.is_ec2_instance_created() is False:
            with logger.nested():
                res = self.create_ec2(
                    bsm=bsm,
                    stack_exports=stack_exports,
                    ami_id=ami_id,
                    check=True,
                    wait=True,
                )
                ec2_inst_id = res["Instances"][0]["InstanceId"]
            url = aws_console.ec2.get_instance(ec2_inst_id)
            logger.info(f"🆕🖥Created EC2 instance {ec2_inst_id!r}, preview at {url}")
            workflow.ec2_inst_id = ec2_inst_id
            workflow.dump(bsm=bsm, s3_path=s3path_workflow)
        else:
            logger.info("Skip creating EC2 instance, EC2 is already created.")

    @logger.emoji_block(
        msg="🧬🖥🛢Create Cloned Server",
        emoji="🧬",
    )
    def create_cloned_server(
        self: "Server",
        bsm: "BotoSesManager",
        workflow_id: str,
        s3path_workflow: S3Path,
        new_server_id: str,
        stack_exports: "StackExports",
        snapshot_id: T.Optional[str] = None,
        skip_reboot: bool = False,
        delete_ami_afterwards: bool = False,
        delete_snapshot_afterwards: bool = False,
    ):
        """
        Implement :ref:`create-cloned-server`.
        """
        # --- make sure old server exists
        self.metadata.refresh(ec2_client=bsm.ec2_client, rds_client=bsm.rds_client)
        self.metadata.ensure_ec2_exists()
        self.metadata.ensure_rds_exists()
        # we need RDS to be available to create snapshot
        if self.metadata.is_rds_running() is False:
            logger.info("RDS is not running, try to wait it to be available then we can create snapshot ...")
            self.metadata.rds_inst.wait_for_available(rds_client=bsm.rds_client, timeout=900)

        aws_console = AWSConsole.from_bsm(bsm=bsm)
        workflow = CreateClonedServerWorkflow.load(
            bsm=bsm, s3_path=s3path_workflow, workflow_id=workflow_id
        )
        if snapshot_id is not None:
            workflow.db_snapshot_id = snapshot_id
            if delete_snapshot_afterwards is True:
                logger.info(
                    f"You provide the snapshot id explicitly, "
                    f"we cannot delete it afterward, "
                    f"set delete_snapshot_afterwards = False"
                )
                delete_snapshot_afterwards = False
        logger.info(f"Clone from {self.id!r} to {new_server_id!r}")

        logger.info("Check new server configurations ...")
        new_server = self.get(bsm=bsm, server_id=new_server_id)
        if new_server.config.is_ready_for_create_cloned_server() is False:
            raise ValueError("server config is not ready for create cloned server")
        logger.info("✅ new server configuration is fine.")

        # --- create AMI and DB Snapshot
        utc_now = get_utc_now()

        if workflow.is_ec2_ami_created() is False:
            with logger.nested():
                ami_name = self._get_ec2_ami_name(utc_now=utc_now)
                res = self.create_ec2_ami(
                    bsm=bsm,
                    ami_name=ami_name,
                    skip_reboot=skip_reboot,
                    wait=False,
                    check=True,
                )
                ami_id = res["ImageId"]
            url = aws_console.ec2.get_ami(ami_id)
            logger.info(f"🆕🖥📸Created EC2 AMI {ami_id!r}, preview at {url}")
            workflow.ec2_ami_id = ami_id
            workflow.dump(bsm=bsm, s3_path=s3path_workflow)
        else:
            logger.info("Skip creating EC2 AMI, AMI is already created.")

        if workflow.is_db_snapshot_created() is False:
            with logger.nested():
                # todo, if the RDS is not running, run it, then create snapshot, then stop it at the end.
                # todo, I need to thinks about if it is a valid feature
                snapshot_id = self._get_db_snapshot_id(utc_now=utc_now)
                res = self.create_db_snapshot(
                    bsm=bsm,
                    snapshot_id=snapshot_id,
                    wait=False,
                    check=True,
                    auto_resolve=True,
                )
                snapshot_id = res["DBSnapshot"]["DBSnapshotIdentifier"]
            url = aws_console.rds.get_snapshot(snapshot_id)
            logger.info(f"🆕🛢📸Created DB Snapshot {snapshot_id!r}, preview at {url}")
            workflow.db_snapshot_id = snapshot_id
            workflow.dump(bsm=bsm, s3_path=s3path_workflow)
        else:
            logger.info("Skip creating DB snapshot, snapshot is already created.")

        # --- create RDS
        if workflow.is_db_instance_created() is False:
            logger.info("wait for DB Snapshot to be available ...")
            snapshot = simple_aws_rds.RDSDBSnapshot(
                db_snapshot_identifier=workflow.db_snapshot_id,
            )
            snapshot.wait_for_available(rds_client=bsm.rds_client)

            with logger.nested():
                res = new_server.create_rds_from_snapshot(
                    bsm=bsm,
                    stack_exports=stack_exports,
                    db_snapshot_id=workflow.db_snapshot_id,
                    check=True,
                    wait=True,
                )
                db_inst_id = res["DBInstance"]["DBInstanceIdentifier"]

            url = aws_console.rds.get_database_instance(db_inst_id)
            logger.info(f"🆕🛢Created DB Instance {db_inst_id!r}, preview at {url}")
            workflow.db_inst_id = db_inst_id
            workflow.dump(bsm=bsm, s3_path=s3path_workflow)
        else:
            logger.info("Skip creating DB instance, DB is already created.")

        # --- create EC2
        if workflow.is_ec2_instance_created() is False:
            logger.info("wait for EC2 AMI to be available ...")
            image = simple_aws_ec2.Image(id=workflow.ec2_ami_id)
            image.wait_for_available(ec2_client=bsm.ec2_client)

            with logger.nested():
                res = new_server.create_ec2(
                    bsm=bsm,
                    stack_exports=stack_exports,
                    ami_id=workflow.ec2_ami_id,
                    check=True,
                    wait=True,
                )
                ec2_inst_id = res["Instances"][0]["InstanceId"]
            url = aws_console.ec2.get_instance(ec2_inst_id)
            logger.info(f"🆕🖥Created EC2 instance {ec2_inst_id!r}, preview at {url}")
            workflow.ec2_inst_id = ec2_inst_id
            workflow.dump(bsm=bsm, s3_path=s3path_workflow)
        else:
            logger.info("Skip creating EC2 instance, EC2 is already created.")

        if delete_ami_afterwards:
            if workflow.is_ec2_ami_deleted is False:
                logger.info("Delete AMI ...")
                image = simple_aws_ec2.Image(id=workflow.ec2_ami_id)
                image.deregister(
                    ec2_client=bsm.ec2_client,
                    delete_snapshot=True,  # also delete the snapshot
                    skip_prompt=True,
                )
                logger.info("✅Done")
                workflow.is_ec2_ami_deleted = True
                workflow.dump(bsm=bsm, s3_path=s3path_workflow)
            else:
                logger.info("Skip delete EC2 AMI, AMI is already deleted.")
        else:
            logger.info("We don't delete temp EC2 AMI afterward.")

        if delete_snapshot_afterwards:
            if workflow.is_db_snapshot_deleted is False:
                logger.info("Delete Snapshot ...")
                bsm.rds_client.delete_db_snapshot(
                    DBSnapshotIdentifier=workflow.db_snapshot_id,
                )
                logger.info("✅Done")
                workflow.is_db_snapshot_deleted = True
                workflow.dump(bsm=bsm, s3_path=s3path_workflow)
            else:
                logger.info("Skip delete DB snapshot, snapshot is already deleted.")
        else:
            logger.info("We don't delete temp DB snapshot afterward.")

    @logger.emoji_block(
        msg="🆕🖥🛢Create Updated Server",
        emoji="🆕",
    )
    def create_updated_server(
        self: "Server",
        bsm: "BotoSesManager",
        workflow_id: str,
        s3path_workflow: S3Path,
        new_server_id: str,
        ami_id: str,
        stack_exports: "StackExports",
        snapshot_id: T.Optional[str] = None,
        delete_snapshot_afterwards: bool = False,
    ):
        """
        Implement :ref:`create-updated-server`.

        :param ami_id: the AMI ID to create the new EC2 instance.
        :param snapshot_id: if None, it will try to run the db instance and wait
            it become available, then create a snapshot from it; if None and
            the db instant not exists, then raise error immediately; if provided
            use the given snapshot_id to create the db instance.
        """
        # --- make sure old server exists
        self.metadata.refresh(ec2_client=bsm.ec2_client, rds_client=bsm.rds_client)
        self.metadata.ensure_ec2_exists()
        self.metadata.ensure_rds_exists()

        aws_console = AWSConsole.from_bsm(bsm=bsm)
        workflow = CreateUpdatedServerWorkflow.load(
            bsm=bsm,
            s3_path=s3path_workflow,
            workflow_id=workflow_id,
        )
        if snapshot_id is not None:
            workflow.db_snapshot_id = snapshot_id
            if delete_snapshot_afterwards is True:
                logger.info(
                    f"You provide the snapshot id explicitly, "
                    f"we cannot delete it afterward, "
                    f"set delete_snapshot_afterwards = False"
                )
                delete_snapshot_afterwards = False
        logger.info(f"Create updated server from {self.id!r} to {new_server_id!r}")

        logger.info("Check new server configurations ...")
        new_server = self.get(bsm=bsm, server_id=new_server_id)
        if new_server.config.is_ready_for_create_cloned_server() is False:
            raise ValueError("server config is not ready for create cloned server")
        logger.info("✅ new server configuration is fine.")

        # --- create DB Snapshot
        utc_now = get_utc_now()
        if workflow.is_db_snapshot_created() is False:
            with logger.nested():
                snapshot_id = self._get_db_snapshot_id(utc_now=utc_now)
                # todo, if the RDS is not running, run it, then create snapshot, then stop it at the end.
                # todo, I need to thinks about if it is a valid feature
                res = self.create_db_snapshot(
                    bsm=bsm,
                    snapshot_id=snapshot_id,
                    wait=False,
                    check=True,
                    auto_resolve=True,
                )
                snapshot_id = res["DBSnapshot"]["DBSnapshotIdentifier"]
            url = aws_console.rds.get_snapshot(snapshot_id)
            logger.info(f"🆕🛢📸Created DB Snapshot {snapshot_id!r}, preview at {url}")
            workflow.db_snapshot_id = snapshot_id
            workflow.dump(bsm=bsm, s3_path=s3path_workflow)
        else:
            logger.info("Skip creating DB snapshot, snapshot is already created.")

        # --- create RDS
        if workflow.is_db_instance_created() is False:
            logger.info("wait for DB Snapshot to be available ...")
            snapshot = simple_aws_rds.RDSDBSnapshot(
                db_snapshot_identifier=workflow.db_snapshot_id
            )
            snapshot.wait_for_available(rds_client=bsm.rds_client)

            with logger.nested():
                res = new_server.create_rds_from_snapshot(
                    bsm=bsm,
                    stack_exports=stack_exports,
                    db_snapshot_id=workflow.db_snapshot_id,
                    check=True,
                    wait=True,
                )
                db_inst_id = res["DBInstance"]["DBInstanceIdentifier"]

            url = aws_console.rds.get_database_instance(db_inst_id)
            logger.info(f"🆕🛢Created DB Instance {db_inst_id!r}, preview at {url}")
            workflow.db_inst_id = db_inst_id
            workflow.dump(bsm=bsm, s3_path=s3path_workflow)
        else:
            logger.info("Skip creating DB instance, DB is already created.")

        # --- create EC2
        if workflow.is_ec2_instance_created() is False:
            with logger.nested():
                res = new_server.create_ec2(
                    bsm=bsm,
                    stack_exports=stack_exports,
                    ami_id=ami_id,
                    check=True,
                    wait=True,
                )
                ec2_inst_id = res["Instances"][0]["InstanceId"]
            url = aws_console.ec2.get_instance(ec2_inst_id)
            logger.info(f"🆕🖥Created EC2 instance {ec2_inst_id!r}, preview at {url}")
            workflow.ec2_inst_id = ec2_inst_id
            workflow.dump(bsm=bsm, s3_path=s3path_workflow)
        else:
            logger.info("Skip creating EC2 instance, EC2 is already created.")

        if delete_snapshot_afterwards:
            if workflow.is_db_snapshot_deleted is False:
                logger.info("Delete Snapshot ...")
                bsm.rds_client.delete_db_snapshot(
                    DBSnapshotIdentifier=workflow.db_snapshot_id,
                )
                logger.info("✅Done")
                workflow.is_db_snapshot_deleted = True
                workflow.dump(bsm=bsm, s3_path=s3path_workflow)
            else:
                logger.info("Skip delete DB snapshot, snapshot is already deleted.")
        else:
            logger.info("We don't delete temp DB snapshot afterward.")

    @logger.emoji_block(
        msg="🗑🖥🛢Delete Server",
        emoji="🗑",
    )
    def delete_server(
        self: "Server",
        bsm: "BotoSesManager",
        workflow_id: str,
        s3path_workflow: S3Path,
        skip_reboot: bool = False,
        create_backup_ec2_ami: bool = True,
        create_backup_db_snapshot: bool = True,
        skip_prompt: bool = False,
    ):
        """
        Implement :ref:`delete-server`.
        """
        aws_console = AWSConsole.from_bsm(bsm=bsm)
        workflow = DeleteServerWorkflow.load(
            bsm=bsm,
            s3_path=s3path_workflow,
            workflow_id=workflow_id,
        )
        logger.info(f"Delete {self.id!r}")
        if skip_prompt is False:
            prompt_for_confirm(
                msg=(f"💥Are you sure you want to DELETE server {self.id!r}?")
            )

        # --- create AMI and DB Snapshot
        utc_now = get_utc_now()

        if create_backup_ec2_ami:
            if workflow.is_ec2_ami_created() is False:
                with logger.nested():
                    ami_name = self._get_ec2_ami_name()
                    ami_name = f"{ami_name}-final-backup"
                    res = self.create_ec2_ami(
                        bsm=bsm,
                        ami_name=ami_name,
                        skip_reboot=skip_reboot,
                        wait=False,
                        check=True,
                    )
                    ami_id = res["ImageId"]
                url = aws_console.ec2.get_ami(ami_id)
                logger.info(f"🗑🖥📸Created EC2 AMI {ami_id!r}, preview at {url}")
                workflow.ec2_ami_id = ami_id
                workflow.dump(bsm=bsm, s3_path=s3path_workflow)
            else:
                logger.info("Skip creating EC2 AMI, AMI is already created.")
        else:
            logger.info("We don't creating final EC2 AMI backup.")

        if create_backup_db_snapshot:
            if workflow.is_db_snapshot_created() is False:
                with logger.nested():
                    snapshot_id = self._get_db_snapshot_id(utc_now=utc_now)
                    snapshot_id = f"{snapshot_id}-final-backup"
                    res = self.create_db_snapshot(
                        bsm=bsm,
                        snapshot_id=snapshot_id,
                        wait=False,
                        check=True,
                    )
                    snapshot_id = res["DBSnapshot"]["DBSnapshotIdentifier"]
                url = aws_console.rds.get_snapshot(snapshot_id)
                logger.info(
                    f"🗑🛢📸Created DB Snapshot {snapshot_id!r}, preview at {url}"
                )
                workflow.db_snapshot_id = snapshot_id
                workflow.dump(bsm=bsm, s3_path=s3path_workflow)
            else:
                logger.info("Skip creating DB snapshot, snapshot is already created.")
        else:
            logger.info("We don't creating final DB snapshot backup.")

        if create_backup_ec2_ami:
            if workflow.is_ec2_ami_available is False:
                logger.info("wait for EC2 AMI to be available ...")
                image = simple_aws_ec2.Image(id=workflow.ec2_ami_id)
                image.wait_for_available(ec2_client=bsm.ec2_client)
                workflow.is_ec2_ami_available = True
                workflow.dump(bsm=bsm, s3_path=s3path_workflow)

        if create_backup_db_snapshot:
            if workflow.is_db_snapshot_available is False:
                logger.info("wait for DB Snapshot to be available ...")
                snapshot = simple_aws_rds.RDSDBSnapshot(
                    db_snapshot_identifier=workflow.db_snapshot_id
                )
                snapshot.wait_for_available(rds_client=bsm.rds_client)
                workflow.is_db_snapshot_available = True
                workflow.dump(bsm=bsm, s3_path=s3path_workflow)

        # --- delete EC2
        if workflow.is_ec2_deleted is False:
            if self.metadata.is_ec2_exists():
                with logger.nested():
                    res = self.delete_ec2(
                        bsm=bsm,
                        check=False,
                    )
                    ec2_inst_id = self.metadata.ec2_inst.id
                    url = aws_console.ec2.get_instance(ec2_inst_id)
                logger.info(f"🗑🖥Delete EC2 instance {ec2_inst_id!r}, verify at {url}")
            else:
                logger.info("Skip terminate EC2 instance, EC2 is already terminated.")
            workflow.is_ec2_deleted = True
            workflow.dump(bsm=bsm, s3_path=s3path_workflow)
        else:
            logger.info("Skip terminate EC2 instance, EC2 is already terminated.")

        # --- delete RDS
        if workflow.is_db_deleted is False:
            if self.metadata.is_rds_exists():
                with logger.nested():
                    res = self.delete_rds(
                        bsm=bsm,
                        create_final_snapshot=False,  # we already manually create one
                        check=False,
                    )
                    db_inst_id = self.metadata.rds_inst.id
                    url = aws_console.rds.get_database_instance(db_inst_id)
                logger.info(f"🗑🛢Delete DB Instance {db_inst_id!r}, verify at {url}")
            else:
                logger.info("Skip delete DB instance, DB is already deleted.")
            workflow.is_db_deleted = True
            workflow.dump(bsm=bsm, s3_path=s3path_workflow)
        else:
            logger.info("Skip delete DB instance, DB is already deleted.")

    @logger.emoji_block(
        msg="🔴🖥🛢Stop Server",
        emoji="🔴",
    )
    def stop_server(
        self: "Server",
        bsm: "BotoSesManager",
    ):
        """
        Implement :ref:`stop-server`. 这个 workflow 不需要用 S3 来 track status.
        """
        # --- Stop worldserver
        # 注意, 每次执行这个 workflow 的时候我们都尝试关闭 worldserver 并等待 10 秒
        # 确保服务器不会丢数据
        if self.metadata.is_ec2_running() is True:
            with logger.nested():
                self.stop_worldserver(bsm=bsm)
            logger.info("Wait 10 seconds for worldserver completely shutdown ...")
            time.sleep(10)
            logger.info(f"🔴Stopped worldserver.")
        else:
            logger.info("EC2 is not running, skip stop worldserver.")

        # --- Shutdown EC2 and RDS
        if self.metadata.ec2_inst.is_ready_to_stop():
            with logger.nested():
                self.stop_ec2(bsm=bsm, wait=False, auto_resolve=True)
        else:
            logger.info("Skip stop EC2, it is already stopped.")
        logger.info("Wait 3 seconds for stopping EC2 instance ...")
        time.sleep(3)

        if self.metadata.rds_inst.is_ready_to_stop():
            with logger.nested():
                self.stop_rds(bsm=bsm, wait=False, auto_resolve=True)
        else:
            logger.info("Skip stop RDS, it is already stopped.")
        logger.info("Wait 3 seconds for stopping RDS instance ...")
        time.sleep(3)

        # --- Wait EC2 and RDS to be fully stopped
        logger.info("Wait for 🖥EC2 instance fully stopped ...")
        self.metadata.ec2_inst.wait_for_stopped(ec2_client=bsm.ec2_client, timeout=300)
        logger.info(f"🔴🖥EC2 is stopped.")

        logger.info("Wait for 🛢RDS instance fully stopped ...")
        self.metadata.rds_inst.wait_for_stopped(rds_client=bsm.rds_client, timeout=900)
        logger.info(f"🔴🛢RDS is stopped.")

    @logger.emoji_block(
        msg="🟢🖥🛢Start Server",
        emoji="🟢",
    )
    def start_server(
        self: "Server",
        bsm: "BotoSesManager",
    ):
        """
        Implement :ref:`start-server`. 这个 workflow 不需要用 S3 来 track status.
        """
        # --- Start RDS
        if self.metadata.rds_inst.is_ready_to_start():
            with logger.nested():
                self.start_rds(bsm=bsm, wait=True)
        else:
            logger.info("Wait 🛢RDS to be available ...")
            self.metadata.rds_inst.wait_for_available(
                rds_client=bsm.rds_client,
                timeout=900,
            )
        logger.info("🟢🛢RDS is available.")

        # --- Start EC2
        if self.metadata.ec2_inst.is_ready_to_start():
            with logger.nested():
                self.start_ec2(bsm=bsm, wait=True)
        else:
            logger.info("Wait 🖥EC2 to be running ...")
            self.metadata.ec2_inst.wait_for_running(
                ec2_client=bsm.ec2_client,
                timeout=300,
            )
        logger.info("🟢🖥EC2 is running.")

        logger.info(
            "🚀EC2 may take 30 seconds to make the worldserver fully ready. "
            "Consider using ``acore_server_bootstrap.api.Remoter.list_session`` "
            "method to verify the status of the worldserver. "
            "You can find more information at https://acore-server-bootstrap.readthedocs.io/en/latest/acore_server_bootstrap/remoter.html#acore_server_bootstrap.remoter.Remoter.list_session"
        )
