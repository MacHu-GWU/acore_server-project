# -*- coding: utf-8 -*-

"""
todo: doc string
"""

import typing as T
import dataclasses
import json
from datetime import datetime, timezone

from boto_session_manager import BotoSesManager
from s3pathlib import S3Path
from aws_ssm_run_command.api import better_boto as ssm_better_boto
from aws_console_url.api import AWSConsole
import simple_aws_ec2.api as simple_aws_ec2
import simple_aws_rds.api as simple_aws_rds
from acore_paths.api import path_acore_server_bootstrap_cli
from acore_constants.api import TagKey
from acore_server_config.api import EnvEnum
from acore_db_ssh_tunnel import api as acore_db_ssh_tunnel

from .paths import path_pem_file as default_path_pem_file
from .constants import EC2_USERNAME, DB_PORT
from .exc import (
    ServerNotFoundError,
    ServerAlreadyExistsError,
    FailedToStartServerError,
    FailedToStopServerError,
)
from .logger import logger
from .utils import get_utc_now, prompt_for_confirm
from .wserver_infra_exports import StackExports


if T.TYPE_CHECKING:  # pragma: no cover
    from .server import Server
    from mypy_boto3_rds.type_defs import CreateDBSnapshotResultTypeDef


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
class DeleteServerWorkflow(Workflow):
    ec2_ami_id: T.Optional[str] = dataclasses.field(default=None)
    db_snapshot_id: T.Optional[str] = dataclasses.field(default=None)
    is_ec2_deleted: bool = dataclasses.field(default=False)
    is_db_deleted: bool = dataclasses.field(default=False)

    def is_fresh_start(self):
        return (self.ec2_ami_id is None) and (self.db_snapshot_id is None)

    def is_ec2_ami_created(self) -> bool:
        return self.ec2_ami_id is not None

    def is_db_snapshot_created(self) -> bool:
        return self.db_snapshot_id is not None

    def is_ec2_ami_created(self) -> bool:
        return self.ec2_ami_id is not None

    def is_db_snapshot_created(self) -> bool:
        return self.db_snapshot_id is not None


class ServerWorkflowMixin:  # pragma: no cover
    """
    Server Workflow Mixin class that contains all the server workflow methods.
    """

    def ensure_server_is_ready_for_clone(
        self: "Server",
        bsm: "BotoSesManager",
    ) -> T.Tuple[simple_aws_ec2.Ec2Instance, simple_aws_rds.RDSDBInstance]:
        ec2_inst = self.ensure_rds_exists(bsm=bsm)
        if self.metadata.is_rds_running() is False:
            raise FailedToStartServerError(
                f"RDS DB instance {self.id!r} is not running, so we cannot create DB snapshot then clone the server!"
            )
        return ec2_inst, self.metadata.rds_inst

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
        skip_reboot: bool = False,
        delete_ami_afterwards: bool = False,
        delete_snapshot_afterwards: bool = False,
    ):
        aws_console = AWSConsole.from_bsm(bsm=bsm)
        workflow = CreateClonedServerWorkflow.load(
            bsm=bsm, s3_path=s3path_workflow, workflow_id=workflow_id
        )
        logger.info(f"Clone from {self.id!r} to {new_server_id!r}")

        logger.info("Check new server configurations ...")
        new_server = self.get(bsm=bsm, server_id=new_server_id)
        if new_server.config.is_ready_for_create_cloned_server() is False:
            raise ValueError("server config is not ready for create cloned server")
        logger.info("✅ new server configuration is fine.")

        if workflow.is_fresh_start():
            logger.info("Check old server status ...")
            ec2_inst, rds_inst = self.ensure_server_is_ready_for_clone(bsm=bsm)
            logger.info("✅ old server is running fine.")

            logger.info("Check new server status ...")
            new_server.ensure_ec2_not_exists(bsm=bsm)
            new_server.ensure_rds_not_exists(bsm=bsm)
            logger.info("✅ new server not exists, ready to create clone.")

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
                )
                ami_id = res["ImageId"]
            url = aws_console.ec2.get_ami(ami_id)
            logger.info(f"🆕🖥📸Created EC2 AMI {ami_id!r}, preview at {url}")
            workflow.ec2_ami_id = ami_id
            workflow.dump(bsm=bsm, s3_path=s3path_workflow)

        if workflow.is_db_snapshot_created() is False:
            with logger.nested():
                snapshot_id = self._get_db_snapshot_id(utc_now=utc_now)
                res = self.create_db_snapshot(
                    bsm=bsm, snapshot_id=snapshot_id, wait=False
                )
                snapshot_id = res["DBSnapshot"]["DBSnapshotIdentifier"]
            url = aws_console.rds.get_snapshot(snapshot_id)
            logger.info(f"🆕🛢📸Created DB Snapshot {snapshot_id!r}, preview at {url}")
            workflow.db_snapshot_id = snapshot_id
            workflow.dump(bsm=bsm, s3_path=s3path_workflow)

        # --- create RDS
        if workflow.is_db_instance_created() is False:
            logger.info("wait for DB Snapshot to be available ...")
            snapshot = simple_aws_rds.RDSDBSnapshot(db_snapshot_identifier=snapshot_id)
            snapshot.wait_for_available(rds_client=bsm.rds_client)

            with logger.nested():
                res = new_server.create_rds_from_snapshot(
                    bsm=bsm,
                    stack_exports=stack_exports,
                    db_snapshot_id=snapshot_id,
                    check=True,
                    wait=True,
                )
                db_inst_id = res["DBInstance"]["DBInstanceIdentifier"]
            url = aws_console.rds.get_database_instance(db_inst_id)
            logger.info(f"🆕🛢Created DB Instance {db_inst_id!r}, preview at {url}")
            workflow.db_inst_id = db_inst_id
            workflow.dump(bsm=bsm, s3_path=s3path_workflow)

        # --- create EC2
        if workflow.is_ec2_instance_created() is False:
            logger.info("wait for EC2 AMI to be available ...")
            image = simple_aws_ec2.Image(id=ami_id)
            image.wait_for_available(ec2_client=bsm.ec2_client)

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

        if delete_ami_afterwards:
            if workflow.is_ec2_ami_deleted is False:
                logger.info("Delete AMI ...")
                image.deregister(
                    ec2_client=bsm.ec2_client,
                    delete_snapshot=True,  # also delete the snapshot
                    skip_prompt=True,
                )
                logger.info("✅Done")
                workflow.is_ec2_ami_deleted = True
                workflow.dump(bsm=bsm, s3_path=s3path_workflow)

        if delete_snapshot_afterwards:
            if workflow.is_db_snapshot_deleted is False:
                logger.info("Delete Snapshot ...")
                bsm.rds_client.delete_db_snapshot(
                    DBSnapshotIdentifier=snapshot_id,
                )
                logger.info("✅Done")
                workflow.is_db_snapshot_deleted = True
                workflow.dump(bsm=bsm, s3_path=s3path_workflow)

    # def ensure_server_is_ready_for_clone(
    #     self: "Server",
    #     bsm: "BotoSesManager",
    # ) -> T.Tuple[simple_aws_ec2.Ec2Instance, simple_aws_rds.RDSDBInstance]:
    #     ec2_inst = self.ensure_rds_exists(bsm=bsm)
    #     if self.metadata.is_rds_running() is False:
    #         raise FailedToStartServerError(
    #             f"RDS DB instance {self.id!r} is not running, so we cannot create DB snapshot then clone the server!"
    #         )
    #     return ec2_inst, self.metadata.rds_inst

    @logger.emoji_block(
        msg="🗑🖥🛢Delete Server",
        emoji="🗑",
    )
    def delete_server(
        self: "Server",
        bsm: "BotoSesManager",
        workflow_id: str,
        s3path_workflow: S3Path,
        stack_exports: "StackExports",
        skip_reboot: bool = False,
        create_backup_ec2_ami: bool = True,
        create_backup_db_snapshot: bool = True,
        skip_prompt: bool = False,
    ):
        aws_console = AWSConsole.from_bsm(bsm=bsm)
        workflow = DeleteServerWorkflow.load(
            bsm=bsm, s3_path=s3path_workflow, workflow_id=workflow_id
        )
        logger.info(f"Delete {self.id!r}")
        if skip_prompt is False:
            prompt_for_confirm(
                msg=(f"💥Are you sure you want to DELETE **Server {self.id!r}**?")
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
                    )
                    ami_id = res["ImageId"]
                url = aws_console.ec2.get_ami(ami_id)
                logger.info(f"Created EC2 AMI {ami_id!r}, preview at {url}")
                workflow.ec2_ami_id = ami_id
                workflow.dump(bsm=bsm, s3_path=s3path_workflow)

        if create_backup_db_snapshot:
            if workflow.is_db_snapshot_created() is False:
                with logger.nested():
                    snapshot_id = self._get_db_snapshot_id(utc_now=utc_now)
                    snapshot_id = f"{snapshot_id}-final-backup"
                    res = self.create_db_snapshot(
                        bsm=bsm,
                        snapshot_id=snapshot_id,
                        wait=False,
                    )
                    snapshot_id = res["DBSnapshot"]["DBSnapshotIdentifier"]
                url = aws_console.rds.get_snapshot(snapshot_id)
                logger.info(f"Created DB Snapshot {snapshot_id!r}, preview at {url}")
                workflow.db_snapshot_id = snapshot_id
                workflow.dump(bsm=bsm, s3_path=s3path_workflow)

        if create_backup_ec2_ami:
            logger.info("wait for EC2 AMI to be available ...")
            image = simple_aws_ec2.Image(id=ami_id)
            image.wait_for_available(ec2_client=bsm.ec2_client)

        if create_backup_db_snapshot:
            logger.info("wait for DB Snapshot to be available ...")
            snapshot = simple_aws_rds.RDSDBSnapshot(db_snapshot_identifier=snapshot_id)
            snapshot.wait_for_available(rds_client=bsm.rds_client)

        # --- delete EC2
        if workflow.is_ec2_deleted is False:
            with logger.nested():
                if self.metadata.is_ec2_exists():
                    res = self.delete_ec2(
                        bsm=bsm,
                        check=False,
                    )
                    ec2_inst_id = self.metadata.ec2_inst.id
                    url = aws_console.ec2.get_instance(ec2_inst_id)
                    logger.info(f"Delete EC2 instance {ec2_inst_id!r}, verify at {url}")
                    workflow.is_ec2_deleted = True
                    workflow.dump(bsm=bsm, s3_path=s3path_workflow)

        # --- delete RDS
        if workflow.is_db_deleted is False:
            with logger.nested():
                if self.metadata.is_rds_exists():
                    res = self.delete_rds(
                        bsm=bsm,
                        stack_exports=stack_exports,
                        db_snapshot_id=snapshot_id,
                        check=True,
                        wait=True,
                    )
                    db_inst_id = self.metadata.rds_inst.id
                    url = aws_console.rds.get_database_instance(db_inst_id)
                    logger.info(f"Created DB Instance {db_inst_id!r}, preview at {url}")
                    workflow.is_db_deleted = True
                    workflow.dump(bsm=bsm, s3_path=s3path_workflow)