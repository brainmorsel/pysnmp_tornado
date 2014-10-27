import socket, errno, sys
import logging

from pysnmp_tornado.carrier.tornado.base import AbstractSocketTransport
from pysnmp.carrier import error
from pysnmp import debug


LOGGER = logging.getLogger(__name__)


sockErrors = { # Ignore these socket errors
    errno.ESHUTDOWN: 1,
    errno.ENOTCONN: 1,
    errno.ECONNRESET: 0,
    errno.ECONNREFUSED: 0,
    errno.EAGAIN: 0,
    errno.EWOULDBLOCK: 0
    }
if hasattr(errno, 'EBADFD'):
    # bad FD may happen upon FD closure on n-1 select() event
    sockErrors[errno.EBADFD] = 1


class DgramSocketTransport(AbstractSocketTransport):
    sockType = socket.SOCK_DGRAM
    retryCount = 3; retryInterval = 1
    def __init__(self, sock=None):
        self.__outQueue = []
        AbstractSocketTransport.__init__(self, sock)

    def openClientMode(self, iface=None):
        if iface is not None:
            try:
                self.socket.bind(iface)
            except socket.error:
                raise error.CarrierError('bind() for %s failed: %s' % (iface is None and "<all local>" or iface, sys.exc_info()[1],))
        return self

    def openServerMode(self, iface):
        try:
            self.socket.bind(iface)
        except socket.error:
            raise error.CarrierError('bind() for %s failed: %s' % (iface, sys.exc_info()[1],))
        return self

    def sendMessage(self, outgoingMessage, transportAddress):
        self.__outQueue.append(
            (outgoingMessage, transportAddress)
            )
        self.set_writable(True)
        LOGGER.debug('sendMessage: outgoingMessage queued (%d octets) %s' % (len(outgoingMessage), debug.hexdump(outgoingMessage)))

    def normalizeAddress(self, transportAddress): return transportAddress

    def __getsockname(self):
        # one evil OS does not seem to support getsockname() for DGRAM sockets
        try:
            return self.socket.getsockname()
        except:
            return ('0.0.0.0', 0)


    def handle_write(self):
        if not self.__outQueue:
            self.set_writable(False)
            return
        outgoingMessage, transportAddress = self.__outQueue.pop(0)
        LOGGER.debug('handle_write: transportAddress %r -> %r outgoingMessage (%d octets) %s' % (self.__getsockname(), transportAddress, len(outgoingMessage), debug.hexdump(outgoingMessage)))
        if not transportAddress:
            LOGGER.debug('handle_write: missing dst address, loosing outgoing msg')
            return
        try:
            self.socket.sendto(outgoingMessage, transportAddress)
        except socket.error:
            if sys.exc_info()[1].args[0] in sockErrors:
                LOGGER.debug('handle_write: ignoring socket error %s' % (sys.exc_info()[1],))
            else:
                raise error.CarrierError('sendto() failed for %s: %s' % (transportAddress, sys.exc_info()[1]))

    def handle_read(self):
        try:
            incomingMessage, transportAddress = self.socket.recvfrom(65535)
            transportAddress = self.normalizeAddress(transportAddress)
            LOGGER.debug('handle_read: transportAddress %r -> %r incomingMessage (%d octets) %s' % (transportAddress, self.__getsockname(), len(incomingMessage), debug.hexdump(incomingMessage)))
            if not incomingMessage:
                # must do something, but don't know what
                return
            else:
                self._cbFun(self, transportAddress, incomingMessage)
                return
        except socket.error:
            if sys.exc_info()[1].args[0] in sockErrors:
                LOGGER.debug('handle_read: known socket error %s' % (sys.exc_info()[1],))
                sockErrors[sys.exc_info()[1].args[0]] and self.handle_close()
                return
            else:
                raise error.CarrierError('recvfrom() failed: %s' % (sys.exc_info()[1],))


