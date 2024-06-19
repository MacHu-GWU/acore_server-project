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

from .paths import path_pem_file as default_path_pem_file
from .constants import EC2_USERNAME, DB_PORT
from .exc import (
    ServerNotFoundError,
    ServerAlreadyExistsError,
    FailedToStartServerError,
    FailedToStopServerError,
)
from .logger import logger
from .wserver_infra_exports import StackExports


if T.TYPE_CHECKING:  # pragma: no cover
    from .server import Server
    from mypy_boto3_rds.type_defs import CreateDBSnapshotResultTypeDef


class ServerWorkflowMixin:  # pragma: no cover
    """
    Server Workflow Mixin class that contains all the server workflow methods.
    """

    def ensure_server_is_ready_for_clone(
        self: "Server",
        bsm: "BotoSesManager",
    ) -> T.Tuple[simple_aws_ec2.Ec2Instance, simple_aws_rds.RDSDBInstance]:
        ec2_inst = self.ensure_rds_exists(bsm=bsm)
        rds_inst = self.ensure_rds_exists(bsm=bsm)
        return ec2_inst, rds_inst

    @logger.emoji_block(
        msg="🧬🖥🛢️Clone Server",
        emoji="🧬",
    )
    def clone_server(
        self: "Server",
        bsm: "BotoSesManager",
        new_server_id: str,
        stack_exports: "StackExports",
        skip_reboot: bool = False,
        delete_ami_afterwards: bool = False,
        delete_snapshot_afterwards: bool = False,
    ):
        logger.info(f"Clone from {self.id!r} to {new_server_id!r}")

        logger.info("Check old server status ...")
        ec2_inst, rds_inst = self.ensure_server_is_ready_for_clone(bsm=bsm)
        logger.info("✅ old server is running fine.")

        logger.info("Check new server configurations ...")
        new_server = self.get(bsm=bsm, server_id=new_server_id)
        if new_server.config.is_ready_for_create_cloned_server() is False:
            raise ValueError("server config is not ready for create cloned server")
        logger.info("✅ new server configuration is fine.")

        logger.info("Check new server status ...")
        new_server.ensure_ec2_not_exists(bsm=bsm)
        new_server.ensure_rds_not_exists(bsm=bsm)
        logger.info("✅ new server not exists, ready to create clone.")

        with logger.nested():
            res = self.create_ec2_ami(bsm=bsm, skip_reboot=skip_reboot, wait=False)
            ami_id = res["ImageId"]
            logger.info(f"Created EC2 AMI {ami_id!r}")

        with logger.nested():
            res = self.create_db_snapshot(bsm=bsm, wait=False)
            snapshot_id = res["DBSnapshot"]["DBSnapshotIdentifier"]
            logger.info(f"Created DB Snapshot {snapshot_id!r}")

        with logger.nested():
            logger.info("wait for DB Snapshot to be available ...")
            snapshot = simple_aws_rds.RDSDBSnapshot(db_snapshot_identifier=snapshot_id)
            snapshot.wait_for_available(rds_client=bsm.rds_client)

        with logger.nested():
            res = self.create_rds_from_snapshot(
                bsm=bsm,
                stack_exports=stack_exports,
                db_snapshot_id=snapshot_id,
                check=True,
                wait=True,
            )

        with logger.nested():
            logger.info("wait for EC2 AMI to be available ...")
            image = simple_aws_ec2.Image(id=ami_id)
            image.wait_for_available(ec2_client=bsm.ec2_client)

        with logger.nested():
            res = self.create_ec2(
                bsm=bsm,
                stack_exports=stack_exports,
                ami_id=ami_id,
                check=True,
                wait=True,
            )

        if delete_ami_afterwards:
            logger("Delete AMI ...")
            image.deregister(
                ec2_client=bsm.ec2_client,
                delete_snapshot=True,
                skip_prompt=True,
            )
            logger("✅Done")

        if delete_snapshot_afterwards:
            logger("Delete Snapshot ...")
            bsm.rds_client.delete_db_snapshot(
                DBSnapshotIdentifier=snapshot_id,
            )
            logger("✅Done")
