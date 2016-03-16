import requests

from memsql_framework.util import json

class GetJSONFromURLException(Exception):
    pass


def get_json_from_url(url):
    try:
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        return data
    except (requests.RequestException, json.JSONDecodeError, UnicodeDecodeError) as e:
        raise GetJSONFromURLException(e)
