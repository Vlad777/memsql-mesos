import os
import sys
import time
import datetime
import signal
import logging
from threading import Thread

from mesos.native import MesosSchedulerDriver
from mesos.interface import mesos_pb2

from memsql_framework import SCHEDULER_NAME, DEFAULT_DATA_ROOT_PATH
from memsql_framework.data.root import Root

from memsql_framework.util import log, web_helpers
from memsql_framework.util.attr_dict import AttrDict
from memsql_framework.util.thread_manager import ThreadManager
from memsql_framework.util.super_thread import SuperThread

from memsql_framework.scheduler.scheduler import MemSQLScheduler
from memsql_framework.scheduler.cluster_monitor import ClusterMonitor
from memsql_framework.ui.api.pool import Pool
from memsql_framework.ui.server import WebServer

import mesos.cli as mesos

MESOS_MASTER_URL = os.environ['MESOS_MASTER_URL']
if MESOS_MASTER_URL.startswith("zk://"):
    MESOS_MASTER_URL=mesos.resolve(MESOS_MASTER_URL).strip()

ZOOKEEPER_URL = os.environ['ZOOKEEPER_URL']

# these are provided by marathon to tell us where we are running
EXTERNAL_WEB_HOST = os.environ.get('HOST', 'localhost')
EXTERNAL_WEB_PORT = int(os.environ.get('PORT0', 9000))

SCHEDULER_ROLE = os.environ.get("MEMSQL_SCHEDULER_ROLE", "*")
SCHEDULER_USER = os.environ.get("MEMSQL_SCHEDULER_USER", "")

MESOS_AUTHENTICATE = os.environ.get("MESOS_AUTHENTICATE", False)

# timeouts in seconds
SHUTTING_DOWN = False
START_TIMEOUT = 30
SHUTDOWN_TIMEOUT = 30
FAILOVER_TIMEOUT = 365 * 24 * 60 * 60

logger = logging.getLogger(__name__)

def setup(data_root_path=DEFAULT_DATA_ROOT_PATH):
    thread_manager = ThreadManager()

    log.setup()
    root = Root(data_root_path).connect(ZOOKEEPER_URL)
    pool = Pool(thread_manager, root)
    return (thread_manager, root, pool)

def run_ui(root_path):
    thread_manager, data_root, pool = setup()

    ui = WebServer()
    ui.context = AttrDict({
        "host": "0.0.0.0",
        "port": EXTERNAL_WEB_PORT,
        "root_path": root_path,
        "pool": pool
    })

    class ReloadRoot(SuperThread):
        sleep = 1

        def work(self):
            data_root.load()

    thread_manager.add(ReloadRoot)

    try:
        thread_manager.start(timeout=START_TIMEOUT)
    except Exception:
        logger.error("Failed to start MemSQL Agent.", exc_info=True)
    else:
        ui.start()

        try:
            while ui.is_alive():
                time.sleep(1)
        except KeyboardInterrupt:
            ui.stop()
            ui.join()
            thread_manager.close(block=True)

def run(root_path):
    thread_manager, data_root, pool = setup()

    # Assert that we're running on Mesos 0.22.1 or above.
    try:
        try:
            version_url = "http://%s/state.json" % MESOS_MASTER_URL
            data = web_helpers.get_json_from_url(version_url)
            mesos_version = data["version"]
        except (web_helpers.GetJSONFromURLException, KeyError) as e:
            logger.error(
                "Error while trying to find version information for Mesos "
                "master %s: %s" % (MESOS_MASTER_URL, str(e)))
            sys.exit(1)
        try:
            mesos_version_tuple = tuple(int(x) for x in mesos_version.split('.'))
            if mesos_version_tuple < (0, 22, 1):
                logger.error(
                    "Mesos master at %s is version %s, but we require at least "
                    "Mesos version 0.22.1" % (MESOS_MASTER_URL, mesos_version))
                sys.exit(1)
        except ValueError:
            # If we can't parse the version tuple, we ignore it.
            pass
    except Exception:
        pass

    framework = mesos_pb2.FrameworkInfo()
    framework.user = SCHEDULER_USER
    framework.name = SCHEDULER_NAME
    framework.role = SCHEDULER_ROLE
    framework.failover_timeout = FAILOVER_TIMEOUT
    framework.checkpoint = True
    framework.webui_url = "http://%s:%d" % (EXTERNAL_WEB_HOST, EXTERNAL_WEB_PORT)
    if data_root.meta.data.framework_id is not None:
        framework.id.value = data_root.meta.data.framework_id

    credential = None
    principal = os.environ.get("DEFAULT_PRINCIPAL", None)
    if MESOS_AUTHENTICATE and principal:
        secret = os.environ.get("DEFAULT_SECRET", None)
        framework.principal = principal
        credential = mesos_pb2.Credential()
        credential.principal = principal
        if secret is not None:
            credential.secret = secret

    implicit_acknowledgments = 1
    if os.getenv("MESOS_EXPLICIT_ACKNOWLEDGEMENTS"):
        implicit_acknowledgments = 0

    scheduler = MemSQLScheduler(data_root)
    if credential is not None:
        driver = MesosSchedulerDriver(scheduler, framework, MESOS_MASTER_URL, implicit_acknowledgments, credential)
    else:
        driver = MesosSchedulerDriver(scheduler, framework, MESOS_MASTER_URL, implicit_acknowledgments)

    thread_manager.add(ClusterMonitor, { "driver": driver, "data_root": data_root })
    thread_manager.add(WebServer, {
        "host": "0.0.0.0",
        "port": EXTERNAL_WEB_PORT,
        "root_path": root_path,
        "pool": pool
    })

    def shutdown(*args):
        global SHUTTING_DOWN
        SHUTTING_DOWN = True

        logger.info("MemSQL scheduler is shutting down")
        thread_manager.close(block=True)

        scheduler.shuttingDown = True

        def stop_timeout():
            wait_started = datetime.datetime.now()
            while scheduler.tasksRunning > 0 and SHUTDOWN_TIMEOUT > (datetime.datetime.now() - wait_started).total_seconds():
                time.sleep(1)

            if scheduler.tasksRunning > 0:
                logger.warning("Shutdown by timeout, %d task(s) have not completed" % scheduler.tasksRunning)

            driver.stop(True)

        stop_thread = Thread(target=stop_timeout)
        stop_thread.start()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        thread_manager.start(timeout=START_TIMEOUT)
    except Exception:
        logger.error("Failed to start MemSQL Agent.", exc_info=True)
    else:
        logger.info("Exit with Ctrl-C")

        result = []

        # driver.run() blocks; we run it in a separate thread
        def run_driver_async():
            status = 0 if driver.run() == mesos_pb2.DRIVER_STOPPED else 1
            driver.stop(True)
            result.append(status)
        framework_thread = Thread(target=run_driver_async, args=())
        framework_thread.start()

        while framework_thread.is_alive():
            time.sleep(1)

        sys.exit(result[0])
    finally:
        if not SHUTTING_DOWN:
            shutdown()
