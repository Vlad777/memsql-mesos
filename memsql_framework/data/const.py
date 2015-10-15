from memsql_framework.util.auto_enum import AutoEnum

class AgentRole(AutoEnum):
    PRIMARY = ()
    FOLLOWER = ()

class MemSQLRole(AutoEnum):
    LEAF = ()
    CHILD = ()
    MASTER = ()

class ClusterStatus(AutoEnum):
    CREATING = ()
    WAITING_FOR_AGENTS = ()
    WAITING_FOR_MEMSQL = ()
    RUNNING = ()
    DELETING = ()
