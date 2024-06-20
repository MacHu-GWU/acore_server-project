# -*- coding: utf-8 -*-

from acore_server.api import Manager


manager = Manager(aws_profile="bmt_app_dev_us_east_1", env_name="sbx")
server = manager.green
server.show_server_config()
server.show_server_status()

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


# ------------------------------------------------------------------------------
# Create Cloned Server
# ------------------------------------------------------------------------------
workflow_id = "create_cloned_server-2024-06-19-04-27-00"
server.create_cloned_server(
    bsm=manager.bsm,
    workflow_id=workflow_id,
    s3path_workflow=manager.s3dir_env_workflow.joinpath(
        server.server_name, f"{workflow_id}.json"
    ),
    new_server_id="sbx-blue",
    stack_exports=manager.stack_exports,
    skip_reboot=True,
    delete_ami_afterwards=True,
    delete_snapshot_afterwards=True,
)

# ------------------------------------------------------------------------------
# Create Updated Server
# ------------------------------------------------------------------------------
# workflow_id = "create_cloned_server-2024-06-20-02-46-00"
# server.create_updated_server(
#     bsm=manager.bsm,
#     workflow_id=workflow_id,
#     s3path_workflow=manager.s3dir_env_workflow.joinpath(
#         server.env_name, f"{workflow_id}.json"
#     ),
#     new_server_id="sbx-blue",
#     ami_id="ami-0452e5248cdce53f2",
#     stack_exports=manager.stack_exports,
#     snapshot_id="rds:sbx-green-2024-06-19-04-50",
#     delete_snapshot_afterwards=False,
# )


# workflow_id = "delete_server-2024-06-20-11-14-00"
# server.delete_server(
#     bsm=bsm,
#     workflow_id=workflow_id,
#     s3path_workflow=s3dir_workflow.joinpath(f"{workflow_id}.json"),
#     skip_reboot=True,
#     create_backup_ec2_ami=False,
#     create_backup_db_snapshot=False,
# )
