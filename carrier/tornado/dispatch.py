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
    
    def registerTransport(self, tDomain, t):
        AbstractTransportDispatcher.registerTransport(self, tDomain, t)
        t.registerSocket(self.io_loop)

    def unregisterTransport(self, tDomain):
        self.getTransport(tDomain).unregisterSocket(self.io_loop)
        AbstractTransportDispatcher.unregisterTransport(self, tDomain)

    def transportsAreWorking(self):
        for transport in self.__sockMap.values():
            if transport.writable():
                return 1
        return 0
    
    def on_timer(self):
        self.handleTimerTick(self.io_loop.time())
