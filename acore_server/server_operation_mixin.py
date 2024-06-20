# -*- coding: utf-8 -*-

"""
todo: doc string
"""

import typing as T
from datetime import datetime, timezone

from boto_session_manager import BotoSesManager
from aws_ssm_run_command.api import better_boto as ssm_better_boto
import simple_aws_ec2.api as simple_aws_ec2
import simple_aws_rds.api as simple_aws_rds

from acore_paths.api import path_acore_server_bootstrap_cli
from acore_constants.api import TagKey
from acore_server_config.api import EnvEnum
from acore_db_ssh_tunnel import api as acore_db_ssh_tunnel
from .vendor.hashes import hashes

from .paths import path_pem_file as default_path_pem_file
from .constants import EC2_USERNAME, DB_PORT
from .wserver_infra_exports import StackExports
from .logger import logger
from .utils import get_utc_now


if T.TYPE_CHECKING:  # pragma: no cover
    from .server import Server
    from mypy_boto3_ec2.type_defs import (
        CreateImageResultTypeDef,
        ReservationResponseTypeDef,
        StartInstancesResultTypeDef,
        StopInstancesResultTypeDef,
        TerminateInstancesResultTypeDef,
    )
    from mypy_boto3_rds.type_defs import (
        CreateDBSnapshotResultTypeDef,
        CreateDBInstanceResultTypeDef,
        RestoreDBInstanceFromDBSnapshotResultTypeDef,
        StartDBInstanceResultTypeDef,
        StopDBInstanceResultTypeDef,
        DeleteDBInstanceResultTypeDef,
    )


class ServerOperationMixin:  # pragma: no cover
    """
    Server Operation Mixin class that contains all the server operation methods.
    """

    def _get_ec2_ami_name(
        self: "Server",
        utc_now: T.Optional[datetime] = None,
    ) -> str:
        """
        Get the EC2 AMI id for this server, the snapshot id
        naming convention is "${server_id}-%Y-%m-%d-%H-%M-%S".
        """
        if utc_now is None:
            utc_now = get_utc_now()
        snapshot_id = "{}-{}".format(
            self.id,
            utc_now.strftime("%Y-%m-%d-%H-%M-%S"),
        )
        return snapshot_id

    def _get_db_snapshot_id(
        self: "Server",
        utc_now: T.Optional[datetime] = None,
    ) -> str:
        """
        Get the db snapshot id for this server, the snapshot id
        naming convention is "${server_id}-%Y-%m-%d-%H-%M-%S".
        """
        if utc_now is None:
            utc_now = get_utc_now()
        snapshot_id = "{}-{}".format(
            self.id,
            utc_now.strftime("%Y-%m-%d-%H-%M-%S"),
        )
        return snapshot_id

    def build_bootstrap_command(
        self: "Server",
        python_version: str = "3.8",
        acore_soap_app_version: T.Optional[str] = None,
        acore_db_app_version: T.Optional[str] = None,
        acore_server_bootstrap_version: T.Optional[str] = None,
    ) -> str:
        """
        构建需要在 EC2 服务器上运行的 bootstrap 命令.
        """
        script_url = "https://raw.githubusercontent.com/MacHu-GWU/acore_server_bootstrap-project/main/install.py"
        main_part = (
            f"sudo /home/ubuntu/.pyenv/shims/python{python_version} -c "
            f'"$(curl -fsSL {script_url})"'
        )
        parts = [main_part]
        if acore_soap_app_version:
            parts.append(f"--acore_soap_app_version {self.config.acore_soap_app_version}")
        if acore_db_app_version:
            parts.append(f"--acore_db_app_version {self.config.acore_db_app_version}")
        if acore_server_bootstrap_version:
            parts.append(f"--acore_server_bootstrap_version {self.config.acore_server_bootstrap_version}")
        cmd = " ".join(parts)
        return cmd

    @logger.emoji_block(
        msg="🆕🖥Create EC2 Instance",
        emoji="🖥",
    )
    def create_ec2(
        self: "Server",
        bsm: "BotoSesManager",
        stack_exports: "StackExports",
        ami_id: T.Optional[str] = None,
        instance_type: T.Optional[str] = None,
        python_version: str = "3.8",
        acore_soap_app_version: T.Optional[str] = None,
        acore_db_app_version: T.Optional[str] = None,
        acore_server_bootstrap_version: T.Optional[str] = None,
        tags: T.Optional[T.Dict[str, str]] = None,
        check: bool = True,
        wait: bool = True,
        **kwargs,
    ) -> "ReservationResponseTypeDef":
        """
        为服务器创建一台新的 EC2. 注意, 一般先创建 RDS, 等 RDS 已经在运行了, 再创建 EC2.
        因为 EC2 有一个 bootstrap 的过程, 这个过程中需要跟数据库通信.

        :param ami_id: 你要从哪个 AMI 来创建 EC2? 如果不指定, 则使用 config 中的 AMI ID.
            这个参数之所以是可选是因为在有的 workflow 中, 我们已经知道 AMI ID 了;
            而有的 workflow 中, 我们要临时创建一个新的 AMI ID, 此时还不知道这个 ID.
        """
        bootstrap_command = self.build_bootstrap_command(
            python_version=python_version,
            acore_soap_app_version=acore_soap_app_version,
            acore_db_app_version=acore_db_app_version,
            acore_server_bootstrap_version=acore_server_bootstrap_version,
        )
        user_data_lines = [
            "#!/bin/bash",
            bootstrap_command,
        ]
        if check:
            self.ensure_ec2_not_exists(bsm=bsm)
        if tags is None:
            tags = dict()
        tags["Name"] = self.id
        tags[TagKey.SERVER_ID] = self.id  # the realm tag indicator has to match
        tags["tech:machine_creator"] = "acore_server_metadata"
        if ami_id is None:
            ami_id = self.config.ec2_ami_id
        if instance_type is None:
            instance_type = self.config.ec2_instance_type
        run_instances_kwargs = dict(
            ImageId=ami_id,
            InstanceType=instance_type,
            # only launch one instance for each realm
            MinCount=1,
            MaxCount=1,
            KeyName=self.config.ec2_key_name,
            SecurityGroupIds=[
                stack_exports.get_default_sg_id(server_id=self.id),
                stack_exports.get_ec2_sg_id(server_id=self.id),
                stack_exports.get_ssh_sg_id(),
            ],
            SubnetId=self.config.ec2_subnet_id,
            IamInstanceProfile=dict(Arn=stack_exports.get_ec2_instance_profile_arn()),
            TagSpecifications=[
                dict(
                    ResourceType="instance",
                    Tags=[dict(Key=k, Value=v) for k, v in tags.items()],
                ),
            ],
            **kwargs,
        )
        if any(
            [
                acore_soap_app_version,
                acore_db_app_version,
                acore_server_bootstrap_version,
            ]
        ):
            kwargs["UserData"] = "\n".join(user_data_lines)
        res = bsm.ec2_client.run_instances(**run_instances_kwargs)
        if wait:
            inst_id = res["Instances"][0]["InstanceId"]
            ec2_inst = simple_aws_ec2.Ec2Instance(id=inst_id, status="na")
            ec2_inst.wait_for_running(ec2_client=bsm.ec2_client, timeout=300)
        return res

    @logger.emoji_block(
        msg="🆕🛢Create RDS from scratch",
        emoji="🛢",
    )
    def create_rds_from_scratch(
        self: "Server",
        bsm: "BotoSesManager",
        stack_exports: "StackExports",
        db_instance_class: T.Optional[str] = None,
        engine_version: T.Optional[str] = None,
        multi_az: T.Optional[bool] = None,
        tags: T.Optional[T.Dict[str, str]] = None,
        check: bool = True,
        wait: bool = True,
        **kwargs,
    ) -> "CreateDBInstanceResultTypeDef":
        """
        不使用 DB Snapshot, 创建一台全新的数据库.

        - https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/rds/client/create_db_instance.html
        """
        if check:
            self.ensure_rds_not_exists(bsm=bsm)
        if tags is None:
            tags = dict()
        tags[TagKey.SERVER_ID] = self.id
        tags["tech:machine_creator"] = "acore_server"
        hashes.use_sha256()
        digest = hashes.of_str(self.config.db_admin_password, hexdigest=True)
        tags["tech:master_password_digest"] = digest
        if db_instance_class is None:
            db_instance_class = self.config.db_instance_class
        if engine_version is None:
            engine_version = self.config.db_engine_version
        if multi_az is None:
            multi_az = False
        res = bsm.rds_client.create_db_instance(
            DBInstanceIdentifier=self.id,
            DBInstanceClass=db_instance_class,
            Engine="mysql",
            EngineVersion=engine_version,
            MasterUsername=self.config.db_admin_username,
            MasterUserPassword=self.config.db_admin_password,
            MultiAZ=multi_az,
            DBSubnetGroupName=stack_exports.get_db_subnet_group_name(),
            PubliclyAccessible=False,  # you should never expose your database to the public
            AutoMinorVersionUpgrade=False,  # don't update MySQL minor version, PLEASE!
            VpcSecurityGroupIds=[
                stack_exports.get_default_sg_id(server_id=self.id),
            ],
            CopyTagsToSnapshot=True,
            Tags=[dict(Key=k, Value=v) for k, v in tags.items()],
            **kwargs,
        )
        if wait:
            rds_inst = simple_aws_rds.RDSDBInstance(id=self.id, status="na")
            rds_inst.wait_for_available(rds_client=bsm.rds_client, timeout=600)
        return res

    @logger.emoji_block(
        msg="🆕🛢Create RDS from snapshot",
        emoji="🛢",
    )
    def create_rds_from_snapshot(
        self: "Server",
        bsm: "BotoSesManager",
        stack_exports: "StackExports",
        db_snapshot_id: T.Optional[str] = None,
        db_instance_class: T.Optional[str] = None,
        multi_az: T.Optional[bool] = None,
        tags: T.Optional[T.Dict[str, str]] = None,
        check: bool = True,
        wait: bool = True,
        **kwargs,
    ) -> "RestoreDBInstanceFromDBSnapshotResultTypeDef":
        """
        为服务器创建一台新的数据库.

        :param bsm:
        :param stack_exports:
        :param db_snapshot_id: 要从哪个 DB Snapshot 来创建 RDS? 如果不指定, 则使用 config 中的 DB Snapshot ID.
            这个参数之所以是可选是因为在有的 workflow 中, 我们已经知道 DB Snapshot ID 了;
            而有的 workflow 中, 我们要临时创建一个新的 DB Snapshot ID, 此时还不知道这个 ID.
        :param db_instance_class:
        :param multi_az:
        :param tags:
        :param check:
        """
        if check:
            self.ensure_rds_not_exists(bsm=bsm)
        if tags is None:
            tags = dict()
        tags[TagKey.SERVER_ID] = self.id
        tags["tech:machine_creator"] = "acore_server"
        if db_snapshot_id is None:
            db_snapshot_id = self.config.db_snapshot_id
        if db_instance_class is None:
            db_instance_class = self.config.db_instance_class
        if multi_az is None:
            multi_az = False
        # locate master password digest from snapshot tags
        res = bsm.rds_client.describe_db_snapshots(
            DBSnapshotIdentifier=db_snapshot_id,
        )
        db_snapshot_list = res.get("DBSnapshots", [])
        if len(db_snapshot_list):
            db_snapshot_tags = {
                dct["Key"]: dct["Value"]
                for dct in db_snapshot_list[0].get("TagList", [])
            }
            master_password_digest = db_snapshot_tags.get("tech:master_password_digest")
            if master_password_digest:
                tags["tech:master_password_digest"] = master_password_digest
        res = bsm.rds_client.restore_db_instance_from_db_snapshot(
            DBInstanceIdentifier=self.id,
            DBSnapshotIdentifier=db_snapshot_id,
            DBInstanceClass=db_instance_class,
            MultiAZ=multi_az,
            DBSubnetGroupName=stack_exports.get_db_subnet_group_name(),
            PubliclyAccessible=False,  # you should never expose your database to the public
            AutoMinorVersionUpgrade=False,  # don't update MySQL minor version, PLEASE!
            VpcSecurityGroupIds=[
                stack_exports.get_default_sg_id(server_id=self.id),
            ],
            CopyTagsToSnapshot=True,
            Tags=[dict(Key=k, Value=v) for k, v in tags.items()],
            **kwargs,
        )
        if wait:
            rds_inst = simple_aws_rds.RDSDBInstance(id=self.id, status="na")
            rds_inst.wait_for_available(rds_client=bsm.rds_client, timeout=600)
        return res

    @logger.emoji_block(
        msg="🟢🖥Start EC2 instance",
        emoji="🖥",
    )
    def start_ec2(
        self: "Server",
        bsm: "BotoSesManager",
        check: bool = True,
        wait: bool = True,
    ) -> "StartInstancesResultTypeDef":
        """
        启动关闭着的 EC2.
        """
        if check:
            self.ensure_ec2_is_ready_to_start(bsm=bsm)
        ec2_inst = self.metadata.ec2_inst
        res = ec2_inst.start_instance(ec2_client=bsm.ec2_client)
        if wait:
            ec2_inst.wait_for_running(ec2_client=bsm.ec2_client, timeout=300)
        return res

    @logger.emoji_block(
        msg="🟢🛢Start RDS instance",
        emoji="🛢",
    )
    def start_rds(
        self: "Server",
        bsm: "BotoSesManager",
        check: bool = True,
        wait: bool = True,
    ) -> "StartDBInstanceResultTypeDef":
        """
        启动关闭着的 RDS.
        """
        if check:
            self.ensure_rds_is_ready_to_start(bsm=bsm)
        rds_inst = self.metadata.rds_inst
        res = rds_inst.start_db_instance(rds_client=bsm.rds_client)
        if wait:
            rds_inst.wait_for_available(rds_client=bsm.rds_client, timeout=600)
        return res

    def associate_eip_address(
        self: "Server",
        bsm: "BotoSesManager",
    ) -> T.Optional[dict]:
        """
        给 EC2 关联 EIP.
        """
        if self.config.ec2_eip_allocation_id is not None:
            return self.metadata.associate_eip_address(
                ec2_client=bsm.ec2_client,
                allocation_id=self.config.ec2_eip_allocation_id,
                check_exists=True,
            )
        return None

    def update_db_master_password(
        self: "Server",
        bsm: "BotoSesManager",
    ) -> T.Optional[dict]:
        """
        更新数据库的 master password.
        """
        return self.metadata.update_db_master_password(
            rds_client=bsm.rds_client,
            master_password=self.config.db_admin_password,
            check_exists=False,
        )

    @logger.emoji_block(
        msg="🔴🖥Stop EC2 instance",
        emoji="🖥",
    )
    def stop_ec2(
        self: "Server",
        bsm: "BotoSesManager",
        check: bool = True,
        wait: bool = True,
    ) -> "StopInstancesResultTypeDef":
        """
        关闭 EC2.
        """
        if check:
            self.ensure_ec2_is_ready_to_stop(bsm=bsm)
        ec2_inst = self.metadata.ec2_inst
        res = ec2_inst.stop_instance(ec2_client=bsm.ec2_client)
        if wait:
            ec2_inst.wait_for_stopped(ec2_client=bsm.ec2_client, timeout=300)
        return res

    @logger.emoji_block(
        msg="🔴🛢Stop RDS instance",
        emoji="🛢",
    )
    def stop_rds(
        self: "Server",
        bsm: "BotoSesManager",
        check: bool = True,
        wait: bool = True,
    ) -> "StopDBInstanceResultTypeDef":
        """
        关闭 RDS.
        """
        if check:
            self.ensure_rds_is_ready_to_stop(bsm=bsm)
        rds_inst = self.metadata.rds_inst
        res = rds_inst.stop_db_instance(rds_client=bsm.rds_client)
        if wait:
            rds_inst.wait_for_stopped(rds_client=bsm.rds_client, timeout=300)
        return res

    @logger.emoji_block(
        msg="🗑🖥Stop EC2 instance",
        emoji="🖥",
    )
    def delete_ec2(
        self: "Server",
        bsm: "BotoSesManager",
        check: bool = True,
    ) -> "TerminateInstancesResultTypeDef":
        """
        删除 EC2.
        """
        if check:
            self.ensure_ec2_exists(bsm=bsm)
        ec2_inst = self.metadata.ec2_inst
        res = ec2_inst.terminate_instance(ec2_client=bsm.ec2_client)
        return res

    @logger.emoji_block(
        msg="🗑🛢Delete EC2 instance",
        emoji="🛢",
    )
    def delete_rds(
        self: "Server",
        bsm: "BotoSesManager",
        create_final_snapshot: T.Optional[bool] = None,
        check: bool = True,
    ) -> "DeleteDBInstanceResultTypeDef":
        """
        删除 RDS.
        """
        if create_final_snapshot is None:
            create_final_snapshot = self.env_name == EnvEnum.prd.value
        if check:
            self.ensure_rds_exists(bsm=bsm)
        rds_inst = self.metadata.rds_inst
        if create_final_snapshot:
            snapshot_id = self._get_db_snapshot_id()
            res = rds_inst.delete_db_instance(
                rds_client=bsm.rds_client,
                skip_final_snapshot=False,
                final_db_snapshot_identifier=snapshot_id,
                delete_automated_backups=False,
            )
        else:
            res = rds_inst.delete_db_instance(
                rds_client=bsm.rds_client,
                skip_final_snapshot=True,
                delete_automated_backups=True,
            )
        return res

    @logger.emoji_block(
        msg="🗑🛢Delete EC2 instance",
        emoji="🛢",
    )
    def bootstrap(
        self: "Server",
        bsm: "BotoSesManager",
        python_version: str = "3.8",
        acore_soap_app_version: T.Optional[str] = None,
        acore_db_app_version: T.Optional[str] = None,
        acore_server_bootstrap_version: T.Optional[str] = None,
    ):
        """
        远程执行 EC2 引导程序.

        这个命令不会失败. 它只是一个 async API call.
        """
        bootstrap_command = self.build_bootstrap_command(
            python_version=python_version,
            acore_soap_app_version=acore_soap_app_version,
            acore_db_app_version=acore_db_app_version,
            acore_server_bootstrap_version=acore_server_bootstrap_version,
        )
        return ssm_better_boto.run_shell_script_async(
            ssm_client=bsm.ssm_client,
            commands=bootstrap_command,
            instance_ids=self.metadata.ec2_inst.id,
        )

    def run_check_server_status_cron_job(
        self: "Server",
        bsm: "BotoSesManager",
    ):
        """
        启动检测游戏服务器状态的定时任务.

        这个命令不会失败. 它只是一个 async API call.
        """
        return ssm_better_boto.run_shell_script_async(
            ssm_client=bsm.ssm_client,
            commands=(
                f"sudo -H -u ubuntu "
                f"{path_acore_server_bootstrap_cli} run_check_server_status_cron_job"
            ),
            instance_ids=self.metadata.ec2_inst.id,
        )

    def stop_check_server_status_cron_job(
        self: "Server",
        bsm: "BotoSesManager",
    ):
        """
        停止检测游戏服务器状态的定时任务.

        这个命令不会失败. 它只是一个 async API call.
        """
        return ssm_better_boto.run_shell_script_async(
            ssm_client=bsm.ssm_client,
            commands=(
                "sudo -H -u ubuntu "
                f"{path_acore_server_bootstrap_cli} stop_check_server_status_cron_job"
            ),
            instance_ids=self.metadata.ec2_inst.id,
        )

    def run_server(
        self: "Server",
        bsm: "BotoSesManager",
    ):
        """
        启动魔兽世界游戏服务器.

        这个命令不会失败. 它只是一个 async API call.
        """
        return ssm_better_boto.run_shell_script_async(
            ssm_client=bsm.ssm_client,
            commands=(
                f"sudo -H -u ubuntu " f"{path_acore_server_bootstrap_cli} run_server"
            ),
            instance_ids=self.metadata.ec2_inst.id,
        )

    def stop_server(
        self: "Server",
        bsm: "BotoSesManager",
    ):
        """
        停止魔兽世界游戏服务器.

        这个命令不会失败. 它只是一个 async API call.
        """
        return ssm_better_boto.run_shell_script_async(
            ssm_client=bsm.ssm_client,
            commands=(
                f"sudo -H -u ubuntu " f"{path_acore_server_bootstrap_cli} stop_server"
            ),
            instance_ids=self.metadata.ec2_inst.id,
        )

    @property
    def wow_status(self: "Server") -> str:
        """
        从 EC2 的 Tag 中获取魔兽世界服务器的状态.

        1. 如果 EC2 或 RDS 任意一个不存在或是已被删除 则返回 "deleted".
        2. 如果 EC2 或 RDS 不在线, 则返回 ``stopped``.
        3. 如果 EC2 或 RDS 都在线, tag 中不存在测量数据, 则返回 "stopped"
        4. 如果 EC2 或 RDS 都在线, tag 中有测量数据且没有过期, 则返回 tag 中的数据, 值可能是
            "123 players" (数字是在线人数), 或是 "stopped"
        5. 如果 EC2 或 RDS 都在线, tag 中有测量数据且过期了, 则返回 "stopped"
        """
        if self.metadata.is_exists() is False:
            return "deleted"
        elif self.metadata.is_running() is False:
            return "stopped"
        elif TagKey.WOW_STATUS not in self.metadata.ec2_inst.tags:
            return "stopped"
        else:
            wow_status = self.metadata.ec2_inst.tags[TagKey.WOW_STATUS]
            measure_time = self.metadata.ec2_inst.tags[TagKey.WOW_STATUS_MEASURE_TIME]
            measure_time = datetime.fromisoformat(measure_time)
            utc_now = datetime.utcnow().replace(tzinfo=timezone.utc)
            elapsed = (utc_now - measure_time).total_seconds()
            if elapsed > 300:
                return "stopped"
            else:
                return wow_status

    def create_ssh_tunnel(
        self: "Server",
        path_pem_file=default_path_pem_file,
    ):
        """
        创建一个本地的 SSH Tunnel, 用于本地数据库开发.
        """
        if self.metadata.is_running() is False:
            raise ConnectionError(
                "cannot create ssh tunnel, EC2 or RDS is not running."
            )
        acore_db_ssh_tunnel.create_ssh_tunnel(
            path_pem_file=path_pem_file,
            db_host=self.metadata.rds_inst.endpoint,
            db_port=DB_PORT,
            jump_host_username=EC2_USERNAME,
            jump_host_public_ip=self.metadata.ec2_inst.public_ip,
        )

    def list_ssh_tunnel(
        self: "Server",
        path_pem_file=default_path_pem_file,
    ):
        """
        列出所有正在运行中的 SSH Tunnel.
        """
        acore_db_ssh_tunnel.list_ssh_tunnel(path_pem_file)

    def test_ssh_tunnel(self: "Server"):
        """
        通过运行一个简单的 SQL 语句来测试 SSH Tunnel 是否正常工作.
        """
        if self.metadata.is_running() is False:
            raise ConnectionError("cannot test ssh tunnel, EC2 or RDS is not running.")
        acore_db_ssh_tunnel.test_ssh_tunnel(
            db_port=DB_PORT,
            db_username=self.config.db_username,
            db_password=self.config.db_password,
            db_name="acore_auth",
        )

    def kill_ssh_tunnel(
        self: "Server",
        path_pem_file=default_path_pem_file,
    ):
        """
        关闭所有正在运行中的 SSH Tunnel.
        """
        acore_db_ssh_tunnel.kill_ssh_tunnel(path_pem_file)

    @logger.emoji_block(
        msg="🆕🖥📸Create new EC2 AMI",
        emoji="📸",
    )
    def create_ec2_ami(
        self: "Server",
        bsm: "BotoSesManager",
        ami_name: T.Optional[str] = None,
        utc_now: T.Optional[datetime] = None,
        skip_reboot: bool = True,
        check: bool = True,
        wait: bool = True,
    ) -> "CreateImageResultTypeDef":
        """
        Create a new AMI from existing EC2.
        """
        if ami_name is None:
            ami_name = self._get_ec2_ami_name(utc_now)
        if check:
            ec2_inst = self.ensure_ec2_exists(bsm=bsm)
        else:
            ec2_inst = self.metadata.ec2_inst
        logger.info(
            f"create image {ami_name!r} from ec2 instance {self.metadata.ec2_inst.id}"
        )
        res = bsm.ec2_client.create_image(
            InstanceId=self.metadata.ec2_inst.id,
            Name=ami_name,
            NoReboot=skip_reboot,
            TagSpecifications=[
                {
                    "ResourceType": "image",
                    "Tags": [{"Key": k, "Value": v} for k, v in ec2_inst.tags.items()],
                }
            ],
        )
        ami_id = res["ImageId"]
        if wait:
            image = simple_aws_ec2.Image(id=ami_id)
            image.wait_for_available(ec2_client=bsm.ec2_client)
        else:
            logger.info("skip waiting for available")
        return res

    @logger.emoji_block(
        msg="🆕🛢📸Create new DB Snapshot",
        emoji="📸",
    )
    def create_db_snapshot(
        self: "Server",
        bsm: "BotoSesManager",
        snapshot_id: T.Optional[str] = None,
        check: bool = True,
        wait: bool = True,
    ) -> "CreateDBSnapshotResultTypeDef":
        if snapshot_id is None:
            snapshot_id = self._get_db_snapshot_id()
        if check:
            rds_inst = self.ensure_rds_exists(bsm=bsm)
        else:
            rds_inst = self.metadata.rds_inst
        logger.info(
            f"create db snapshot {snapshot_id!r} from db instance {rds_inst.id}"
        )
        res = bsm.rds_client.create_db_snapshot(
            DBSnapshotIdentifier=snapshot_id,
            DBInstanceIdentifier=rds_inst.id,
        )
        if wait:
            snap = simple_aws_rds.RDSDBSnapshot(db_snapshot_identifier=snapshot_id)
            snap.wait_for_available(rds_client=bsm.rds_client)
        else:
            logger.info("skip waiting for available")
        return res
