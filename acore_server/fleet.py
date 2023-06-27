# -*- coding: utf-8 -*-

"""
todo: doc string
"""

import typing as T
import dataclasses
from datetime import datetime, timezone

from func_args import NOTHING, resolve_kwargs
from boto_session_manager import BotoSesManager

from acore_paths.api import (
    path_acore_server_bootstrap_cli,
)
from acore_constants.api import TagKey
from acore_server_metadata.api import Server as ServerMetadata
from acore_server_config.api import (
    Server as ServerConfig,
    ConfigLoader,
    EnvEnum,
)

from aws_ssm_run_command.api import better_boto as ssm_better_boto
from acore_db_ssh_tunnel import api as acore_db_ssh_tunnel

from .paths import path_pem_file as default_path_pem_file
from .constants import EC2_USERNAME, DB_PORT
from .wserver_infra_exports import StackExports


@dataclasses.dataclass
class Server:  # pragma: no cover
    """
    A data container that holds both the config and metadata of a server.

    Usage:

    .. code-block:: python

        >>> server = Server.get(bsm=..., server_id="sbx-blue", ...)

    Operate server methods:

    - :meth:`~Server.run_ec2`
    - :meth:`~Server.run_rds`
    - :meth:`~Server.start_ec2`
    - :meth:`~Server.start_rds`
    - :meth:`~Server.associate_eip_address`
    - :meth:`~Server.update_db_master_password`
    - :meth:`~Server.stop_ec2`
    - :meth:`~Server.stop_rds`
    - :meth:`~Server.delete_ec2`
    - :meth:`~Server.delete_rds`
    - :meth:`~Server.bootstrap`
    - :meth:`~Server.run_server`
    - :meth:`~Server.stop_server`
    - :meth:`~Server.count_online_player`
    - :meth:`~Server.create_ssh_tunnel`
    - :meth:`~Server.list_ssh_tunnel`
    - :meth:`~Server.test_ssh_tunnel`
    - :meth:`~Server.kill_ssh_tunnel`

    :param config: See https://acore-server-config.readthedocs.io/en/latest/acore_server_config/config/define/server.html#acore_server_config.config.define.server.Server
    :param metadata: See https://github.com/MacHu-GWU/acore_server_metadata-project/blob/main/acore_server_metadata/server/server.py
    """

    config: ServerConfig
    metadata: ServerMetadata

    @classmethod
    def get(
        cls,
        bsm: BotoSesManager,
        server_id: str,
        parameter_name_prefix: T.Optional[str] = NOTHING,
        s3folder_config: T.Optional[str] = NOTHING,
    ) -> "Server":
        env_name, server_name = server_id.split("-", 1)
        # get acore_server_config
        config_loader = ConfigLoader.new(
            **resolve_kwargs(
                env_name=env_name,
                parameter_name_prefix=parameter_name_prefix,
                s3folder_config=s3folder_config,
                bsm=bsm,
            )
        )
        server_config = config_loader.get_server(server_name=server_name)
        # get acore_server_metadata
        server_metadata = ServerMetadata.get_server(
            id=server_id,
            ec2_client=bsm.ec2_client,
            rds_client=bsm.rds_client,
        )
        # put them together
        server = Server(
            config=server_config,
            metadata=server_metadata,
        )
        return server

    @property
    def id(self) -> str:
        """
        Server id, the naming convention is ``${env_name}-${server_name}``
        """
        return self.config.id

    @property
    def env_name(self) -> str:
        """
        Environment name, e.g. ``sbx``, ``tst``, ``prd``.
        """
        return self.id.split("-", 1)[0]

    @property
    def server_name(self) -> str:
        """
        Server name, e.g. ``blue``, ``green``.
        """
        return self.id.split("-", 1)[1]

    @property
    def bootstrap_command(self) -> str:
        return (
            "sudo -H -u ubuntu /home/ubuntu/.pyenv/shims/python3.8 -c "
            '"$(curl -fsSL https://raw.githubusercontent.com/MacHu-GWU/acore_server_bootstrap-project/main/install.py)" '
            f"--acore_soap_app_version {self.config.acore_soap_app_version} "
            f"--acore_server_bootstrap_version {self.config.acore_server_bootstrap_version}"
        )

    def run_ec2(
        self,
        bsm: "BotoSesManager",
        stack_exports: "StackExports",
    ):
        user_data_lines = [
            "#!/bin/bash",
            self.bootstrap_command,
        ]
        return self.metadata.run_ec2(
            ec2_client=bsm.ec2_client,
            ami_id=self.config.ec2_ami_id,
            instance_type=self.config.ec2_instance_type,
            key_name=self.config.ec2_key_name,
            subnet_id=self.config.ec2_subnet_id,
            security_group_ids=[
                stack_exports.get_default_sg_id(server_id=self.id),
                stack_exports.get_ec2_sg_id(server_id=self.id),
                stack_exports.get_ssh_sg_id(),
            ],
            iam_instance_profile_arn=stack_exports.get_ec2_instance_profile_arn(),
            UserData="\n".join(user_data_lines),
            check_exists=False,
        )

    def run_rds(
        self,
        bsm: "BotoSesManager",
        stack_exports: "StackExports",
    ):
        return self.metadata.run_rds(
            rds_client=bsm.rds_client,
            db_snapshot_identifier=self.config.db_snapshot_id,
            db_instance_class=self.config.db_instance_class,
            db_subnet_group_name=stack_exports.get_db_subnet_group_name(),
            security_group_ids=[
                stack_exports.get_default_sg_id(server_id=self.id),
            ],
            multi_az=False,
            check_exists=False,
        )

    def start_ec2(
        self,
        bsm: "BotoSesManager",
    ):
        return self.metadata.start_ec2(ec2_client=bsm.ec2_client)

    def start_rds(
        self,
        bsm: "BotoSesManager",
    ):
        return self.metadata.start_rds(rds_client=bsm.rds_client)

    def associate_eip_address(
        self,
        bsm: "BotoSesManager",
    ) -> T.Optional[dict]:
        if self.config.ec2_eip_allocation_id is not None:
            return self.metadata.associate_eip_address(
                ec2_client=bsm.ec2_client,
                allocation_id=self.config.ec2_eip_allocation_id,
                check_exists=True,
            )
        return None

    def update_db_master_password(
        self,
        bsm: "BotoSesManager",
    ) -> T.Optional[dict]:
        return self.metadata.update_db_master_password(
            rds_client=bsm.rds_client,
            master_password=self.config.db_admin_password,
            check_exists=False,
        )

    def stop_ec2(
        self,
        bsm: "BotoSesManager",
    ):
        return self.metadata.stop_ec2(bsm.ec2_client)

    def stop_rds(
        self,
        bsm: "BotoSesManager",
    ):
        return self.metadata.stop_rds(bsm.rds_client)

    def delete_ec2(
        self,
        bsm: "BotoSesManager",
    ):
        return self.metadata.delete_ec2(bsm.ec2_client)

    def delete_rds(
        self,
        bsm: "BotoSesManager",
    ):
        create_final_snapshot = self.env_name == EnvEnum.prd.value
        return self.metadata.delete_rds(
            bsm.rds_client,
            create_final_snapshot=create_final_snapshot,
        )

    def bootstrap(
        self,
        bsm: "BotoSesManager",
    ):
        """
        这个命令不会失败. 它只是一个 async API call.
        """
        return ssm_better_boto.send_command(
            ssm_client=bsm.ssm_client,
            instance_id=self.metadata.ec2_inst.id,
            commands=[
                self.bootstrap_command,
            ],
        )

    def run_server(
        self,
        bsm: "BotoSesManager",
    ):
        """
        这个命令不会失败. 它只是一个 async API call.
        """
        return ssm_better_boto.send_command(
            ssm_client=bsm.ssm_client,
            instance_id=self.metadata.ec2_inst.id,
            commands=[
                f"{path_acore_server_bootstrap_cli} run_server",
            ],
        )

    def stop_server(
        self,
        bsm: "BotoSesManager",
    ):
        """
        这个命令不会失败. 它只是一个 async API call.
        """
        return ssm_better_boto.send_command(
            ssm_client=bsm.ssm_client,
            instance_id=self.metadata.ec2_inst.id,
            commands=[
                f"{path_acore_server_bootstrap_cli} stop_server",
            ],
        )

    @property
    def wow_status(self) -> str:
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
        self,
        path_pem_file=default_path_pem_file,
    ):
        """
        创建一个本地的 SSH Tunnel, 用于本地数据库开发.
        """
        if self.metadata.is_running() is False:
            raise ConnectionError("cannot create ssh tunnel, EC2 or RDS is not running.")
        acore_db_ssh_tunnel.create_ssh_tunnel(
            path_pem_file=path_pem_file,
            db_host=self.metadata.rds_inst.endpoint,
            db_port=DB_PORT,
            jump_host_username=EC2_USERNAME,
            jump_host_public_ip=self.metadata.ec2_inst.public_ip,
        )

    def list_ssh_tunnel(
        self,
        path_pem_file=default_path_pem_file,
    ):
        """
        列出所有正在运行中的 SSH Tunnel.
        """
        acore_db_ssh_tunnel.list_ssh_tunnel(path_pem_file)

    def test_ssh_tunnel(self):
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
        self,
        path_pem_file=default_path_pem_file,
    ):
        """
        关闭所有正在运行中的 SSH Tunnel.
        """
        acore_db_ssh_tunnel.kill_ssh_tunnel(path_pem_file)


@dataclasses.dataclass
class Fleet:  # pragma: no cover
    """
    Fleet of server for a given environment.

    It is just a dictionary containing all servers' data. key is ``server_id``
    value is the :class:`Server` object.

    Usage:

    .. code-block:: python

        >>> fleet = Fleet.get(bsm=..., env_name="sbx", ...)
        >>> server = fleet.get_server(server_id="sbx-blue")
    """

    servers: T.Dict[str, Server] = dataclasses.field(init=False)

    @classmethod
    def get(
        cls,
        bsm: BotoSesManager,
        env_name: str,
        parameter_name_prefix: T.Optional[str] = NOTHING,
        s3folder_config: T.Optional[str] = NOTHING,
    ) -> "Fleet":
        """
        Load all servers' data for a given environment efficiently.
        """
        # get acore_server_config
        config_loader = ConfigLoader.new(
            **resolve_kwargs(
                env_name=env_name,
                parameter_name_prefix=parameter_name_prefix,
                s3folder_config=s3folder_config,
                bsm=bsm,
            )
        )
        server_id_list = [server.id for _, server in config_loader.iter_servers()]
        # get acore_server_metadata
        server_metadata_mapper = ServerMetadata.batch_get_server(
            ids=server_id_list,
            ec2_client=bsm.ec2_client,
            rds_client=bsm.rds_client,
        )
        # put them together
        servers = dict()
        for server_id in server_id_list:
            server_name = server_id.split("-", 1)[1]
            metadata = server_metadata_mapper.get(server_id)
            if metadata is None:
                metadata = ServerMetadata(id=server_id)
            server = Server(
                config=config_loader.get_server(server_name=server_name),
                metadata=metadata,
            )
            servers[server_id] = server

        fleet = cls()
        fleet.servers = servers
        return fleet

    def get_server(self, server_id: str) -> Server:
        return self.servers[server_id]
