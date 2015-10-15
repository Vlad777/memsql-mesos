import logging
import os
import requests
import subprocess
import time

from memsql_framework.util import json, log
from memsql_framework.util.time_helpers import unix_timestamp

CLUSTER_CREATE_INTERVAL = 120
MAX_CLUSTERS = 10
TEST_RUN_TIME = 3600

logger = logging.getLogger(__name__)

def run_shell_command(cmd, only_error=None):
    cmd = list(str(v) for v in cmd)
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = proc.communicate()
    if proc.poll() != 0:
        if only_error is None or proc.poll() == only_error:
            raise Exception("Command failed\n%s\n%s" % (stdout, stderr))
    return stdout

def run(scheduler_pid):
    log.setup()

    logger.info("Running resiliency test for MemSQL Mesos framework")

    num_initial_open_fds = len(os.listdir("/proc/%d/fd" % scheduler_pid))
    num_initial_open_sockets_out = run_shell_command(
        [ "netstat", "-nap", "tcp" ])
    num_initial_open_sockets = len(num_initial_open_sockets_out.split("\n"))

    created_clusters = []
    next_cluster_id = 1
    last_created_cluster_time = 0
    start_time = unix_timestamp()
    try:
        now = unix_timestamp()
        while now < start_time + TEST_RUN_TIME:
            now = unix_timestamp()
            time.sleep(5)
            # Create a new cluster every five minutes.
            if len(created_clusters) < MAX_CLUSTERS and last_created_cluster_time + CLUSTER_CREATE_INTERVAL < now:
                last_created_cluster_time = now
                logger.info("Creating new cluster")
                cluster_data = {
                    "display_name": "resiliency-test-cluster-%d" % next_cluster_id,
                    "num_leaves": 1,
                    "num_aggs": 1,
                    "flavor": "small",
                    "install_demo": True,
                    "high_availability": False
                }
                try:
                    new_cluster = call_scheduler_api("cluster/create", cluster_data)
                except Exception as e:
                    logger.warning("Exception when calling cluster/create: %s" % str(e))
                    continue

                next_cluster_id += 1
                created_clusters.append(new_cluster)

            if len(created_clusters) == MAX_CLUSTERS:
                cluster = created_clusters.pop(0)
                delete_cluster(cluster)
    except KeyboardInterrupt:
        pass

    for cluster in created_clusters:
        delete_cluster(cluster)

    print("Sleeping for 120 seconds to let TCP sockets close themselves")
    try:
        time.sleep(120)
    except KeyboardInterrupt:
        pass

    num_final_open_fds = len(os.listdir("/proc/%d/fd" % scheduler_pid))
    num_final_open_sockets_out = run_shell_command([ "netstat", "-nap", "tcp" ])
    num_final_open_sockets = len(num_final_open_sockets_out.split("\n"))

    now = unix_timestamp()
    print("MemSQL Mesos framework resiliency test ran for %s seconds" % (now - start_time))
    print("We initially had:")
    print("%d open file descriptors" % num_initial_open_fds)
    print("%d open TCP sockets" % num_initial_open_sockets)
    print("We finished with:")
    print("%d open file descriptors" % num_final_open_fds)
    print("%d open TCP sockets" % num_final_open_sockets)

def delete_cluster(cluster):
    logger.info("Deleting cluster %s" % cluster["display_name"])
    try:
        call_scheduler_api("cluster/delete", {
            "cluster_id": cluster["cluster_id"]
        })
    except Exception as e:
        logger.warning("Exception when calling cluster/delete: %s" % str(e))

def call_scheduler_api(path, params):
    host = "127.0.0.1"
    port = 9000
    base_url = "http://%s:%d/api" % (host, port)
    resp = requests.post(
        os.path.join(base_url, path), data=json.dumps(params), timeout=60)
    return json.loads(resp.content)
