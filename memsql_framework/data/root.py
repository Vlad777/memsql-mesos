from kazoo.client import KazooClient
from kazoo.retry import KazooRetry

from threading import Lock

from memsql_framework.data.record import Record
from memsql_framework.data.collection import Collection
from memsql_framework.data.cluster import Cluster
from memsql_framework.data.meta import Meta

class Root(Record):
    def __init__(self, root_path):
        if not root_path.startswith("/"):
            root_path = "/" + root_path

        super(Root, self).__init__(None, root_path)

        self.lock = Lock()
        self.ZK_retry = KazooRetry(max_tries=-1)
        self.ZK = None

    def connect(self, zookeeper_hosts):
        self.ZK = KazooClient(
            zookeeper_hosts,
            connection_retry=self.ZK_retry,
            command_retry=self.ZK_retry)

        self.ZK.start()

        # create & load collections
        self.clusters = Collection(self, "clusters", Cluster)
        self.meta = Meta(self, "meta")

        return self.load()

    def load(self):
        super(Root, self).load()
        self.clusters.load()
        self.meta.load()
        return self

    def zk_ensure_path(self, *args, **kwargs):
        return self.ZK.retry(self.ZK.ensure_path, *args, **kwargs)

    def zk_set(self, *args, **kwargs):
        return self.ZK.retry(self.ZK.set, *args, **kwargs)

    def zk_get(self, *args, **kwargs):
        return self.ZK.retry(self.ZK.get, *args, **kwargs)

    def zk_get_children(self, *args, **kwargs):
        return self.ZK.retry(self.ZK.get_children, *args, **kwargs)

    def zk_delete(self, *args, **kwargs):
        return self.ZK.retry(self.ZK.delete, *args, **kwargs)
