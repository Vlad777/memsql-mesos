from contextlib import closing
import os
import time
import subprocess
import logging
import requests

from memsql_framework.data import const
from memsql_framework.executor.hosts import update_hosts

logger = logging.getLogger(__name__)

MEMSQL_DEMO_TARGET_ROLES = (const.MemSQLRole.MASTER, const.MemSQLRole.CHILD)

def run(cmd, only_error=None, detach=False, set_user=False):
    cmd = list(str(v) for v in cmd)
    if set_user:
        cmd = [ "/sbin/setuser", "memsql" ] + cmd
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if detach:
        return

    stdout, stderr = proc.communicate()
    if proc.poll() != 0:
        if only_error is None or proc.poll() == only_error:
            raise Exception("Command failed\n%s\n%s" % (stdout, stderr))

class Executor(object):
    def __init__(self, root):
        self.root = root

        self.agent_host = os.environ["MEMSQL_AGENT_HOST"]
        self.agent_port = int(os.environ["MEMSQL_AGENT_PORT"])
        self.memsql_role = os.environ["MEMSQL_ROLE"]
        self.memsql_port = os.environ["MEMSQL_PORT"]

        self.cluster_name = os.environ["MEMSQL_CLUSTER_NAME"]

        self.agent_version = os.environ["MEMSQL_AGENT_VERSION"]

        self.install_demo = "MEMSQL_DEMO_ENABLED" in os.environ
        self.memsql_demo_port = os.environ["MEMSQL_DEMO_PORT"]

        self.procs = []

    def start(self):
        update_hosts(self.root)

        logger.info("Downloading MemSQL Ops")
        url = "http://download.memsql.com/memsql-ops-%s/memsql-ops-%s.tar.gz" % (self.agent_version, self.agent_version)
        self._download_file(url)
        logger.info("Unpacking MemSQL Ops")
        run([ "mkdir", "-p", "/tmp/memsql_ops" ])
        run([ "tar", "-xzf", "/tmp/memsql_ops.tar.gz", "-C", "/tmp/memsql_ops", "--strip-components", "1" ])
        logger.info("Installing and starting MemSQL Ops")
        run([ "/tmp/memsql_ops/install.sh", "--host", self.agent_host, "--port", self.agent_port, "--no-cluster" ])

        if self.install_demo and self.memsql_role in MEMSQL_DEMO_TARGET_ROLES:
            self._install_demo()

    def _install_demo(self):
        while True:
            self.root.load()
            cluster = self.root.clusters.find_by_name(self.cluster_name)
            if not cluster:
                logger.warning("Could not find cluster %s while installing demo" % self.cluster_name)
                return
            node = cluster.nodes.find(host=self.agent_host)

            logger.info("Waiting for cluster to be ready for MemSQL Demo")
            if node.data.status == const.ClusterStatus.RUNNING:
                run(["/memsql_demo/memsql-demo", "worker"],
                    detach=True,
                    set_user=True)
                if self.memsql_role == const.MemSQLRole.MASTER:
                    run(["/memsql_demo/memsql-demo", "server",
                         "-p", self.memsql_demo_port,
                         "--db-port", self.memsql_port],
                        detach=True,
                        set_user=True)
                return

            time.sleep(1)

    def _download_file(self, url):
        with open("/tmp/memsql_ops.tar.gz", "w+b") as tmp_file:
            with closing(requests.get(url, verify=False, timeout=30, stream=True)) as resp:
                resp.raise_for_status()
                tmp_file.seek(0)
                for chunk in resp.iter_content(chunk_size=1024):
                    if chunk:
                        tmp_file.write(chunk)
