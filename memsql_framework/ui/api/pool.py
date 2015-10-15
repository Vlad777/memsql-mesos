from tornado.concurrent import Future
import Queue
import sys
import logging

from memsql_framework.util.super_thread import SuperThread
from memsql_framework.ui.api import endpoints

logger = logging.getLogger(__name__)
NUM_WORKERS = 10

class ApiWorker(SuperThread):
    sleep = 0

    def work(self):
        try:
            request = self.context.queue.get(timeout=0.1)
            request.execute(self.context.root)
        except Queue.Empty:
            pass

class ApiRequest(object):
    def __init__(self, name, params, method, future):
        self.name = name
        self.params = params
        self.method = method
        self.future = future

    def execute(self, root):
        try:
            response = endpoints.call(root, self.name, self.params, self.method)
            self.future.set_result(response)
        except Exception:
            self.future.set_exc_info(sys.exc_info())

class Pool(object):
    def __init__(self, thread_manager, root):
        self.root = root
        self.queue = Queue.Queue()
        for _ in range(NUM_WORKERS):
            thread_manager.add(ApiWorker, { "root": root, "queue": self.queue })

    def status(self):
        logger.info('%d queries outstanding' % (self.queue.qsize()))

    def query(self, name, params, method):
        future = Future()
        request = ApiRequest(name, params, method, future)
        self.queue.put(request)
        return future
