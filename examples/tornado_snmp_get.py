import sys
from tornado.ioloop import IOLoop

from pysnmp_tornado.carrier.tornado.dispatch import TornadoDispatcher
from pysnmp_tornado.carrier.tornado.dgram import udp
from pysnmp.entity.rfc3413 import cmdgen
from pysnmp.entity import engine, config
from pysnmp import debug


def cbFun(sendRequestHandle, errorIndication, errorStatus, errorIndex, varBinds, cbCtx):
    if errorIndication:
        print(errorIndication)
    elif errorStatus:
        print('%s at %s' % (
                errorStatus.prettyPrint(),
                errorIndex and varBinds[int(errorIndex)-1][0] or '?'
            )
        )
    else:
        for oid, val in varBinds:
            print('%s = %s' % (oid.prettyPrint(), val.prettyPrint()))
    dispatcher = cbCtx['dispatcher']
    dispatcher.closeDispatcher()
    IOLoop.instance().stop()


def main(argv):
    # Create SNMP engine instance
    snmpEngine = engine.SnmpEngine()
    dispatcher = TornadoDispatcher()
    snmpEngine.registerTransportDispatcher(dispatcher)

    # SecurityName <-> CommunityName mapping
    config.addV1System(snmpEngine, 'my-area', 'public')

    # Specify security settings per SecurityName (SNMPv1 - 0, SNMPv2c - 1)
    config.addTargetParams(snmpEngine, 'my-creds', 'my-area', 'noAuthNoPriv', 1)

    # UDP/IPv4
    config.addSocketTransport(
        snmpEngine,
        udp.domainName,
        udp.UdpSocketTransport().openClientMode()
    )
    config.addTargetAddr(
        snmpEngine,
        'my-router',
        udp.domainName,
        (argv[0], 161),
        'my-creds',
        timeout=3.0,
        retryCount=1
    )

    cbCtx = dict(dispatcher=dispatcher)

    cmdGen = cmdgen.GetCommandGenerator()
    cmdGen.sendReq(
        snmpEngine,
        'my-router',
        ( ('1.3.6.1.2.1.1.1.0', None), ),
        cbFun,
        cbCtx
    )

    IOLoop.instance().start()

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
