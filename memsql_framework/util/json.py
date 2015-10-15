import simplejson

# declare direct exports here
loads = simplejson.loads
JSONDecodeError = simplejson.JSONDecodeError

def _simplejson_datetime_serializer(obj):
    """ Designed to be passed as simplejson.dumps default serializer.

    Serializes dates and datetimes to ISO strings.
    """
    if hasattr(obj, 'isoformat'):
        return obj.isoformat()
    else:
        raise TypeError('Object of type %s with value of %s is not JSON serializable' % (type(obj), repr(obj)))

def _set_defaults(kwargs, pretty=False):
    kwargs.setdefault('default', _simplejson_datetime_serializer)
    kwargs.setdefault('for_json', True)
    if pretty:
        kwargs.setdefault('separators', (',', ': '))
        kwargs.setdefault('indent', ' ' * 4)
        kwargs.setdefault('sort_keys', True)
    else:
        kwargs.setdefault('separators', (',', ':'))

    return kwargs

def dumps(data, **kwargs):
    """ Dump the provided data to JSON via simplejson.

    Sets a bunch of default options providing the following functionality:

        * serializes anything with a isoformat method (like datetime) to a iso timestamp.
        * if it encounters an unknown object it will try calling for_json on it
          to get a json serializable version.
    """
    return simplejson.dumps(data, **_set_defaults(kwargs))

def pretty_dumps(data, **kwargs):
    """ Same as dumps, except it formats the JSON so it looks pretty. """
    return simplejson.dumps(data, **_set_defaults(kwargs, pretty=True))

def safe_loads(data, default, **kwargs):
    """ Tries to load the provided data, on failure returns the default instead. """
    try:
        return simplejson.loads(data, **kwargs)
    except JSONDecodeError:
        return default
