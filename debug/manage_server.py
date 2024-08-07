# -*- coding: utf-8 -*-

"""
这个脚本是用来对单台服务器进行管理的脚本. 可以方便的执行
`server operation 或是 workflow <https://acore-server.readthedocs.io/en/latest/search.html?q=Operation+and+Workflow&check_keywords=yes&area=default>`_
"""

from acore_server.api import Manager


# ------------------------------------------------------------------------------
# PLEASE DOUBLE CHECK TO MAKE SURE YOU ARE WORKING ON THE RIGHT SERVER
# ------------------------------------------------------------------------------
env_name = "sbx"
manager = Manager(aws_profile="bmt_app_dev_us_east_1", env_name=env_name)
server = manager.blue

# server.show_server_config()
# server.show_server_status()
# server.show_aws_link(bsm=manager.bsm)

# server.associate_eip_address(bsm=manager.bsm, allow_reassociation=True)
# server.update_db_master_password(bsm=manager.bsm)

# server.create_ssh_tunnel(bsm=manager.bsm)
# server.list_ssh_tunnel(bsm=manager.bsm)
# server.kill_ssh_tunnel(bsm=manager.bsm)
# server.test_ssh_tunnel()

# ------------------------------------------------------------------------------
# Create Cloned Server
# ------------------------------------------------------------------------------
# workflow_id = "create_cloned_server-2024-07-26-15-24-00"
# server.create_cloned_server(
#     bsm=manager.bsm,
#     workflow_id=workflow_id,
#     s3path_workflow=manager.s3dir_env_workflow.joinpath(
#         server.server_name, f"{workflow_id}.json"
#     ),
#     new_server_id="sbx-black",
#     stack_exports=manager.stack_exports,
#     skip_reboot=True,
#     delete_ami_afterwards=False,
#     delete_snapshot_afterwards=False,
# )


# ------------------------------------------------------------------------------
# Create Updated Server
# ------------------------------------------------------------------------------
# workflow_id = "create_updated_server-2024-07-26-15-24-00"
# server.create_updated_server(
#     bsm=manager.bsm,
#     workflow_id=workflow_id,
#     s3path_workflow=manager.s3dir_env_workflow.joinpath(
#         server.env_name, f"{workflow_id}.json"
#     ),
#     new_server_id="sbx-blue",
#     ami_id="ami-0168d2b22c6ff633e",
#     stack_exports=manager.stack_exports,
#     snapshot_id="sbx-blue-snapshot-final-2024-07-26",
#     delete_snapshot_afterwards=False,
# )


# ------------------------------------------------------------------------------
# Delete Server
# ------------------------------------------------------------------------------
# workflow_id = "delete_server-2024-06-20-04-19-00"
# server.delete_server(
#     bsm=manager.bsm,
#     workflow_id=workflow_id,
#     s3path_workflow=manager.s3dir_env_workflow.joinpath(
#         server.server_name, f"{workflow_id}.json"
#     ),
#     skip_reboot=True,
#     create_backup_ec2_ami=False,
#     create_backup_db_snapshot=False,
# )


# ------------------------------------------------------------------------------
# Stop Server
# ------------------------------------------------------------------------------
# server.stop_server(bsm=manager.bsm)


# ------------------------------------------------------------------------------
# Start Server
# ------------------------------------------------------------------------------
# server.start_server(bsm=manager.bsm)
