import good as G
from memsql_framework.util.attr_dict import AttrDict

class Flavor(AttrDict):
    schema = G.Schema({
        "flavor_id": basestring,
        "memory": int,
        "cpu": int,
        "disk": int
    })

    def __init__(self, **params):
        sanitized_data = Flavor.schema(params)
        super(Flavor, self).__init__(sanitized_data)

    def bigger_than(self, cpu, memory, disk):
        return self.cpu > cpu or self.memory > memory or self.disk > disk

    def __str__(self):
        return "Flavor(%s, %s, %s)" % (self.cpu, self.memory, self.disk)

    @property
    def memory_mb(self):
        return self.memory * 1024

    @property
    def disk_mb(self):
        return self.disk * 1024

FLAVORS = [
    Flavor(flavor_id="small", memory=16, cpu=4, disk=32),
    Flavor(flavor_id="medium", memory=24, cpu=6, disk=48),
    Flavor(flavor_id="large", memory=32, cpu=8, disk=64),
    Flavor(flavor_id="xlarge", memory=60, cpu=12, disk=120)
]
