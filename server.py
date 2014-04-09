#!/usr/bin/env python
import sys
import json
import functools

from twisted.python import log
from twisted.internet import reactor, defer
from twisted.web import static, server

from autobahn.twisted.resource import WebSocketResource
from autobahn.twisted.websocket import WebSocketServerProtocol, \
    WebSocketServerFactory

import txtorcon


class WSProtocol(WebSocketServerProtocol):

    @defer.inlineCallbacks
    def onOpen(self):
        self.factory.register(self)

        conn = self.factory.tor_protocol
        info = yield conn.get_info('version', 'dormant', 'process/pid',
                                   'process/user', 'address', 'status/version/current',
                                   'net/listeners/socks')
        conf = yield conn.get_conf('ExitPolicy', 'Address', 'SocksPort')
        info.update(conf)

        self.factory.broadcast(json.dumps({'type': 'info',
                                           'data': info}))

    def connectionLost(self, reason):
        WebSocketServerProtocol.connectionLost(self, reason)
        self.factory.unregister(self)


class WSFactory(WebSocketServerFactory):

    def __init__(self, url, control_connection):
        WebSocketServerFactory.__init__(self, url)
        self.clients = []
        self.tor_protocol = control_connection

    def register(self, client):
        if client not in self.clients:
            print("Registering client {}".format(client.peer))
            self.clients.append(client)

    def unregister(self, client):
        if client in self.clients:
            print("Unregistering client {}".format(client.peer))
            self.clients.remove(client)

    def broadcast(self, msg):
        msg = str(msg).encode('utf8')
        for c in self.clients:
            c.sendMessage(msg)


def bandwidth_event(factory, data):
    ## could use stem to parse the event payload, but it's just two
    ## ints.

    r, w = map(int, data.split())
    factory.broadcast(json.dumps({
        "type": "bw",
        "data": dict(read=r, written=w)
    }))

def an_error(failure):
    print "Error:", failure.getErrorMessage()
    reactor.stop()              # scorch the earth!

def setup_complete(connection):
    print "Connected to Tor (or launched our own)", connection

    factory = WSFactory("ws://localhost:9000", connection)
    factory.protocol = WSProtocol

    connection.add_event_listener('BW', functools.partial(bandwidth_event, factory))

    root = static.File("public/")
    resource = WebSocketResource(factory)
    root.putChild("ws", resource)
    reactor.listenTCP(9000, server.Site(root))

def progress(*args):
    '''percent, tag, description'''
    print '%2f%%: %s: %s' % args

def main(launch_tor=False):
    log.startLogging(sys.stdout)

    control_port = 9051
    if launch_tor:
        control_port = 9151
        config = txtorcon.TorConfig()
        config.ControlPort = control_port
        config.SocksPort = 0
        d = txtorcon.launch_tor(config, reactor, progress_updates=progress)

        ## launch_tor returns a TorProcessProtocol
        ## ...so we grab out the TorControlProtocol instance in order
        ## to simply use the same callback on "d" below
        d.addCallback(lambda pp: pp.tor_protocol)

    else:
        ## if build_state=True, then we get a TorState() object back
        d = txtorcon.build_tor_connection((reactor, '127.0.0.1', control_port),
                                          build_state=False)

    d.addCallback(setup_complete).addErrback(an_error)

    try:
        reactor.run()

    except KeyboardInterrupt:
        pass  # ctrl+c


if __name__ == '__main__':
    main()
