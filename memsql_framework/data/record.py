import os
import good as G
import copy

from memsql_framework.util import json
from memsql_framework.util.attr_dict import AttrDict
from memsql_framework.data import errors

class Record(object):
    schema = None

    def __init__(self, parent, name, data=None):
        self.parent = parent
        self.name = name
        if data is not None:
            self.data = self.validate_data(data)
        else:
            self.data = {}

    @property
    def root(self):
        """ Retrieve the root record. """
        if self.parent is None:
            return self
        else:
            return self.parent.root

    @property
    def path(self):
        """ Return an absolute path to this record. """
        if self.parent is None:
            return self.name
        else:
            return os.path.join(self.parent.path, self.name)

    def validate_data(self, data):
        if self.schema is not None:
            try:
                return AttrDict(self.schema(data or {}))
            except G.Invalid as e:
                raise errors.RecordValidationError(e)
        else:
            return AttrDict(data or {})

    def load(self):
        root = self.root
        path = self.path
        with root.lock:
            root.zk_ensure_path(path)
        if self.schema is not None:
            data, _ = root.zk_get(path)
            self.data = self.validate_data(json.safe_loads(data, {}))
        return self

    def save(self, **updates):
        root = self.root
        path = self.path
        with root.lock:
            root.zk_ensure_path(path)
            if self.schema is not None:
                # update a copy of our data
                data = self.data.immutable_update(updates)
                # make sure the updated copy validates
                data = self.validate_data(data)
                # save to zookeeper
                bdata = bytes(json.dumps(data))
                root.zk_set(path, bdata)
                # save
                self.data = data

        return self

    def delete(self):
        root = self.root
        with root.lock:
            root.zk_delete(self.path, recursive=True)

        if self.parent is not None:
            self.parent.handle_delete_child(self)

    def handle_delete_child(self, child):
        pass

    def serialize(self):
        return copy.deepcopy(self.data)
