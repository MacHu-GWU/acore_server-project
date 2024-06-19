# -*- coding: utf-8 -*-

"""
todo: doc string
"""

import typing as T
import dataclasses

from func_args import NOTHING, resolve_kwargs
from boto_session_manager import BotoSesManager

from acore_server_metadata.api import Server as ServerMetadata
from acore_server_config.api import ConfigLoader

from .server import Server


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
    ):
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
        """
        Get a server by its id.
        """
        return self.servers[server_id]
