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

from stem.control import EventType, Controller
from stem.process import launch_tor_with_config


class WSProtocol(WebSocketServerProtocol):

    def onOpen(self):
        self.factory.register(self)

    def connectionLost(self, reason):
        WebSocketServerProtocol.connectionLost(self, reason)
        self.factory.unregister(self)


class WSFactory(WebSocketServerFactory):

    def __init__(self, url):
        WebSocketServerFactory.__init__(self, url)
        self.clients = []

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
    factory.broadcast(json.dumps(event.__dict__))


def main():
    log.startLogging(sys.stdout)

    root = static.File("public/")

    factory = WSFactory("ws://localhost:9000")
    factory.protocol = WSProtocol

    resource = WebSocketResource(factory)
    root.putChild("ws", resource)

    reactor.listenTCP(9000, server.Site(root))

    # tor_process = launch_tor_with_config(
    #     config={"ControlPort": "9151"},
    #     completion_percent=5,
    # )

    print_event = functools.partial(_print_event, factory)

    with Controller.from_port(port=9151) as controller:
        controller.authenticate()
        controller.add_event_listener(
            print_event,
            EventType.BW
        )

        try:
            reactor.run()
        except KeyboardInterrupt:
            pass  # ctrl+c

        # tor_process.kill()


if __name__ == '__main__':
    main()
