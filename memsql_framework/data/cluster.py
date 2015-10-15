import good as G

from memsql_framework.scheduler import flavors

from memsql_framework.data.record import Record
from memsql_framework.data.collection import Collection
from memsql_framework.data.node import Node
from memsql_framework.data.const import ClusterStatus, AgentRole, MemSQLRole

class Cluster(Record):
    schema = G.Schema({
        "display_name": basestring,
        "status": G.Map(ClusterStatus),
        "num_leaves": int,
        "num_aggs": int,
        "flavor": basestring,
        "install_demo": bool,
        "high_availability": bool,
        "created": int,
        "primary_host": G.Maybe(basestring),
        "primary_agent_port": G.Maybe(int),
        "primary_memsql_port": G.Maybe(int),
        "primary_demo_port": G.Maybe(int),
        "license_key": G.Maybe(basestring),
        "deploy_memsql_intention_id": G.Maybe(basestring),
        "currently_promoting_master": G.Any(bool, G.Default(False)),
        "successfully_started": G.Any(bool, G.Default(False)),
        "agent_version": G.Maybe(basestring),
    })

    def __init__(self, *args, **kwargs):
        super(Cluster, self).__init__(*args, **kwargs)
        self.nodes = Collection(self, "nodes", Node)

    def load(self):
        super(Cluster, self).load()
        self.nodes.load()
        return self

    @property
    def flavor(self):
        for f in flavors.FLAVORS:
            if f.flavor_id == self.data.flavor:
                return f
        raise KeyError("Flavor not found")

    @property
    def progress(self):
        current = 0
        total = 1 + self.data.num_leaves + self.data.num_aggs

        for node in self.nodes:
            if self.data.status == ClusterStatus.CREATING:
                if node.data.status == ClusterStatus.WAITING_FOR_AGENTS:
                    current += 1
            elif self.data.status == ClusterStatus.WAITING_FOR_AGENTS:
                if node.data.agent_id is not None:
                    current += 1
            elif self.data.status == ClusterStatus.WAITING_FOR_MEMSQL:
                # NOTE: When we're in the WAITING_FOR_MEMSQL stage, we don't
                # have access to incremental progress.
                pass
            elif self.data.status == ClusterStatus.RUNNING:
                if node.data.status == ClusterStatus.RUNNING:
                    current += 1

        return { "current": current, "total": total }

    def serialize(self):
        data = super(Cluster, self).serialize()
        data["cluster_id"] = self.name
        data["nodes"] = self.nodes.serialize()
        data["progress"] = self.progress
        return data

    def maybe_create_nodes(self):
        def make_node(agent_role, memsql_role):
            self.nodes.create(dict(
                status=ClusterStatus.CREATING,
                agent_role=agent_role,
                memsql_role=memsql_role))

        if len(self.nodes.records) == 0:
            make_node(AgentRole.PRIMARY, MemSQLRole.MASTER)
            for _ in range(self.data.num_aggs):
                make_node(AgentRole.FOLLOWER, MemSQLRole.CHILD)
            for _ in range(self.data.num_leaves):
                make_node(AgentRole.FOLLOWER, MemSQLRole.LEAF)
