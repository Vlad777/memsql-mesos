import logging

from mesos.interface import mesos_pb2

from memsql_framework.data import const
from memsql_framework.util import api_client
from memsql_framework.util.super_thread import SuperThread

logger = logging.getLogger(__name__)

# Automatically delete clusters if they don't successfully start up in an hour.
CLUSTER_TIMEOUT = 60 * 60

class FollowPrimaryException(Exception):
    pass

class ClusterMonitor(SuperThread):
    sleep = 2

    def setup(self):
        super(ClusterMonitor, self).setup()
        self.driver = self.context.driver
        self.root = self.context.data_root

    def work(self):
        for cluster in self.root.clusters:
            if cluster.data.status == const.ClusterStatus.DELETING:
                self._delete_cluster(cluster)
            elif cluster.data.status == const.ClusterStatus.WAITING_FOR_AGENTS:
                self._deploy_memsql(cluster)
            elif cluster.data.status == const.ClusterStatus.WAITING_FOR_MEMSQL:
                self._check_memsql(cluster)

    def _delete_cluster(self, cluster):
        logger.info("Deleting cluster %s" % cluster.name)
        for node in cluster.nodes:
            if node.data.task_id is not None:
                t = mesos_pb2.TaskID()
                t.value = node.data.task_id
                self.driver.killTask(t)
        cluster.delete()

    def _deploy_memsql(self, cluster):
        # If we're currently promoting a MemSQL child aggregator to a master
        # with AGGREGATOR SET AS MASTER, return here.  We will check if the
        # operation is done on the next work() iteration.
        if cluster.data.currently_promoting_master:
            return

        nodes = list(cluster.nodes)
        # Try to set the agent_id field on all nodes in this cluster. If we
        # cannot do this for all nodes, then we assume that the cluster isn't
        # ready yet (i.e. MemSQL Agent hasn't started on all nodes) so we
        # just return here and try again on the next work() iteration.
        total = len(nodes)
        current = self._set_agent_id_on_nodes(nodes)
        logger.info(
            "%d/%d nodes have MemSQL Agent on cluster %s"
            % (current, total, cluster.name))
        if current < total:
            return

        try:
            self._follow_primary(cluster)
        except FollowPrimaryException as e:
            logger.error(str(e))
            return

        primary_client = api_client.ApiClient(
            cluster.data.primary_host, cluster.data.primary_agent_port)
        agents = []
        try:
            agents = primary_client.call("topology/agents/query", {})
        except (api_client.ApiException, api_client.ConnectionError) as e:
            pass
        # Wait for all of the followers to follow the primary.
        if len(agents) < total:
            return

        logger.info("Deploying MemSQL on cluster %s" % cluster.name)
        # XXX: Only check cluster.data.high_availability once the frontend
        # sets it properly.
        if cluster.data.high_availability and cluster.data.license_key:
            redundancy_level = 2
        else:
            redundancy_level = 1

        memsql_nodes = []
        for node in nodes:
            if node.data.status == const.ClusterStatus.RUNNING:
                # This indicates that the node already has MemSQL set up (this
                # can occur if, for instance, we have an existing cluster and
                # some nodes goes down, so we're re-deploying MemSQL to them
                # here).
                continue
            if node.data.memsql_role == const.MemSQLRole.MASTER:
                role = "MASTER"
            elif node.data.memsql_role == const.MemSQLRole.CHILD:
                role = "AGGREGATOR"
            elif node.data.memsql_role == const.MemSQLRole.LEAF:
                role = "LEAF"
            memsql_nodes.append({
                "agent_id": node.data.agent_id,
                "port": node.data.memsql_port,
                "role": role
            })

        if cluster.data.license_key is not None:
            try:
                existing_license = primary_client.call("topology/memsql/license/query", {
                    "license_key": cluster.data.license_key
                })
                if not existing_license:
                    primary_client.call("topology/memsql/license/create_with_key", {
                        "license_key": cluster.data.license_key
                    })
            except api_client.ApiException as e:
                logger.error("Could not create license key %s: %s. Rolling back cluster" % (cluster.data.license_key, str(e)))
                return

        intention_data = {
            "memsql_nodes": memsql_nodes,
            "redundancy_level": redundancy_level,
            "interactive": False
        }
        try:
            intention_row = primary_client.call("topology/intentions/create", {
                "intention": "DeployMemsql",
                "data": intention_data
            })
        except (api_client.ConnectionError, api_client.ApiException) as e:
            logger.error("Could not create DeployMemSQL intention: %s. Rolling back cluster" % str(e))
            return

        cluster.save(
            status=const.ClusterStatus.WAITING_FOR_MEMSQL,
            deploy_memsql_intention_id=intention_row["intention_id"])
        for node in nodes:
            node.save(status=const.ClusterStatus.WAITING_FOR_MEMSQL)

    def _check_memsql(self, cluster):
        primary_client = api_client.ApiClient(
            cluster.data.primary_host, cluster.data.primary_agent_port)
        intention_id = cluster.data.deploy_memsql_intention_id

        try:
            intention_row = primary_client.call("topology/intentions/intention_get", { "intention_id": intention_id })
            if not intention_row or intention_row["status"] == "ACTIVE":
                # The DeployMemsql intention is still going. We will check this
                # cluster again on the next work() iteration.
                return
        except api_client.ApiException as e:
            logger.error("Could not deploy MemSQL: %s. Rolling back cluster" % str(e))
            return

        if intention_row["status"] != "SUCCEEDED":
            logger.error(
                "DeployMemsql failed with data %s for cluster %s"
                % (intention_row["state"]["data"], cluster.name))
            return

        cluster.save(
            status=const.ClusterStatus.RUNNING, successfully_started=True)
        for node in cluster.nodes:
            node.save(status=const.ClusterStatus.RUNNING)

        logger.info("Successfully deployed MemSQL on cluster %s" % cluster.name)

    def _set_agent_id_on_nodes(self, nodes):
        for node in nodes:
            if node.data.agent_id is not None:
                continue
            try:
                client = api_client.ApiClient(
                    node.data.host_ip, node.data.agent_port)
                agent_id = client.call("variables/agent_id", {})
            except api_client.ConnectionError:
                continue
            node.save(agent_id=agent_id)
        # Return the number of nodes that have their agent ID set.
        return sum([ 1 for node in nodes if node.data.agent_id is not None ])

    def _follow_primary(self, cluster):
        primary_node = cluster.nodes.find(agent_role=const.AgentRole.PRIMARY)
        primary_host = primary_node.data.host
        primary_agent_port = primary_node.data.agent_port

        # Sort the nodes so that we set up the primary first, since if the
        # primary is currently set up as a follower we need to promote it to
        # a primary before we try to make anything else follow it.
        nodes = list(cluster.nodes)
        nodes.sort(key=lambda n: 1 if n is primary_node else 2)
        for node in nodes:
            client = api_client.ApiClient(
                node.data.host_ip, node.data.agent_port)
            try:
                if node.data.agent_role == const.AgentRole.PRIMARY:
                    try:
                        # Tell this node to become the primary if it isn't
                        # already.
                        current_state = client.call("network/current_state", {})
                        if current_state != "Primary":
                            client.call("network/unfollow", {})
                    except api_client.ApiException:
                        pass
                    # Attach to all existing MemSQL nodes so that we can
                    # reconnect the cluster.
                    for node in nodes:
                        client.call("topology/jobs/put", {
                            "target": "primary",
                            "job_type": "memsql_attach",
                            "properties": {
                                "host": node.data.host,
                                "port": node.data.memsql_port,
                                "user": "root"
                            }
                        })
                else:
                    primary_details = client.call("variables/primary_details", {})
                    if not primary_details or primary_details[1] != primary_host or primary_details[2] != primary_agent_port:
                        try:
                            # Unfollow in case this agent is already following a
                            # different primary.
                            current_state = client.call("network/current_state", {})
                            if current_state != "Primary":
                                client.call("network/unfollow", {})
                        except api_client.ApiException:
                            pass
                        client.call("network/follow", {
                            "host": primary_host,
                            "port": primary_agent_port
                        })
            except (api_client.ConnectionError, api_client.ApiException) as e:
                raise FollowPrimaryException("Error when attempting to get agent %s to follow the primary agent at %s:%d: %s" % (node.data.agent_id, primary_host, primary_agent_port, str(e)))
