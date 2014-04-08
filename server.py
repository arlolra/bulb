#!/usr/bin/env python
import sys
import json
import functools

from twisted.python import log
from twisted.internet import reactor
from twisted.web import static, server

from autobahn.twisted.resource import WebSocketResource
from autobahn.twisted.websocket import WebSocketServerProtocol, \
    WebSocketServerFactory

import stem
from stem.control import EventType, Controller
from stem.process import launch_tor_with_config


class WSProtocol(WebSocketServerProtocol):

    def onOpen(self):
        self.factory.register(self)
        self.sendMessage(json.dumps({
            "type": "info",
            "data": get_info(self.factory.controller)
        }))

    def connectionLost(self, reason):
        WebSocketServerProtocol.connectionLost(self, reason)
        self.factory.unregister(self)


class WSFactory(WebSocketServerFactory):

    def __init__(self, url, controller):
        WebSocketServerFactory.__init__(self, url)
        self.clients = []
        self.controller = controller

    def register(self, client):
        if client not in self.clients:
            print("Registering client {}".format(client.peer))
            self.clients.append(client)

    def unregister(self, client):
        if client in self.clients:
            print("Unregistering client {}".format(client.peer))
            self.clients.remove(client)

    def broadcast(self, msg):
        for c in self.clients:
            c.sendMessage(msg.encode('utf8'))


def _print_event(factory, event):
    factory.broadcast(json.dumps({
        "type": "bw",
        "data": event.__dict__
    }))

def get_info(c):
    return {
        "version": str(c.get_version()),
        "exit_policy": c.get_exit_policy().summary(),
        "user": c.get_user(),
        "pid": c.get_pid()
    }

def main(launch_tor=False):
    log.startLogging(sys.stdout)

    control_port = 9151
    if launch_tor:
        tor_process = launch_tor_with_config(
            config={"ControlPort": control_port},
            completion_percent=5,
        )

    try:
        controller = Controller.from_port(port=control_port)
    except stem.SocketError as exc:
        print("Unable to connect to tor on port %d: %s" % (control_port, exc))
        sys.exit(1)

    controller.authenticate()

    root = static.File("public/")

    factory = WSFactory("ws://localhost:9000", controller)
    factory.protocol = WSProtocol

    resource = WebSocketResource(factory)
    root.putChild("ws", resource)

    print_event = functools.partial(_print_event, factory)
    controller.add_event_listener(print_event, EventType.BW)

    reactor.listenTCP(9000, server.Site(root))
    try:
        reactor.run()
    except KeyboardInterrupt:
        pass  # ctrl+c

    if launch_tor:
        tor_process.kill()


if __name__ == '__main__':
    main()
