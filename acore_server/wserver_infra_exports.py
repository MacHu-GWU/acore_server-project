# -*- coding: utf-8 -*-

"""
This module provides an interface for external code to read cloudformation output.
via export name. You can just copy and paste this file into the external codebase.
"""

import typing as T
import dataclasses

project_name = "wserver_infra"  # this value has to match the ``config.project_name``
project_name_snake = project_name.replace("-", "_")
project_name_slug = project_name.replace("_", "-")


@dataclasses.dataclass
class StackExports:
    """
    Read cloudformation output values from ``wserver-infra-{self.env_name}`` stack.

    Usage:

    .. code-block:: python

        >>> import boto3
        >>> cf_client = boto3.client("cloudformation")
        >>> stack_exports = StackExports(env_name="sbx")
        >>> stack_exports.load(cf_client)
        >>> stack_exports.get_db_subnet_group_name()
        ...
        >>> stack_exports.get_ssh_sg_id()
        ...
        >>> stack_exports.get_default_sg_id(server_id="sbx-blue")
        ...
        >>> stack_exports.get_ec2_sg_id(server_id="sbx-blue")
        ...
        >>> stack_exports.get_ec2_iam_role_arn()
        ...
        >>> stack_exports.get_ec2_instance_profile_arn()
        ...

    :param env_name: environment name, sbx, tst, prd, etc ...
    :param _outputs: internal cache, don't use it directly.
    :param _exports: internal cache, don't use it directly.
    """

    env_name: str = dataclasses.field()
    _outputs: T.Dict[str, str] = dataclasses.field(default_factory=dict)
    _exports: T.Dict[str, str] = dataclasses.field(default_factory=dict)

    @property
    def prefix_name_snake(self) -> str:  # pragma: no cover
        return f"{project_name_snake}-{self.env_name}"

    @property
    def prefix_name_slug(self) -> str:  # pragma: no cover
        return f"{project_name_slug}-{self.env_name}"

    @property
    def stack_name(self) -> str:
        return self.prefix_name_slug

    def load(self, cf_client):
        res = cf_client.describe_stacks(StackName=self.stack_name)
        output_list = res["Stacks"][0]["Outputs"]
        outputs = {dct["OutputKey"]: dct["OutputValue"] for dct in output_list}
        exports = {dct["ExportName"]: dct["OutputValue"] for dct in output_list}
        self._outputs = outputs
        self._exports = exports

    # --------------------------------------------------------------------------
    # access output value via export name
    # --------------------------------------------------------------------------
    def get_db_subnet_group_name(self) -> str:
        return self._exports[
            f"{self.prefix_name_slug}-db-subnet-group-name-for-private-db"
        ]

    def get_ssh_sg_id(self) -> str:
        return self._exports[f"{self.prefix_name_slug}-sg-ssh-id"]

    def get_default_sg_id(self, server_id: str) -> str:
        return self._exports[f"{self.prefix_name_slug}-{server_id}-sg-default-id"]

    def get_ec2_sg_id(self, server_id: str) -> str:
        return self._exports[f"{self.prefix_name_slug}-{server_id}-sg-ec2-id"]

    def get_ec2_iam_role_arn(self) -> str:
        return self._exports[f"{self.prefix_name_slug}-ec2-iam-role-arn"]

    def get_ec2_instance_profile_arn(self) -> str:
        return self._exports[f"{self.prefix_name_slug}-instance-profile-arn"]
