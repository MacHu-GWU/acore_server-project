# -*- coding: utf-8 -*-

from datetime import datetime, timezone


def get_utc_now() -> datetime:
    return datetime.utcnow().replace(tzinfo=timezone.utc)


def prompt_for_confirm(msg: str):
    entered = input(f"{msg} Enter 'YES' to proceed: ")
    if entered != "YES":
        raise KeyboardInterrupt()
