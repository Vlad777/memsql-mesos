from functools import wraps
from memsql_framework.util.attr_dict import AttrDict
from memsql_framework.ui import exceptions

ENDPOINTS = {}

def endpoint(name, schema=None, methods=None):
    def _deco(wrapped):
        @wraps(wrapped)
        def _wrap(root, params):
            if schema is not None:
                params = AttrDict(schema(params))

            return wrapped(root, params)

        if methods is None:
            setattr(_wrap, "__http_methods__", ["POST"])
        else:
            setattr(_wrap, "__http_methods__", methods)
        ENDPOINTS[name] = _wrap
        return _wrap

    return _deco

def call(root, name, props, method):
    endpoint = ENDPOINTS.get(name)
    if endpoint is None:
        raise exceptions.ApiException("Endpoint not found: %s" % name)

    allowed_methods = getattr(endpoint, "__http_methods__")
    if method not in allowed_methods:
        raise exceptions.ApiException("Method %s not supported by %s" % (method, name))

    return endpoint(root, props)

# import all endpoints here

from memsql_framework.ui.api import cluster  # noqa
