import os
import time

DEFAULT_HOSTS = None
CLUSTER_NAME = os.environ["MEMSQL_CLUSTER_NAME"]

def get_default():
    global DEFAULT_HOSTS
    if DEFAULT_HOSTS is None:
        with open("/etc/hosts") as hosts_file:
            DEFAULT_HOSTS = hosts_file.read()
    return DEFAULT_HOSTS

def update_hosts(root):
    root.load()
    cluster = root.clusters.find_by_name(CLUSTER_NAME)
    if not cluster:
        return

    data = get_default()
    for node in cluster.nodes:
        data += "%s %s\n" % (node.data.host_ip, node.data.host)

    with open("/etc/hosts", "w") as hosts_file:
        hosts_file.write(data)

def update_hosts_forever(root):
    while True:
        update_hosts(root)
        time.sleep(1)
