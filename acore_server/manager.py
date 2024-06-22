# -*- coding: utf-8 -*-

"""
todo: doctring
"""

import dataclasses
from functools import cached_property

from s3pathlib import S3Path
from boto_session_manager import BotoSesManager

from .wserver_infra_exports import StackExports
from .server import Server
from .fleet import Fleet


@dataclasses.dataclass
class Manager:
    """
    This manager class is to simplify executing Server workflow methods.

    See https://github.com/MacHu-GWU/acore_server-project/blob/main/debug/manager_server.py
    for an example of how to use this class.
    """

    aws_profile: str = dataclasses.field()
    env_name: str = dataclasses.field()

    @cached_property
    def bsm(self) -> "BotoSesManager":
        return BotoSesManager(profile_name=self.aws_profile)

    @cached_property
    def s3dir_env_workflow(self) -> S3Path:
        return S3Path(
            f"s3://{self.bsm.aws_account_alias}-{self.bsm.aws_region}-data"
            f"/projects/acore_server/workflows/{self.env_name}/"
        ).to_dir()

    @cached_property
    def stack_exports(self) -> StackExports:
        stack_exports = StackExports(env_name=self.env_name)
        stack_exports.load(cf_client=self.bsm.cloudformation_client)
        return stack_exports

    @cached_property
    def fleet(self) -> Fleet:
        return Fleet.get(bsm=self.bsm, env_name=self.env_name)

    @property
    def blue(self) -> Server:
        return self.fleet.get_server(server_id=f"{self.env_name}-blue")

    @property
    def green(self) -> Server:
        return self.fleet.get_server(server_id=f"{self.env_name}-green")

    @property
    def black(self) -> Server:
        return self.fleet.get_server(server_id=f"{self.env_name}-black")

    @property
    def white(self) -> Server:
        return self.fleet.get_server(server_id=f"{self.env_name}-white")

    @property
    def yellow(self) -> Server:
        return self.fleet.get_server(server_id=f"{self.env_name}-yellow")

    @property
    def orange(self) -> Server:
        return self.fleet.get_server(server_id=f"{self.env_name}-orange")
