from memsql_framework.util.super_thread import SuperThreadStoppingException
from memsql_framework.util.attr_dict import AttrDict
import logging
import time

logger = logging.getLogger(__name__)

class ThreadInfo(object):
    def __init__(self, Class, context, instance):
        self.Class = Class
        self.context = context
        self.instance = instance

class ThreadStartTimeout(Exception):
    """ Raised if start() takes longer than the timeout. """
    pass

class OneOffThreadException(Exception):
    """ Raised if a one-off thread is detected. """
    pass

class ThreadExitingException(SuperThreadStoppingException):
    message = "Thread is exiting"

    def __str__(self):
        return self.message

class ThreadManager(object):
    """ A ThreadManager manages one or more SuperThreads.

    The primary usage of ThreadManager is to restart threads that have died.

    Usage::

        class Foo(SuperThread):
            sleep = 1

            def work(self):
                print(self.context)

        t = ThreadManager({ "foo": "bar" })
        t.add(Foo, { "baz": "bing" })

        t.check()       # first time check runs, all threads will start

        # foo thread will start printing { "foo": "bar", "baz": "bing" } every second

        t.close()       # will signal Foo to stop and block until it does
    """

    def __init__(self, shared_context=None):
        """ Create a ThreadManager.

        :param shared_context: This dictionary will be available as self.context in all of your threads.
        """
        self._shared_context = shared_context
        self._threads = []

    def add(self, ThreadClass, context=None):
        """ Add a SuperThread to the ThreadManager.

        :param ThreadClass: The SuperThread class to run.
        :param context: Additional context to provide to the thread. Will be
            merged with the ThreadManager's shared_context.
        """
        self._threads.append(ThreadInfo(ThreadClass, context, None))

    def find(self, ThreadClass, context=None):
        """ Retrieve ThreadInfo objects for threads that match the provided ThreadClass/context.

        :param ThreadClass: The SuperThread class to check.
        :param context: A key-value dict to decide which thread to remove.
        :returns: ThreadInfo objects for each thread that matches.
        """
        def _match_context(info):
            # check to see that info is a superset of context
            return context is None or (info.context is not None and all(item in info.context.items() for item in context.items()))

        return [i for i in self._threads if i.Class == ThreadClass and _match_context(i)]

    def remove(self, ThreadClass, context=None):
        """ Remove one or more SuperThreads from the ThreadManager.

        .. note::

            * If there are multiple threads of the same type, context will be used to figure out which one(s) to remove.
            * If an instance of the specified ThreadClass is running we will stop it syncronously.

        :param ThreadClass: The SuperThread class to stop.
        :param context: A key-value dict to decide which thread to remove.
        :returns: The number of threads removed.
        """
        to_remove = self.find(ThreadClass, context)
        for info in to_remove:
            self._threads.remove(info)

            if info.instance is not None and info.instance.is_alive():
                info.instance.stop()
                logger.debug("Waiting for %s to exit" % info.instance.__class__.__name__)
                info.instance.join()

        return len(to_remove)

    def start(self, timeout=None):
        """ Start all of the threads, and then block until all of their setup() methods have completed.

        Will raise any exceptions raised by any of the threads.
        """
        logger.debug("Waiting for all threads to start")
        start = time.time()
        while self.check(raise_exceptions=True):
            time.sleep(0.1)
            if timeout:
                diff = time.time() - start
                if diff > timeout:
                    self.close(block=False)
                    raise ThreadStartTimeout("Threads took longer than %f seconds to start." % timeout)

    def check(self, raise_exceptions=False):
        """ Check all of the threads and make sure that they are all running.

        If a thread raises ``ThreadExitingException``, it will not get restarted.

        Returns True if any of the threads are starting.

        :param raise_exceptions: If ``True``, sub-thread exceptions will be raised.
        """
        any_starting = False

        for info in self._threads:
            if info.instance is None or not info.instance.is_alive():
                if info.instance is None:
                    logger.debug("Starting %s" % info.Class.__name__)
                elif info.instance.has_exception():
                    if isinstance(info.instance.get_exception(), ThreadExitingException):
                        logger.info("%s exiting" % info.Class.__name__)
                        continue

                    if raise_exceptions:
                        raise info.instance.get_exception()
                    else:
                        logger.error("%s not running. Restarting..." % info.Class.__name__, exc_info=info.instance.get_exc_info())
                elif info.instance.stopped_by_stopping_exception():
                    logger.info("%s stopped and will not be restarted" % info.Class.__name__)
                else:
                    raise OneOffThreadException("%s not running, but no exception. ThreadManager should not be used to manage one-off threads." % info.Class.__name__)

                context = {}
                if self._shared_context is not None:
                    context.update(self._shared_context)
                if info.context is not None:
                    context.update(info.context)

                info.instance = info.Class()
                info.instance.context = AttrDict(context)
                info.instance.start()

                any_starting = True
            else:
                any_starting |= info.instance.starting()

        return any_starting

    def close(self, block=True):
        """ Signal and wait for all managed threads to exit. """
        running_threads = [ info.instance for info in self._threads if info.instance is not None and info.instance.is_alive() ]
        running_threads.reverse()

        logger.info("Signaling all threads to stop")

        for instance in running_threads:
            instance.stop()

            if block:
                logger.info("Waiting for %s to exit" % instance.__class__.__name__)
                instance.join()
                logger.info("%s exited" % instance.__class__.__name__)

        logger.info("All threads exited")
