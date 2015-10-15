import os
import requests

from memsql_framework.util import json

DOWNLOADS_BASE = "http://download.memsql.com"

class BuildReceiptError(Exception):
    pass

class BuildReceipt(object):
    def __init__(self, license_key=None):
        self.url = os.path.join(DOWNLOADS_BASE, license_key, "build_receipt.json")

        try:
            resp = requests.get(self.url, timeout=5)
            resp.raise_for_status()
            data = resp.json()

            self.license_key = license_key
            self.version = data['version']
        except requests.exceptions.HTTPError as e:
            # this license key does not exist
            if e.response.status_code == 403:
                raise BuildReceiptError("License key %s does not exist" % license_key)
            else:
                raise
        except requests.exceptions.ConnectionError:
            raise BuildReceiptError("Failed to connect to the MemSQL license server")
        except (KeyError, ValueError, json.JSONDecodeError):
            raise BuildReceiptError("Could not parse build_receipt.json for URL %s" % self.url)
