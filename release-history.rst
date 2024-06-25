.. _release_history:

Release and Version History
==============================================================================


x.y.z (Backlog)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Features and Improvements**

**Minor Improvements**

**Bugfixes**

**Miscellaneous**


1.1.3 (2024-06-25)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Bugfixes**

- Fix bug in ``create_cloned_server``.


1.1.2 (2024-06-24)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Miscellaneous**

- Improve logging message.


1.1.1 (2024-06-22)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Features and Improvements**

- Add the following workflow:
    - :meth:`~acore_server.server_workflow_mixin.ServerWorkflowMixin.stop_server`
    - :meth:`~acore_server.server_workflow_mixin.ServerWorkflowMixin.start_server`

**Minor Improvements**

- Improve document.


1.0.3 (2024-06-21)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**💥Breaking Changes**

- remove the following deprecated methods, these features are moved to `acore_server_bootstrap.api.Remoter <https://acore-server-bootstrap.readthedocs.io/en/latest/search.html?q=Remote+Bootstrap&check_keywords=yes&area=default>`_:
    - ``Server.bootstrap()``
    - ``Server.run_check_server_status_cron_job()``
    - ``Server.stop_check_server_status_cron_job()``
    - ``Server.run_game_server()``
    - ``Server.stop_game_server()``

**Bugfixes**

- Fix a bug in ``Server.build_bootstrap_command(...)`` method that the method doesn't use the explicit library version.


1.0.2 (2024-06-20)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Bugfixes**

- Fix a bug that ``Server.create_ssh_tunnel(...)``, ``Server.list_ssh_tunnel(...)``, ``Server.test_ssh_tunnel(...)``, ``Server.kill_ssh_tunnel(...)`` methods failed to locate the pem file correctly.


1.0.1 (2024-06-20)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**💥Breaking Changes**

- Moved most of server operation logics into this library.

**Features and Improvements**

- Add lot of `workflows <https://acore-server.readthedocs.io/en/latest/search.html?q=Operation+and+Workflow&check_keywords=yes&area=default>`_.


0.2.5 (2023-07-18)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Features and Improvements**

**Minor Improvements**

- add ``acore_db_app_version`` argument to ``acore_server.fleet.Server.run_ec2`` method.

**Bugfixes**

**Miscellaneous**


0.2.4 (2023-06-28)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Miscellaneous**

- Upgrade ``acore_server_config`` dependency from 0.4.2 to 0.5.1.


0.2.3 (2023-06-28)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Miscellaneous**

- Upgrade dependencies.


0.2.2 (2023-06-28)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Miscellaneous**

- Remove unnecessary dependencies.


0.2.1 (2023-06-27)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Features and Improvements**

- Add ``acore_server.api.Server.from_ec2_inside``


0.1.2 (2023-06-27)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Minor Improvements**

- Add ``acore_soap_app_version``, ``acore_server_bootstrap_version`` arguments to ``acore_server.api.Server.bootstrap`` method.
- Add ``acore_server.api.Server.stop_check_server_status_cron_job``.

**Bugfixes**

- Fix some but that some remote command should be run as ubuntu user, not root.

**Miscellaneous**

- Upgrade dependencies.


0.1.1 (2023-06-27)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Features and Improvements**

- First release
- Add the following public API:
    - ``acore_server.api.Server``
    - ``acore_server.api.Fleet``
    - ``acore_server.api.InfraStackExports``
