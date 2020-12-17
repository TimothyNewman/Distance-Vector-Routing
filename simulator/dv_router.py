"""
Your awesome Distance Vector router

Based on skeleton code by:
  MurphyMc, zhangwen0411, lab352
"""

import sim.api as api
from cs168.dv import RoutePacket, \
                     Table, TableEntry, \
                     DVRouterBase, Ports, \
                     FOREVER, INFINITY

class DVRouter(DVRouterBase):

    # A route should time out after this interval
    ROUTE_TTL = 15

    # Dead entries should time out after this interval
    GARBAGE_TTL = 10

    # -----------------------------------------------
    # At most one of these should ever be on at once
    SPLIT_HORIZON = False
    POISON_REVERSE = False
    # -----------------------------------------------

    # Determines if you send poison for expired routes
    POISON_EXPIRED = False

    # Determines if you send updates when a link comes up
    SEND_ON_LINK_UP = False

    # Determines if you send poison when a link goes down
    POISON_ON_LINK_DOWN = False

    def __init__(self):
        """
        Called when the instance is initialized.
        DO NOT remove any existing code from this method.
        However, feel free to add to it for memory purposes in the final stage!
        """
        assert not (self.SPLIT_HORIZON and self.POISON_REVERSE), \
                    "Split horizon and poison reverse can't both be on"

        self.start_timer()  # Starts signaling the timer at correct rate.

        # Contains all current ports and their latencies.
        # See the write-up for documentation.
        self.ports = Ports()
        self.history = {}
        # This is the table that contains all current routes
        self.table = Table()
        self.table.owner = self


    def add_static_route(self, host, port):
        """
        Adds a static route to this router's table.

        Called automatically by the framework whenever a host is connected
        to this router.

        :param host: the host.
        :param port: the port that the host is attached to.
        :returns: nothing.
        """
        # `port` should have been added to `peer_tables` by `handle_link_up`
        # when the link came up.
        assert port in self.ports.get_all_ports(), "Link should be up, but is not."
        # TODO: fill this in!
        self.table[host] = TableEntry(dst=host, port=port, latency=self.ports.get_latency(port), expire_time=FOREVER)

    def handle_data_packet(self, packet, in_port):
        """
        Called when a data packet arrives at this router.

        You may want to forward the packet, drop the packet, etc. here.

        :param packet: the packet that arrived.
        :param in_port: the port from which the packet arrived.
        :return: nothing.
        """
        for host, entry in self.table.items():
            if packet.dst == entry.dst:
                if entry.latency < INFINITY:
                    self.send(packet, entry.port)


    def send_routes(self, force=False, single_port=None):
        """
        Send route advertisements for all routes in the table.

        :param force: if True, advertises ALL routes in the table;
                      otherwise, advertises only those routes that have
                      changed since the last advertisement.
               single_port: if not None, sends updates only to that port; to
                            be used in conjunction with handle_link_up.
        :return: nothing.
        """
        if force == False:
            for host, entry in self.table.items():
                for port in self.ports.get_all_ports():
                    if (port, entry.dst) not in self.history.keys():
                        self.send_route(port, entry.dst, entry.latency)
                        self.history[(port, entry.dst)] = entry.latency
                    elif self.history[(port, entry.dst)] != entry.latency:
                        self.send_route(port, entry.dst, entry.latency)
                        self.history[(port, entry.dst)] = entry.latency
        if force == True:
            for host, entry in self.table.items():
                for port in self.ports.get_all_ports():
                    if self.SPLIT_HORIZON == True and port == entry.port:
                        continue
                    elif self.POISON_REVERSE == True and port == entry.port:
                        self.send_route(port, entry.dst, INFINITY)
                        self.history[(port, entry.dst)] = INFINITY
                    else:
                        self.send_route(port, entry.dst, entry.latency)
                        self.history[(port, entry.dst)] = entry.latency

    def expire_routes(self):
        """
        Clears out expired routes from table.
        accordingly.
        """
        kill = []
        for host, entry in self.table.items():
            if entry.expire_time == FOREVER:
                continue
            if api.current_time() >= entry.expire_time:
                if self.POISON_EXPIRED == True:
                    self.handle_route_advertisement(entry.dst, INFINITY, entry.port)
                    continue
                kill.append(host)
        for i in kill:
            self.table.pop(i)

    def handle_route_advertisement(self, route_dst, route_latency, port):
        """
        Called when the router receives a route advertisement from a neighbor.

        :param route_dst: the destination of the advertised route.
        :param route_latency: latency from the neighbor to the destination.
        :param port: the port that the advertisement arrived on.
        :return: nothing.
        """
        total = min(route_latency+self.ports.get_latency(port), INFINITY)
        if route_dst not in self.table.keys():
            self.table[route_dst] = TableEntry(dst=route_dst, port=port, latency=total, expire_time=api.current_time()+self.ROUTE_TTL)
        elif self.table[route_dst].port == port:
            self.table[route_dst] = TableEntry(dst=route_dst, port=port, latency=total, expire_time=api.current_time()+self.ROUTE_TTL)
        elif total < self.table[route_dst].latency:
            self.table[route_dst] = TableEntry(dst=route_dst, port=port,latency=total, expire_time=api.current_time()+self.ROUTE_TTL)
        self.send_routes(force=False)

    def handle_link_up(self, port, latency):
        """
        Called by the framework when a link attached to this router goes up.

        :param port: the port that the link is attached to.
        :param latency: the link latency.
        :returns: nothing.
        """
        self.ports.add_port(port, latency)

    def handle_link_down(self, port):
        """
        Called by the framework when a link attached to this router does down.

        :param port: the port number used by the link.
        :returns: nothing.
        """
        self.ports.remove_port(port)
