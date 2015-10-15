from tornado import web
from tornado import gen
import logging
import good as G

from memsql_framework.ui.exceptions import ApiException, JSONDecodeError
from memsql_framework.util import json

logger = logging.getLogger(__name__)

USER_ERRORS = (ApiException, G.Invalid)

class ApiHandler(web.RequestHandler):
    def initialize(self, pool):
        self.pool = pool

    @web.removeslash
    @gen.coroutine
    def get(self, name):
        return self._api_call(name, method="GET")

    @web.removeslash
    @gen.coroutine
    def post(self, name):
        return self._api_call(name, method="POST")

    def _api_call(self, name, method):
        try:
            params = self._params()
            response = yield self.pool.query(name, params, method)
            self._respond_success(response)
        except Exception as err:
            self._respond_error(err)

    def _params(self):
        """ Decode a params dictionary from the request body. """
        body = self.request.body.strip()
        if not body:
            return {}

        try:
            return json.loads(body)
        except json.JSONDecodeError as e:
            raise JSONDecodeError(str(e))

    def _respond_success(self, data):
        self._finish(200, data)

    def _respond_error(self, error):
        status_code = 400 if isinstance(error, USER_ERRORS) else 500
        data = {
            "error": str(error),
            "error_type": error.__class__.__name__
        }

        if isinstance(error, G.Invalid):
            data["error_path"] = error.path

        self._finish(status_code, data)

    def _finish(self, status_code, data):
        self.set_status(status_code)
        self._write_json(data)
        self.finish()

    def _write_json(self, data):
        data = json.dumps(data)
        self.write(data + "\n")
