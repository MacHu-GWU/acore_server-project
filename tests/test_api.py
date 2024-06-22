# -*- coding: utf-8 -*-

from acore_server import api


def test():
    _ = api
    _ = api.Server
    _ = api.Fleet
    _ = api.InfraStackExports

    _ = api.Server
    _ = api.Server.id
    _ = api.Server.env_name
    _ = api.Server.server_name
    _ = api.Server.create_ec2
    _ = api.Server.create_rds_from_scratch
    _ = api.Server.create_rds_from_snapshot
    _ = api.Server.start_ec2
    _ = api.Server.start_rds
    _ = api.Server.associate_eip_address
    _ = api.Server.update_db_master_password
    _ = api.Server.stop_ec2
    _ = api.Server.stop_rds
    _ = api.Server.delete_ec2
    _ = api.Server.delete_rds
    _ = api.Server.wow_status
    _ = api.Server.create_ssh_tunnel
    _ = api.Server.list_ssh_tunnel


if __name__ == "__main__":
    from acore_server.tests import run_cov_test

    run_cov_test(__file__, "acore_server.api", preview=False)
