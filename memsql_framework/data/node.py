import good as G

from memsql_framework.data.record import Record
from memsql_framework.data import const

class Node(Record):
    schema = G.Schema({
        "status": G.Map(const.ClusterStatus),
        "agent_role": G.Map(const.AgentRole),
        "memsql_role": G.Map(const.MemSQLRole),
        "host": G.Maybe(basestring),
        "host_ip": G.Maybe(basestring),
        "agent_port": G.Maybe(int),
        "memsql_port": G.Maybe(int),
        "demo_port": G.Maybe(int),
        "task_id": G.Maybe(basestring),
        "agent_id": G.Maybe(basestring)
    })

    def serialize(self):
        data = super(Node, self).serialize()
        data["node_id"] = self.name
        return data
