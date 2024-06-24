# -*- coding: utf-8 -*-

"""
todo: doc string
"""

import typing as T
import json
import dataclasses
from boto_session_manager import BotoSesManager
from aws_console_url.api import AWSConsole

try:
    from rich import print as rprint
except ImportError:
    pass

from .logger import logger


if T.TYPE_CHECKING:  # pragma: no cover
    from .server import Server


class ServerHelperMixin:  # pragma: no cover
    """
    Server Helper Mixin class that contains all the server helper methods.
    """

    @logger.emoji_block(
        msg="🔍🛠Show server config",
        emoji="🔍",
    )
    def show_server_config(
        self: "Server",
    ):
        logger.info(json.dumps(dataclasses.asdict(self.config), indent=4))

    @logger.emoji_block(
        msg="🔍🖥🛢Show server status",
        emoji="🔍",
    )
    def show_server_status(
        self: "Server",
    ):
        logger.info(f"🖥is_ec2_exists: {self.metadata.is_ec2_exists()}")
        logger.info(f"🛢is_rds_exists: {self.metadata.is_rds_exists()}")
        logger.info(f"🖥is_ec2_running: {self.metadata.is_ec2_running()}")
        logger.info(f"🛢is_rds_running: {self.metadata.is_rds_running()}")
        if self.metadata.is_ec2_running():
            logger.info(f"🖥public_ip: {self.metadata.ec2_inst.public_ip}")

    @logger.emoji_block(
        msg="🔍🛠Show server config",
        emoji="🔍",
    )
    def show_aws_link(
        self: "Server",
        bsm: "BotoSesManager"
    ):
        aws_console = AWSConsole.from_bsm(bsm=bsm)
        if self.metadata.is_ec2_exists():
            url = aws_console.ec2.get_instance(self.metadata.ec2_inst.id)
            logger.info(f"🌐🖥preview EC2: {url}")
        else:
            logger.info("🛑EC2 does not exist")
        if self.metadata.is_rds_exists():
            url = aws_console.rds.get_database_instance(self.metadata.rds_inst.id)
            logger.info(f"🌐🖥preview RDS: {url}")
        else:
            logger.info("🛑RDS does not exist!")
