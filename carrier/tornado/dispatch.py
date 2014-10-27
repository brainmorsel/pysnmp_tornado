# Implements I/O over asynchronous sockets
from sys import exc_info
from traceback import format_exception

from pysnmp.carrier.base import AbstractTransportDispatcher
from pysnmp.error import PySnmpError
from tornado.ioloop import IOLoop, PeriodicCallback


class TornadoDispatcher(AbstractTransportDispatcher):
    def __init__(self, io_loop=None):
        AbstractTransportDispatcher.__init__(self)

        self.io_loop = io_loop or IOLoop.current()
        self.timer = PeriodicCallback(self.on_timer,
            self.getTimerResolution()*1000, io_loop=self.io_loop)

        self.timer.start()

    def on_timer(self):
        try:
            self.handleTimerTick(self.io_loop.time())
        except Exception:
            self.timer.stop()
            self.io_loop.stop()
            raise

