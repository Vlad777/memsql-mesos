import good as G

from memsql_framework.ui.api.endpoints import endpoint
from memsql_framework.ui.exceptions import ApiException

from memsql_framework.data.const import ClusterStatus
from memsql_framework.data.errors import RecordValidationError

from memsql_framework.scheduler.flavors import FLAVORS
from memsql_framework.util.build_receipt import BuildReceipt, BuildReceiptError
from memsql_framework.util.time_helpers import unix_timestamp

class HealthCheckException(Exception):
    pass

def _validate_license_key(license_key):
    if license_key is not None:
        try:
            BuildReceipt(license_key)
        except BuildReceiptError as e:
            raise G.Invalid(str(e), "valid license", license_key)
    return license_key

@endpoint("ping")
def ping(root, params):
    return "pong"

@endpoint("healthcheck", methods=["GET"])
def healthcheck(root, params):
    if not root.ZK.connected:
        raise HealthCheckException()
    return True

@endpoint("cluster/list")
def cluster_list(root, params):
    return root.clusters.serialize()

@endpoint("cluster/create", G.Schema({
    "display_name": G.All(basestring, G.Msg(G.Length(min=1), u"Name can not be empty")),
    "num_leaves": G.All(int, G.Range(min=0)),
    "num_aggs": G.All(int, G.Range(min=0)),
    "flavor": basestring,
    "install_demo": G.Any(bool, G.Default(True)),
    "high_availability": G.Any(bool, G.Default(False)),
    G.Optional("license_key"): _validate_license_key
}))
def cluster_create(root, params):
    existing_cluster = root.clusters.find(display_name=params.display_name)
    if existing_cluster is not None:
        raise G.Invalid("Cluster name must be unique", "unique name", params.display_name, ["display_name"])

    try:
        params["status"] = ClusterStatus.CREATING
        params["created"] = unix_timestamp()
        cluster = root.clusters.create(params)
        return cluster.serialize()
    except RecordValidationError as e:
        raise ApiException(str(e))

@endpoint("cluster/delete", G.Schema({
    "cluster_id": basestring
}))
def cluster_delete(root, params):
    cluster = root.clusters.records.get(params.cluster_id)
    if cluster is None:
        raise ApiException("Cluster with id %s not found" % params.cluster_id)
    cluster.save(status=ClusterStatus.DELETING)
    return params.cluster_id

@endpoint("node/list", G.Schema({
    "cluster_id": basestring
}))
def node_list(root, params):
    cluster = root.clusters.records.get(params.cluster_id)
    if cluster is None:
        raise ApiException("Cluster with id %s not found" % params.cluster_id)
    return cluster.nodes.serialize()

@endpoint("flavor/list")
def flavor_list(root, params):
    return FLAVORS
