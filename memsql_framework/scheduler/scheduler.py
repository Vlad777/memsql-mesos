import logging
import os
import socket
from threading import Thread

from memsql.common import database

from memsql_framework import SCHEDULER_NAME
from memsql_framework.data import const
from memsql_framework.scheduler import utils
from memsql_framework.util import api_client, web_helpers

from mesos.interface import Scheduler
from mesos.interface import mesos_pb2

logger = logging.getLogger(__name__)

WEB_TASK_CPUS = 1
WEB_TASK_MEM = 32
WEB_TASK_PORTS = 1
AGENT_TASK_PORTS = 3
SHUTDOWN_TIMEOUT = 30  # in seconds

CURRENT_AGENT_VERSION_URL = "http://versions.memsql.com/memsql-ops/latest"

ZOOKEEPER_URL = os.environ['ZOOKEEPER_URL']
MEMSQL_SCHEDULER_ROLE = os.getenv('MEMSQL_SCHEDULER_ROLE', '*')

NAME_MAP = {
    6: "TASK_STAGING",      # Initial state. Framework status updates should not use.
    0: "TASK_STARTING",
    1: "TASK_RUNNING",
    2: "TASK_FINISHED",     # TERMINAL.
    3: "TASK_FAILED",       # TERMINAL.
    4: "TASK_KILLED",       # TERMINAL.
    5: "TASK_LOST",         # TERMINAL.
    7: "TASK_ERROR",        # TERMINAL.
}
TERMINAL_STATES = (
    mesos_pb2.TASK_FINISHED,
    mesos_pb2.TASK_FAILED,
    mesos_pb2.TASK_KILLED,
    mesos_pb2.TASK_LOST,
    mesos_pb2.TASK_ERROR
)

# See the Mesos Framework Development Guide:
# http://mesos.apache.org/documentation/latest/app-framework-development-guide
class MemSQLScheduler(Scheduler):
    def __init__(self, data_root):
        logger.info("Starting scheduler")

        self.root = data_root
        if self.root.meta.data.last_task_id is None:
            self.root.meta.save(last_task_id=0)

        self.tasksRunning = 0
        self.shuttingDown = False

    def make_task(self, offer, cpu, mem, disk=None):
        task = mesos_pb2.TaskInfo()
        tid = self.root.meta.data.last_task_id + 1
        self.root.meta.save(last_task_id=tid)
        task.task_id.value = str(tid).zfill(5)
        task.slave_id.value = offer.slave_id.value
        cpu_resources = task.resources.add()
        cpu_resources.name = "cpus"
        cpu_resources.role = MEMSQL_SCHEDULER_ROLE
        cpu_resources.type = mesos_pb2.Value.SCALAR
        cpu_resources.scalar.value = cpu
        mem_resources = task.resources.add()
        mem_resources.name = "mem"
        mem_resources.role = MEMSQL_SCHEDULER_ROLE
        mem_resources.type = mesos_pb2.Value.SCALAR
        mem_resources.scalar.value = mem

        if disk is not None:
            ddd_resources = task.resources.add()
            ddd_resources.name = "disk"
            ddd_resources.type = mesos_pb2.Value.SCALAR
            ddd_resources.scalar.value = disk
        return task

    def make_agent_task(self, offer, cpu, mem, disk, agent_host, agent_port, memsql_port, demo_port, memsql_role, cluster_name, install_demo, agent_version, primary_host=None, primary_memsql_port=None):
        agent_task = self.make_task(offer, cpu, mem, disk)
        agent_task.name = "agent task %s" % agent_task.task_id.value
        agent_task.command.value = "/sbin/my_init"
        agent_task.container.type = mesos_pb2.ContainerInfo.DOCKER
        agent_task.container.docker.image = "memsql/mesos-executor:latest"
        agent_task.container.docker.force_pull_image = True

        port_resource = agent_task.resources.add()
        port_resource.name = "ports"
        port_resource.role = MEMSQL_SCHEDULER_ROLE
        port_resource.type = mesos_pb2.Value.RANGES
        port_range = port_resource.ranges.range.add()
        port_range.begin = agent_port
        port_range.end = agent_port

        port_resource = agent_task.resources.add()
        port_resource.name = "ports"
        port_resource.role = MEMSQL_SCHEDULER_ROLE
        port_resource.type = mesos_pb2.Value.RANGES
        port_range = port_resource.ranges.range.add()
        port_range.begin = memsql_port
        port_range.end = memsql_port

        port_resource = agent_task.resources.add()
        port_resource.name = "ports"
        port_resource.role = MEMSQL_SCHEDULER_ROLE
        port_resource.type = mesos_pb2.Value.RANGES
        port_range = port_resource.ranges.range.add()
        port_range.begin = demo_port
        port_range.end = demo_port

        agent_task.container.docker.network = mesos_pb2.ContainerInfo.DockerInfo.HOST

        data = {}
        data["ZOOKEEPER_URL"] = ZOOKEEPER_URL
        data["MEMSQL_AGENT_HOST"] = agent_host
        data["MEMSQL_AGENT_PORT"] = agent_port
        data["MEMSQL_PORT"] = memsql_port
        data["MEMSQL_DEMO_PORT"] = demo_port
        data["MEMSQL_ROLE"] = memsql_role
        data["MEMSQL_CLUSTER_NAME"] = cluster_name
        data["MEMSQL_SCHEDULER_NAME"] = SCHEDULER_NAME
        data["MEMSQL_AGENT_VERSION"] = agent_version

        if install_demo:
            data["MEMSQL_DEMO_ENABLED"] = 1

        if primary_host is not None:
            data["MEMSQL_PRIMARY_HOST"] = primary_host
        if primary_memsql_port is not None:
            data["MEMSQL_PRIMARY_MEMSQL_PORT"] = primary_memsql_port

        for key, value in data.items():
            param = agent_task.container.docker.parameters.add()
            param.key = "env"
            param.value = "%s=%s" % (key, value)

        return agent_task

    # scheduler api
    def registered(self, driver, frameworkId, masterInfo):
        if frameworkId.value != self.root.meta.data.framework_id:
            self.root.meta.save(framework_id=frameworkId.value)
            logger.info("Registered with framework ID [%s]" % frameworkId.value)
        else:
            logger.info("Registered with existing framework ID [%s]" % frameworkId.value)
        # Tell the driver to send us status updates for all tasks associated
        # with this framework.
        driver.reconcileTasks([])

    def reregistered(self, driver, masterInfo):
        logger.info("Reregistered with master")
        driver.reconcileTasks([])

    def disconnected(self, driver):
        logger.info("Disconnected from master")

    def resourceOffers(self, driver, offers):
        logger.debug("Got %d offers" % len(offers))

        clusters = self.root.clusters
        logger.debug("Current clusters: %s" % clusters.records)

        for offer in offers:
            didathing = False
            logger.debug("Got resource offer [%s]" % offer.id.value)

            work = None
            for cluster in clusters:
                if cluster.data.status != const.ClusterStatus.CREATING:
                    continue
                work = cluster
                break

            if self.shuttingDown:
                logger.debug("Shutting down: declining offer on [%s]" % offer.hostname)
                driver.declineOffer(offer.id)
                continue
            elif work is None:
                logger.debug("Nothing to do, declining offer [%s]" % offer.id)
                driver.declineOffer(offer.id)
                continue

            cpus, mem, disk, ports = utils.get_resources(offer.resources, MEMSQL_SCHEDULER_ROLE)
            cluster = work

            try:
                data = web_helpers.get_json_from_url(CURRENT_AGENT_VERSION_URL)
                agent_version = data["version"]
            except (web_helpers.GetJSONFromURLException, KeyError) as e:
                logger.error(
                    "Error while getting newest version of MemSQL Agent: %s. "
                    "Rolling back cluster" % str(e))
                continue

            cluster.save(agent_version=agent_version)
            cluster.maybe_create_nodes()
            flavor = cluster.flavor

            if flavor.bigger_than(cpus, mem / 1024, disk / 1024) or len(ports) < AGENT_TASK_PORTS:
                logger.info("Not enough resources for agent task: "
                            "%s cpus, %s mem, %s disk, %s ports but "
                            "need %s, %s ports" % (
                                cpus, mem / 1024, disk / 1024, len(ports),
                                flavor, AGENT_TASK_PORTS))
                driver.declineOffer(offer.id)
                continue

            primary_node = cluster.nodes.find(agent_role=const.AgentRole.PRIMARY)

            nodes = list(cluster.nodes)
            nodes.sort(key=lambda n: 1 if n is primary_node else 2)

            for i, node in enumerate(nodes):
                if primary_node is None:
                    primary_node = node

                if node.data.status == const.ClusterStatus.CREATING:
                    logger.info("Accepting offer for agent on [%s] for node %s" % (offer.hostname, node.data.memsql_role))

                    extras = {}
                    if node.data.agent_role == const.AgentRole.FOLLOWER:
                        extras['primary_host'] = primary_node.data.host
                        extras['primary_memsql_port'] = primary_node.data.memsql_port

                    host = utils.generate_host()
                    task = self.make_agent_task(
                        offer=offer,
                        cpu=flavor.cpu,
                        mem=flavor.memory_mb,
                        disk=flavor.disk_mb,
                        agent_host=host,
                        agent_port=ports[0],
                        memsql_port=ports[1],
                        demo_port=ports[2],
                        memsql_role=node.data.memsql_role,
                        cluster_name=cluster.name,
                        install_demo=cluster.data.install_demo,
                        agent_version=cluster.data.agent_version,
                        **extras)
                    didathing = True
                    driver.launchTasks(offer.id, [task])

                    node.save(
                        task_id=task.task_id.value,
                        status=const.ClusterStatus.WAITING_FOR_AGENTS,
                        host=host,
                        host_ip=socket.gethostbyname(offer.hostname),
                        agent_port=ports[0],
                        memsql_port=ports[1],
                        demo_port=ports[2])

                    # save this data in the cluster
                    if node.data.agent_role == const.AgentRole.PRIMARY:
                        cluster.save(
                            primary_host=offer.hostname,
                            primary_agent_port=ports[0],
                            primary_memsql_port=ports[1],
                            primary_demo_port=ports[2]
                        )

                    logger.info("Running agent on (%s) %s:%d, %d, %d" % (host, offer.hostname, ports[0], ports[1], ports[2]))
                    break

                if i == len(nodes) - 1:
                    cluster.save(status=const.ClusterStatus.WAITING_FOR_AGENTS)

            if not didathing:
                logger.debug("Not doing anything anymore, declining offer [%s]" % offer.id)
                driver.declineOffer(offer.id)

    def offerRescinded(self, driver, offer_id):
        logger.info("Offer for [%s] rescinded" % offer_id)

    def statusUpdate(self, driver, update):
        task_id = update.task_id.value
        stateName = NAME_MAP[update.state]
        update_str = ""
        if update.state in TERMINAL_STATES:
            # Only log the full update if the state is terminal.
            update_str = str(update)
        logger.info(
            "Task [%s] is in state [%s] %s" % (task_id, stateName, update_str))

        clusters = self.root.clusters
        all_nodes = []
        for cluster in clusters:
            all_nodes += list(cluster.nodes)

        node = None
        for n in all_nodes:
            if n.data.task_id == task_id:
                node = n
                break
        if node is None:
            if update.state not in TERMINAL_STATES:
                # If we don't know about this task in Zookeeper, kill it.
                t = mesos_pb2.TaskID()
                t.value = task_id
                driver.killTask(t)
            return

        if update.state == mesos_pb2.TASK_RUNNING:  # Running
            self.tasksRunning += 1
        elif update.state > 0 and update.state in TERMINAL_STATES:
            self.tasksRunning -= 1

        if update.state in ( mesos_pb2.TASK_LOST, mesos_pb2.TASK_FAILED ):
            self._handle_lost_node(node)

    def frameworkMessage(self, driver, executorId, slaveId, message):
        logger.info("Recieved message: %s" % message)

    def executorLost(self, driver, executorId, slaveId, status):
        logger.info("Executor [%s] lost: %s" % (executorId, status))

    def slaveLost(self, driver, slave_id):
        logger.info("Slave [%s] lost" % slave_id)

    def error(self, driver, message):
        logger.info("ERROR [%s]" % message)

    def _handle_lost_node(self, node):
        # The node is in a Collection, which is a child of a Cluster, so to
        # get the cluster in question we need the node's grandparent.
        cluster = node.parent.parent

        if node.data.agent_role == const.AgentRole.PRIMARY:
            self._create_new_primary(cluster, node)
        elif node.data.agent_role == const.AgentRole.FOLLOWER and node.data.agent_id is not None:
            self._remove_node_from_primary(cluster, node)

        cluster.save(status=const.ClusterStatus.CREATING)
        node.save(status=const.ClusterStatus.CREATING, task_id=None, agent_id=None)

    def _create_new_primary(self, cluster, node):
        child_agg = None
        nodes = list(cluster.nodes)
        for n in nodes:
            if n.data.memsql_role == const.MemSQLRole.CHILD:
                child_agg = n
                break
        if child_agg is None:
            # If there are no child aggs, just create a new primary. We will
            # set this node back to CREATING in _handle_lost_node above, which
            # will cause us to create a new task with a primary agent in
            # resourceOffers above, and the ClusterMonitor thread will
            # automatically tell all other nodes to follow the new primary that
            # we create.
            logger.info("Deploying a new primary node for cluster %s" % cluster.name)
            return

        # Otherwise, promote this child agg to being a primary.  We run the
        # AGGREGATOR SET AS MASTER command in its own thread because it can
        # take several minutes to finish.
        logger.info(
            "Promoting child aggregator at %s:%d to a primary node for "
            "cluster %s"
            % (child_agg.data.host_ip, child_agg.data.agent_port, cluster.name))
        promote_thread = Thread(
            target=self._promote_child_agg_memsql, args=(cluster, child_agg))
        promote_thread.start()
        child_agg.save(
            agent_role=const.AgentRole.PRIMARY,
            memsql_role=const.MemSQLRole.MASTER)
        # Recreate this node as a child aggregator.
        node.save(
            agent_role=const.AgentRole.FOLLOWER,
            memsql_role=const.MemSQLRole.CHILD)
        cluster.save(
            primary_host=child_agg.data.host_ip,
            primary_agent_port=child_agg.data.agent_port)

    def _remove_node_from_primary(self, cluster, node):
        primary_client = api_client.ApiClient(
            cluster.data.primary_host, cluster.data.primary_agent_port)
        memsqls = []
        try:
            memsqls = primary_client.call("topology/memsql/query", {
                "colocated_agent_id": node.data.agent_id
            })
        except (api_client.ApiException, api_client.ConnectionError) as e:
            logger.warning(
                "Error when attempting to remove MemSQL nodes for "
                "agent %s: %s" % (node.data.agent_id, str(e)))

        for memsql in memsqls:
            try:
                primary_client.call("topology/jobs/put", {
                    "target": "primary",
                    "job_type": "memsql_stop_monitoring",
                    "properties": { "memsql_id": memsql["memsql_id"] }
                })
            except (api_client.ApiException, api_client.ConnectionError) as e:
                logger.warning(
                    "Error when attempting to remove MemSQL instance %s "
                    "for agent %s: %s" % (memsql["memsql_id"], node.data.agent_id, str(e)))

        try:
            primary_client.call("topology/agents/delete", {
                "agent_id": node.data.agent_id
            })
        except (api_client.ApiException, api_client.ConnectionError) as e:
            logger.warning(
                "Error when attempting to remove agent %s: %s"
                % (node.data.agent_id, str(e)))

    def _promote_child_agg_memsql(self, cluster, child_agg):
        cluster.save(currently_promoting_master=True)

        try:
            logger.info(
                "Promoting child aggregator at %s:%d to master"
                % (child_agg.data.host_ip, child_agg.data.memsql_port))
            can_connect = False
            try:
                with database.connect(host=child_agg.data.host_ip, port=child_agg.data.memsql_port, user="root", password="") as conn:
                    conn.query("SELECT 1")
                    can_connect = True
                    conn.execute("AGGREGATOR SET AS MASTER")
            except database.OperationalError as e:
                if can_connect:
                    logger.error(
                        "Could not promote child agg to master for cluster %s: %s"
                        % (cluster.name, str(e)))
                    return
        finally:
            cluster.save(currently_promoting_master=False)
