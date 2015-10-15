import logging
import uuid

from memsql_framework.data.record import Record
from memsql_framework.data.errors import RecordValidationError

logger = logging.getLogger(__name__)

class Collection(Record):
    def __init__(self, parent, name, RecordClass):
        super(Collection, self).__init__(parent, name)
        self.RecordClass = RecordClass

        self.records = {}

    def load(self):
        super(Collection, self).load()

        def get_record(name):
            try:
                return self.RecordClass(self, name).load()
            except RecordValidationError as e:
                logger.warning("Could not validate data for %s with id %s: %s" % (self.RecordClass.__name__, name, str(e)))

        names = self.root.zk_get_children(self.path)
        if names is not None:
            records = { name: get_record(name) for name in names }
            # filter any bad records
            self.records = { k: v for (k, v) in records.items() if v is not None }

        return self

    def create(self, initial_data):
        name = uuid.uuid1().hex
        record = self.RecordClass(self, name, initial_data)
        record.save()
        self.records[name] = record
        return record

    def handle_delete_child(self, record):
        del self.records[record.name]

    def serialize(self):
        return [ r.serialize() for r in self ]

    def __iter__(self):
        for record in self.records.values():
            yield record

    def find(self, **where):
        for record in self:
            if all(record.data[k] == v for k, v in where.items()):
                return record

    def find_by_name(self, name):
        for record in self:
            if record.name == name:
                return record
