# -*- coding: utf-8 -*-

from rich import print as rprint
from boto_session_manager import BotoSesManager
from acore_server.api import Fleet, InfraStackExports

server_id = "sbx-blue"
env_name, server_name = server_id.split("-", 1)
bsm = BotoSesManager(profile_name="bmt_app_dev_us_east_1")
fleet = Fleet.get(bsm=bsm, env_name=env_name)
server = fleet.get_server(server_id)

rprint(server)
# rprint("--- Config:", server.config)
# rprint("--- Metadata:", server.metadata)
rprint(f"is_ec2_exists: {server.metadata.is_ec2_exists()}")
rprint(f"is_rds_exists: {server.metadata.is_rds_exists()}")
rprint(f"is_ec2_running: {server.metadata.is_ec2_running()}")
rprint(f"is_rds_running: {server.metadata.is_rds_running()}")


stack_exports = InfraStackExports(env_name=env_name)
stack_exports.load(cf_client=bsm.cloudformation_client)

# server.run_ec2(bsm=bsm, stack_exports=stack_exports)
# server.run_rds(bsm=bsm, stack_exports=stack_exports)

# server.start_ec2(bsm=bsm)
# server.start_rds(bsm=bsm)

# server.associate_eip_address(bsm=bsm)
# server.update_db_master_password(bsm=bsm)
# server.bootstrap(bsm=bsm)

# print(server.wow_status)

# server.stop_ec2(bsm=bsm)
# server.stop_rds(bsm=bsm)

# server.delete_ec2(bsm=bsm)
# server.delete_rds(bsm=bsm)

# server.run_server(bsm=bsm)
# server.stop_server(bsm=bsm)

# server.create_ssh_tunnel()
# server.list_ssh_tunnel()
# server.kill_ssh_tunnel()
# server.test_ssh_tunnel()
