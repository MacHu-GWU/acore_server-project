Operation and Workflow
==============================================================================


What is Operation and Workflow
------------------------------------------------------------------------------
这个库的核心对象是 :class:`~acore_server.server.Server`, 它是一个游戏服务器的抽象, 并且提高了许多操作服务器的方法. 这些方法被分为两类:

1. **Operation**: 对游戏服务器的一个操作, 通常这个操作是一个原子操作, 例如启动 EC2, 关闭 EC2. :class:`~acore_server.server_operation.ServerOperationMixin` 实现了所有的 operation.
2. **Workflow**: 为了达到特定目的对游戏服务器的一系列操作. 例如启动一个新的游戏服务器就包括启动 RDS, 等待 RDS 启动完成, 启动 EC2, 等待 EC2 启动完成这一系列操作. :class:`~acore_server.server_workflow.ServerWorkflowMixin` 实现了所有的 workflow.


.. _create-new-server:

Workflow 1 - Create New Server
------------------------------------------------------------------------------
.. admonition:: 任务
    :class: note

    用一个刚编译好的新的游戏服务器核心 (一个 EC2 AMI) 创建新的 EC2, 创建一个全新的 RDS Instance, 把两者合起来作为一个新的游戏服务器.

.. admonition:: 使用场景
    :class: tip

    通常用于开一个全新的服务器的情况, 也就是开服的时候上面没有任何玩家数据的情况.

.. admonition:: 步骤

    - 检查这个新的游戏服务器是否已经存在.
    - 检查这个新的游戏服务器的配置是否已经存在, 并且通过了 validation.
    - 使用指定的 Configuration 创建新的 DB Instance
    - 等待 DB Instance 的状态变成 available.
    - 使用刚编译好的核心的 AMI 创建新的 EC2 Instance, 并使用 bootstrap 脚本初始化.
    - 等待 EC2 Instance 的状态变成 running, 并且游戏服务器启动成功.


.. _create-cloned-server:

Workflow 2 - Create Cloned Server
------------------------------------------------------------------------------
.. admonition:: 目标
    :class: note

    用一个运行良好的游戏服务器, 创建一个和它一摸一样的镜像.

.. admonition:: 使用场景
    :class: tip

    通常用于为已经存在的服务器修改配置, 或是测试 lua 脚本, 或是修改数据库中的数据.

.. admonition:: 步骤

    - 检查这个新的游戏服务器是否已经存在.
    - 检查这个新的游戏服务器的配置是否已经存在, 并且通过了 validation.
    - 用已有的 DB Instance 创建一个 Snapshot.
    - (Optional) 停止已有的 EC2 Instance. 因为创建 AMI 的过程中如果 EC2 还是很活跃, 可能会导致数据不一致的情况. 虽然 AWS 允许你在不停机的情况下创建 AMI, 但是我还是推荐先停止已有的 EC2 Instance.
    - 用已有的 EC2 Instance 创建一个 AMI.
    - 等待 Snapshot 的状态变成 available.
    - 等待 AMI 的状态变成 available.
    - 用新创建的 Snapshot 创建 DB Instance. 无需等待 AMI 的状态变成 available, 只要 snapshot 的状态变成 available 就可以创建 DB Instance 了.
    - 等待 DB Instance 状态变成 available.
    - 使用指定的 AMI 创建新的 EC2 Instance, 并使用 bootstrap 脚本初始化.
    - 等待 EC2 Instance 的状态变成 running, 并且游戏服务器启动成功.


.. _create-updated-server:

Workflow 3 - Create Updated Server
------------------------------------------------------------------------------
.. admonition:: 目标
    :class: note

    用一个运行良好的游戏服务器的数据库 snapshot 和一个刚编译好的游戏服务器核心 (一个 EC2 AMI), 创建一个新的服务器.

.. admonition:: 使用场景
    :class: tip

    通常用于 azerothcore 的升级. See `How to update AzerothCore to the latest stable version <https://www.azerothcore.org/wiki/update>`_.

.. admonition:: 步骤

    - 检查这个新的游戏服务器是否已经存在.
    - 检查这个新的游戏服务器的配置是否已经存在, 并且通过了 validation.
    - 用已有的 DB Instance 创建一个 Snapshot.
    - 等待 Snapshot 的状态变成 available.
    - 用新创建的 Snapshot 创建 DB Instance.
    - 等待 DB Instance 状态变成 available.
    - 使用刚编译好的核心的 AMI 创建新的 EC2 Instance, 并使用 bootstrap 脚本初始化.
    - 等待 EC2 Instance 的状态变成 running, 并且游戏服务器启动成功.


.. _stop-server:

Workflow 4 - Stop Server
------------------------------------------------------------------------------
.. admonition:: 目标
    :class: note

    关闭一个运行良好的游戏服务器和数据库.

.. admonition:: 使用场景
    :class: tip

    通常用于服务器停机维护, 或者在没有玩家的时候关闭服务器以节约成本.

.. admonition:: 步骤

    - 检查这个游戏服务器是否已经存在. 只有已经存在并运行良好的服务器彩可以被关闭. 但这不是必须得, 我们也可以 force 关闭.
    - 检查这个游戏服务器的配置是否已经存在, 并且通过了 validation.
    - 用 AWS SSM Run Command 远程 `关闭 screen session <https://github.com/MacHu-GWU/acore_server_bootstrap-project/blob/main/acore_server_bootstrap/vendor/screen_session_manager.py#L60>`_ 来关闭 worldserver 和 authserver.
    - 再关闭 EC2 Instance.
    - 再关闭 DB Instance.


.. _start-server:

Workflow 5 - Start Server
------------------------------------------------------------------------------
.. admonition:: 目标
    :class: note

    把一个已经关闭的游戏服务器和数据库重新启动.

.. admonition:: 使用场景
    :class: tip

    通常用于在服务器停机维护之后重新启动服务器, 或是准备开始玩游戏的时候重新启动服务器.

.. admonition:: 步骤

    - 检查这个游戏服务器是否已经存在. 只有已经存在并处于停机状态的服务器才可以被启动.
    - 检查这个游戏服务器的配置是否已经存在, 并且通过了 validation.
    - 用 AWS SSM Run Command 远程 `关闭 screen session <https://github.com/MacHu-GWU/acore_server_bootstrap-project/blob/main/acore_server_bootstrap/vendor/screen_session_manager.py#L60>`_ 来关闭 worldserver 和 authserver.
    - 再关闭 EC2 Instance.
    - 再关闭 DB Instance.


.. _delete-server:

Workflow 6 - Delete Server
------------------------------------------------------------------------------
.. admonition:: 目标
    :class: note

    彻底删除一个游戏服务器以及对应的数据库.

.. admonition:: 使用场景
    :class: tip

    通常在临时的开发服务器上完成了开发和测试之后, 已经保存了代码和数据, 就可以删除这个服务器了.

.. admonition:: 步骤

    - 检查这个游戏服务器是否已经存在. 只有已经存在才可以被删除.
    - (optional) 为 EC2 创建一个 AMI 备份, 并等待 AMI 的状态变成 available.
    - (optional) 为 RDS 创建一个 Snapshot 备份, 并等待 Snapshot 的状态变成 available.
    - 彻底删除 (Terminate) EC2 Instance.
    - 删除 DB Instance.
