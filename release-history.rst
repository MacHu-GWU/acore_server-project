.. _release_history:

Release and Version History
==============================================================================


x.y.z (Backlog)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Features and Improvements**

**Minor Improvements**

**Bugfixes**

**Miscellaneous**


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
