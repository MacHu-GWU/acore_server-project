# -*- coding: utf-8 -*-

from vislog import VisLog

# I am trying to use rich for logging, I intentionally this code here
# I haven't made decision using it right now
try:  # pragma: no cover
    from rich import print as rprint

    class RichLogger:
        def info(self, msg: str):
            rprint(msg)

    _logger = RichLogger()
except ImportError:  # pragma: no cover
    _logger = None

_logger = None

logger = VisLog(
    name="acore_server",
    logger=_logger,
    log_format="%(message)s",
)
