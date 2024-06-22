Server And Fleet
==============================================================================


What is Server
------------------------------------------------------------------------------
:class:`~acore_server.server.Server` 是这个库的核心属性. 它有两个属性:

1. 一个是 ``config``, 用于访问配置数据. 其本质是一个 `acore_server_config.api.Server <https://acore-server-config.readthedocs.io/en/latest/acore_server_config/config/define/server.html#acore_server_config.config.define.server.Server>`_ 对象 (另一个项目中的类).
2. 另一个是 ``metadata``, 用于访问 EC2 和 RDS 的属性. 其本质是一个  `acore_server_metadata.api.Server <https://acore-server-metadata.readthedocs.io/en/latest/acore_server_metadata/server/server.html#acore_server_metadata.server.server.Server>`_ 对象 (另一个项目中的类).

要创建一个 Server 对象很简单. 如果你的代码运行在 EC2 Game Server 之内, 那么调用 :meth:`server = acore_server.api.Server.from_ec2_inside() <acore_server.server.Server.from_ec2_inside>` 既可. 无需任何参数, 因为它会自动用 `EC2 metadata API <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instancedata-data-retrieval.html>`_ 获知自己是哪个 server. 而如果你的代码运行在 EC2 Game Server 之外, 那么调用 :meth:`server = acore_server.api.Server.get(bsm=..., server_id=...) <acore_server.server.Server.get>` 既可, 关键参数是 AWS 的 boto session manager 和显式指定 server_id.


What is Fleet
------------------------------------------------------------------------------
:class:`~acore_server.fleet.Fleet` 则是一个能把一个 `Environment <https://acore-server-metadata.readthedocs.io/en/latest/search.html?q=Environment+Name+and+Server+Name&check_keywords=yes&area=default>`_ 下的所有 server 的信息用一次 API 批量获得, 而无需一个个的调用 :meth:`server = acore_server.api.Server.get(bsm=..., server_id=...) <acore_server.server.Server.get>`, 提高了性能.

你只需要调用一次 :meth:`fleet = acore_server.api.Fleet.get(bsm=..., env_name=...) <acore_server.fleet.Fleet.get>` 然后你就可以用 :meth:`fleet.get_server(server_id=...) <acore_server.fleet.Fleet.get_server>` 来获取已经 load 到内存中的 server 的信息了.
