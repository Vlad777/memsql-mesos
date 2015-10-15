import copy

def convert_value(v):
    if isinstance(v, dict):
        return AttrDict(v)
    elif isinstance(v, list):
        return [ convert_value(x) for x in v ]
    else:
        return v

class _AttrDictBase(type):
    """ Metaclass for AttrDict which ensures direct equality with dict

        i.e. type(AttrDict()) == dict
    """

    def __eq__(self, other):
        return other == dict or super().__eq__(other)

    # hash AttrDict as if it was dict
    def __hash__(self):
        return hash(dict)

class AttrDict(dict):
    __metaclass__ = _AttrDictBase
    """ A dictionary that provides access to its values via attributes.

    If initialized with a dictionary, will provide recursive access to
    sub-dictionary keys via attributes as well.

    Usage::

        x = AttrDict({ 'a': { 'b': 2 } })
        assert x.a.b == 2
    """

    __slots__ = ()

    # since we use __getattr__, we need to make sure these members exist
    # so that AttrDicts can be serialized to json
    for_json = False
    _asdict = False

    def __init__(self, source=None):
        if source is not None:
            super(AttrDict, self).__init__(source)
            for k, v in self.items():
                self[k] = convert_value(v)

    def __getattr__(self, key):
        return self[key]

    def __setattr__(self, key, value):
        self[key] = value

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, dict.__repr__(self))

    def immutable_update(self, updates):
        other = copy.deepcopy(self)
        other.update(updates)
        return AttrDict(other)
