# -*- coding: utf-8 -*-

from acore_server import api


def test():
    _ = api
    _ = api.Server
    _ = api.Fleet
    _ = api.InfraStackExports


if __name__ == "__main__":
    from acore_server.tests import run_cov_test

    run_cov_test(__file__, "acore_server.api", preview=False)
