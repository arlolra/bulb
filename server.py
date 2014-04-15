#!/usr/bin/env python
import sys
import json
import getopt
import functools
import txtorcon

from twisted.python import log
from twisted.internet import reactor, defer
from twisted.web import static, server

from autobahn.twisted.resource import WebSocketResource
from autobahn.twisted.websocket import WebSocketServerProtocol, \
    WebSocketServerFactory


DEFAULT_PORT = 9000
DEFAULT_CONTROL_PORT = 9151


class options(object):
    control_port = DEFAULT_CONTROL_PORT
    launch_tor = False
    port = DEFAULT_PORT


class WSProtocol(WebSocketServerProtocol):

    @defer.inlineCallbacks
    def onOpen(self):
        self.factory.register(self)
        info = yield get_info(self.factory.tor_protocol)
        self.sendMessage(json.dumps({'type': 'info',
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
            print "Registering client {}".format(client.peer)
            self.clients.append(client)

    def unregister(self, client):
        if client in self.clients:
            print "Unregistering client {}".format(client.peer)
            self.clients.remove(client)

    def broadcast(self, msg):
        msg = str(msg).encode('utf8')
        for c in self.clients:
            c.sendMessage(msg)


@defer.inlineCallbacks
def get_info(conn):
    info = conn.get_info('version', 'dormant', 'process/pid', 'process/user',
                         'address', 'status/version/current',
                         'net/listeners/socks')
    conf = conn.get_conf('ExitPolicy', 'Address', 'SocksPort')
    info = yield info
    conf = yield conf
    info.update(conf)
    defer.returnValue(info)


def bandwidth_event(factory, data):
    r, w = map(int, data.split())
    factory.broadcast(json.dumps({
        "type": "bw",
        "data": dict(read=r, written=w)
    }))


def log_event(factory, level, data):
    factory.broadcast(json.dumps({
        "type": "log",
        "data": {
            "level": level,
            "text": data
        }
    }))


def an_error(failure):
    print "Error:", failure.getErrorMessage()
    reactor.stop()


def setup_complete(connection):
    print "Connected to Tor (or launched our own)", connection

    factory = WSFactory("ws://localhost:%d" % options.port, connection)
    factory.protocol = WSProtocol

    connection.add_event_listener('BW',
                                  functools.partial(bandwidth_event, factory))

    for event in ['INFO', 'NOTICE', 'WARN', 'ERR']:
        connection.add_event_listener(event,
                                      functools.partial(log_event, factory,
                                                        event))

    root = static.File("public/")
    resource = WebSocketResource(factory)
    root.putChild("ws", resource)
    reactor.listenTCP(options.port, server.Site(root))


def progress(*args):
    '''percent, tag, description'''
    print '%2f%%: %s: %s' % args


def usage():
    print """\
Bulb is Tor relay monitor that provides a status dashboard site on localhost.

Usage: %(progname)s --port [PORT] --control_port [PORT]

  -c, --control_port    specify a control port (default "%(control_port)s")
  -h, --help            print this help message
  -p, --port            specify a port on which to run bulb \
(default "%(port)s")
  -t, --launch_tor      have bulb launch a tor

""" % {
        "progname": sys.argv[0],
        "control_port": DEFAULT_CONTROL_PORT,
        "port": DEFAULT_PORT
    }


def main():

    try:
        opts, args = getopt.gnu_getopt(sys.argv[1:], "c:hp:t", [
            "control_port=",
            "help",
            "port",
            "launch_tor"
        ])
    except getopt.GetoptError as err:
        print str(err)
        usage()
        sys.exit(2)

    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
            sys.exit()
        elif o in ("-c", "--control_port"):
            options.control_port = int(a)
        elif o in ("-t", "--launch_tor"):
            options.launch_tor = True
        elif o in ("-p", "--port"):
            options.port = int(a)
        else:
            assert False, "unhandled option"

    log.startLogging(sys.stdout)

    if options.launch_tor:
        config = txtorcon.TorConfig()
        config.ControlPort = options.control_port
        config.SocksPort = 0
        d = txtorcon.launch_tor(config, reactor, progress_updates=progress)

        # launch_tor returns a TorProcessProtocol
        # ...so we grab out the TorControlProtocol instance in order
        # to simply use the same callback on "d" below
        d.addCallback(lambda pp: pp.tor_protocol)

    else:
        # if build_state=True, then we get a TorState() object back
        d = txtorcon.build_tor_connection((reactor, '127.0.0.1',
                                          options.control_port),
                                          build_state=False)

    d.addCallback(setup_complete).addErrback(an_error)

    try:
        reactor.run()

    except KeyboardInterrupt:
        pass  # ctrl+c


if __name__ == '__main__':
    main()
