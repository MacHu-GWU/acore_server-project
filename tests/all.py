# -*- coding: utf-8 -*-

if __name__ == "__main__":
    from acore_server.tests import run_cov_test

    run_cov_test(__file__, "acore_server", is_folder=True, preview=False)
