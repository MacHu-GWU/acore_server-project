# -*- coding: utf-8 -*-

"""
See :class:`Server` for more details.
"""

import typing as T
import dataclasses

from func_args import NOTHING, resolve_kwargs
from boto_session_manager import BotoSesManager

from acore_server_metadata.api import Server as ServerMetadata
from acore_server_config.api import (
    Server as ServerConfig,
    Ec2ConfigLoader,
    ConfigLoader,
)

from .server_operation_mixin import ServerOperationMixin
from .server_workflow_mixin import ServerWorkflowMixin
from .server_helper_mixin import ServerHelperMixin


@dataclasses.dataclass
class Server(
    ServerOperationMixin,
    ServerWorkflowMixin,
    ServerHelperMixin,
):  # pragma: no cover
    """
    A data container that holds both the config and metadata of a server.

    Usage:

    .. code-block:: python

        # if you are on develop's laptop or lambda
        >>> server = Server.get(bsm=..., server_id="sbx-blue", ...)
        # if you are on game server EC2
        >>> server = Server.from_ec2_inside()

    Server operation methods:

    - :meth:`Server.run_ec2 <acore_server.server_operation_mixin.ServerOperationMixin.run_ec2`
    - :meth:`Server.run_rds <acore_server.server_operation_mixin.ServerOperationMixin.run_rds`
    - :meth:`Server.start_ec2 <acore_server.server_operation_mixin.ServerOperationMixin.start_ec2`
    - :meth:`Server.start_rds <acore_server.server_operation_mixin.ServerOperationMixin.start_rds`
    - :meth:`Server.associate_eip_address <acore_server.server_operation_mixin.ServerOperationMixin.associate_eip_address`
    - :meth:`Server.update_db_master_password <acore_server.server_operation_mixin.ServerOperationMixin.update_db_master_password`
    - :meth:`Server.stop_ec2 <acore_server.server_operation_mixin.ServerOperationMixin.stop_ec2`
    - :meth:`Server.stop_rds <acore_server.server_operation_mixin.ServerOperationMixin.stop_rds`
    - :meth:`Server.delete_ec2 <acore_server.server_operation_mixin.ServerOperationMixin.delete_ec2`
    - :meth:`Server.delete_rds <acore_server.server_operation_mixin.ServerOperationMixin.delete_rds`
    - :meth:`Server.bootstrap <acore_server.server_operation_mixin.ServerOperationMixin.bootstrap`
    - :meth:`Server.run_server <acore_server.server_operation_mixin.ServerOperationMixin.run_server`
    - :meth:`Server.stop_server <acore_server.server_operation_mixin.ServerOperationMixin.stop_server`
    - :meth:`Server.count_online_player <acore_server.server_operation_mixin.ServerOperationMixin.count_online_player`
    - :meth:`Server.create_ssh_tunnel <acore_server.server_operation_mixin.ServerOperationMixin.create_ssh_tunnel`
    - :meth:`Server.list_ssh_tunnel <acore_server.server_operation_mixin.ServerOperationMixin.list_ssh_tunnel`
    - :meth:`Server.test_ssh_tunnel <acore_server.server_operation_mixin.ServerOperationMixin.test_ssh_tunnel`
    - :meth:`Server.kill_ssh_tunnel <acore_server.server_operation_mixin.ServerOperationMixin.kill_ssh_tunnel`

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
    ):
        """
        指定一个 server_id, 读取它的 config 和 metadata, 然后返回一个 Server 对象.

        :param bsm: BotoSesManager 对象
        :param server_id: server id, the naming convention is ``${env_name}-${server_name}``
        :param parameter_name_prefix: see
            https://acore-server-config.readthedocs.io/en/latest/acore_server_config/config/loader.html#acore_server_config.config.loader.get_config
        :param s3folder_config: see
            https://acore-server-config.readthedocs.io/en/latest/acore_server_config/config/loader.html#acore_server_config.config.loader.get_config
        """
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
        server = cls(
            config=server_config,
            metadata=server_metadata,
        )
        return server

    @classmethod
    def from_ec2_inside(cls):
        """
        用 "自省" 的方式从 EC2 instance 里面读取 server_id, 读取 config 和 metadata,
        然后返回一个 Server 对象.
        """
        server_metadata = ServerMetadata.from_ec2_inside()
        server_config = Ec2ConfigLoader.load(server_id=server_metadata.id)
        # put them together
        server = cls(
            config=server_config,
            metadata=server_metadata,
        )
        return server

    @property
    def id(self) -> str:
        """
        Server id, the naming convention is ``${env_name}-${server_name}``
        """
        return self.metadata.id

    @property
    def env_name(self) -> str:
        """
        Environment name, e.g. ``sbx``, ``tst``, ``prd``.
        """
        return self.metadata.env_name

    @property
    def server_name(self) -> str:
        """
        Server name, e.g. ``blue``, ``green``.
        """
        return self.metadata.server_name
