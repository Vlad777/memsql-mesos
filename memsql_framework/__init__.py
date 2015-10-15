import os
import re

SCHEDULER_NAME = os.environ.get("MEMSQL_SCHEDULER_NAME", "memsql")
if SCHEDULER_NAME == "memsql":
    DEFAULT_DATA_ROOT_PATH = "memsql_scheduler"
else:
    DEFAULT_DATA_ROOT_PATH = "memsql_scheduler_%s" % re.sub("\W", "", SCHEDULER_NAME)

__version__ = "0.0.1"
