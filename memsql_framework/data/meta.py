import good as G

from memsql_framework.data.record import Record

class Meta(Record):
    schema = G.Schema({
        "framework_id": G.Maybe(basestring),
        "last_task_id": G.Maybe(int)
    })
