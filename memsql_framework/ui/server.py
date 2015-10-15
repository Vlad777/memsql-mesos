import sys
import os
import logging

from tornado import web
from tornado import httpserver
from tornado import ioloop
from tornado import gen

from memsql_framework.util.super_thread import SuperThread
from memsql_framework.ui.web_handler import single_file_handler
from memsql_framework.ui.api_handler import ApiHandler

logger = logging.getLogger(__name__)

class WebServer(SuperThread):
    sleep = 0

    def setup(self):
        super(WebServer, self).setup()
        self.host = self.context.host
        self.port = self.context.port
        self.static_path = os.path.join(self.context.root_path, "static")
        self.pool = self.context.pool
        self._loop = ioloop.IOLoop.instance()

    def work(self):
        app = web.Application(
            handlers=[
                (r"/api/(?P<name>.*)/?", ApiHandler, { "pool": self.pool }),
                (r"/favicon.ico", single_file_handler(os.path.join(self.static_path, "images/favicon.ico")), {}),
                ("/(?:.*)", single_file_handler(os.path.join(self.static_path, "html/index.html")), {})
            ],
            compress_response=True,
            log_function=self._tornado_logger,
            static_path=self.static_path
        )

        server = httpserver.HTTPServer(request_callback=app, io_loop=self._loop)
        server.listen(address=self.host, port=self.port)

        self._set_interval(self._check_exit, 1000)
        self._loop.start()

    def _set_interval(self, callback, interval, nowait=True):
        cb = ioloop.PeriodicCallback(callback, interval, io_loop=self._loop)
        cb.start()
        if nowait:
            self._loop.add_callback(callback)

    def _tornado_logger(self, handler):
        exc_info = False
        if handler.get_status() < 400:
            log_method = logger.debug
        elif handler.get_status() < 500:
            log_method = logger.warning
        else:
            exc_info = sys.exc_info() or False
            log_method = logger.error

        request_time = 1000.0 * handler.request.request_time()
        log_method("%d %s %.2fms", handler.get_status(), handler._request_summary(), request_time, exc_info=exc_info)

    @gen.coroutine
    def _check_exit(self):
        if self.stopping():
            self._loop.stop()
            return True
        return False
