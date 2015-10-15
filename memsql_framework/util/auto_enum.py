from enum import Enum

class Enum(Enum):
    def __str__(self):
        """ Serialize to a string """
        return self.name
    for_json = __str__

    def __eq__(self, other):
        if isinstance(other, Enum):
            return super(Enum, self).__eq__(other)
        else:
            return str(self) == str(other)

    def __hash__(self):
        return hash(self._name_)

class AutoEnum(Enum):
    """ An Enum which automatically assigns values to its members.

    If you stringify or jsonify one of its members you will get the name of the
    member back rather than the value.

    Usage::

        class Foo(AutoEnum):
            BAR = ()
            BAZ = ()

        assert Foo.BAR != Foo.BAZ
        assert str(Foo.BAR) == "BAR"
    """
    def __new__(cls):
        value = len(cls.__members__) + 1
        obj = object.__new__(cls)
        obj._value_ = value
        return obj
