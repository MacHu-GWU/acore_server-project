# -*- coding: utf-8 -*-

from rich import print as rprint
from boto_session_manager import BotoSesManager
from s3pathlib import S3Path
from acore_server.api import Fleet, InfraStackExports

server_id = "sbx-blue"
env_name, server_name = server_id.split("-", 1)
bsm = BotoSesManager(profile_name="bmt_app_dev_us_east_1")
fleet = Fleet.get(bsm=bsm, env_name=env_name)
server = fleet.get_server(server_id)

# rprint(server)
# rprint("--- Config:", server.config)
# rprint("--- Metadata:", server.metadata)
rprint(f"is_ec2_exists: {server.metadata.is_ec2_exists()}")
rprint(f"is_rds_exists: {server.metadata.is_rds_exists()}")
rprint(f"is_ec2_running: {server.metadata.is_ec2_running()}")
rprint(f"is_rds_running: {server.metadata.is_rds_running()}")


stack_exports = InfraStackExports(env_name=env_name)
stack_exports.load(cf_client=bsm.cloudformation_client)
s3dir_workflow = S3Path(
    f"s3://{bsm.aws_account_alias}-{bsm.aws_region}-data"
    f"/projects/acore_server/workflows/{env_name}/{server_id}/"
).to_dir()

# server.run_rds(bsm=bsm, stack_exports=stack_exports)
# server.run_ec2(
#     bsm=bsm,
#     stack_exports=stack_exports,
#     acore_soap_app_version="0.3.4",
#     acore_db_app_version="0.2.2",
#     acore_server_bootstrap_version="0.4.1",
# )

# server.start_ec2(bsm=bsm)
# server.start_rds(bsm=bsm)

# server.associate_eip_address(bsm=bsm
# server.update_db_master_password(bsm=bsm)
# server.bootstrap(bsm=bsm, acore_soap_app_version="0.3.2", acore_server_bootstrap_version="0.3.1")

# print(server.wow_status)

# server.stop_ec2(bsm=bsm)
# server.stop_rds(bsm=bsm)

# server.delete_ec2(bsm=bsm)
# server.delete_rds(bsm=bsm)

# server.run_check_server_status_cron_job(bsm=bsm)
# server.stop_check_server_status_cron_job(bsm=bsm)

# server.run_server(bsm=bsm)
# server.stop_server(bsm=bsm)

# server.create_ssh_tunnel()
# server.list_ssh_tunnel()
# server.kill_ssh_tunnel()
# server.test_ssh_tunnel()

workflow_id = "create_cloned_server-2024-06-19-04-27-00"
# server.create_cloned_server(
#     bsm=bsm,
#     workflow_id=workflow_id,
#     s3path_workflow=s3dir_workflow.joinpath(f"{workflow_id}.json"),
#     new_server_id="sbx-blue",
#     stack_exports=stack_exports,
#     skip_reboot=True,
#     delete_ami_afterwards=True,
#     delete_snapshot_afterwards=True,
# )

workflow_id = "delete_server-2024-06-20-11-14-00"
server.delete_server(
    bsm=bsm,
    workflow_id=workflow_id,
    s3path_workflow=s3dir_workflow.joinpath(f"{workflow_id}.json"),
    skip_reboot=True,
    create_backup_ec2_ami=False,
    create_backup_db_snapshot=False,
)
