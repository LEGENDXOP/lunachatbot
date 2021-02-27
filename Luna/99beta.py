import asyncio
import datetime
import importlib
import inspect
import logging
import math
import os
import re
import sys
import time
import traceback
from pathlib import Path
from time import gmtime, strftime

from telethon import events
from telethon.tl.functions.channels import GetParticipantRequest
from telethon.tl.types import ChannelParticipantAdmin, ChannelParticipantCreator
from Luna import CMD_LIST, LOAD_PLUG, LOGS, SUDO_USERS, tbot

def load_module(shortname):
    if shortname.startswith("__"):
        pass
    elif shortname.endswith("_"):
        import Luna.defs

        path = Path(f"Luna/modules/{shortname}.py")
        name = "Luna.modules.{}".format(shortname)
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        LOGS.info("Successfully imported " + shortname)
    else:
        import Luna.defs

        path = Path(f"Luna/modules/{shortname}.py")
        name = "Luna.modules.{}".format(shortname)
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        mod.tbot = tbot
        mod.command = command
        mod.logger = logging.getLogger(shortname)
        mod.tbot = bot
        spec.loader.exec_module(mod)
        # for imports
        sys.modules["Luna.modules." + shortname] = mod
        LOGS.info("Successfully imported " + shortname)
