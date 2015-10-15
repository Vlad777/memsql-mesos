import os
import requests

from memsql_framework.util import json

class ConnectionError(Exception):
    pass

class ApiException(Exception):
    pass


class ApiClient(object):
    def __init__(self, host, port):
        self.base_url = "http://%s:%d/api/v1" % (host, port)

    def call(self, path, params=None, timeout=60):
        if params is None:
            params = {}

        try:
            resp = requests.post(
                os.path.join(self.base_url, path),
                data=json.dumps(params),
                headers={ "AGENT_AUTH_TOKEN": "+tIs3U\>o@3`@4<-DR:ll'Bu590y(#]ACu2jlr(S.BDiO]]FLVubQcZP+?avBFM" },
                timeout=timeout)
        except requests.exceptions.ConnectionError, requests.exceptions.Timeout:
            raise ConnectionError

        data = json.loads(resp.content)
        if resp.status_code == 200:
            return data
        else:
            raise ApiException(data)

        resp.raise_for_status()
        return json.loads(resp.content)
