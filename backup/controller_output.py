from datetime import datetime
import time
from pox.lib.revent.revent import EventMixin, Event
import pox.lib.util as util
from pox.core import core
import pox.openflow.libopenflow_01 as of
from collections import defaultdict
import pox.lib.packet as pkt
from collections import namedtuple
from pox.openflow.flow_table import FlowTable, TableEntry
 
log = core.getLogger()
 
switches = {}
switch_ports = {}
adj = defaultdict(lambda:defaultdict(lambda:None))
 
mac_learning = {}

link_flows_matrix = {}
link_timeout_matrix = {}
bandwidth = {}
previous = {}
timeout = 10
max_flows_per_link = 1

# The edge weights based on IGP metrics from Abilene network
ori_weights_topo = [[],\
        [0,0,1,0,0,0,0,0,0,0,0,0,0],\
        [0,1,0,0,0,1176,587,0,0,0,0,0,846],\
        [0,0,0,0,0,0,260,0,0,700,0,0,0],\
        [0,0,0,0,0,0,0,639,0,0,1295,2095,0],\
        [0,0,1176,0,0,0,0,902,1893,0,0,0,0],\
        [0,0,587,260,0,0,0,548,0,0,0,0,0],\
        [0,0,0,0,639,902,548,0,0,0,0,0,0],\
        [0,0,0,0,0,1893,0,0,0,0,366,0,0],\
        [0,0,0,700,0,0,0,0,0,0,0,0,233],\
        [0,0,0,0,1295,0,0,0,366,0,0,861,0],\
        [0,0,0,0,2095,0,0,0,0,0,861,0,0],\
        [0,0,846,0,0,0,0,0,0,233,0,0,0]]

weights_topo = [[],\
        [0,0,1,0,0,0,0,0,0,0,0,0,0],\
        [0,1,0,0,0,1176,587,0,0,0,0,0,846],\
        [0,0,0,0,0,0,260,0,0,700,0,0,0],\
        [0,0,0,0,0,0,0,639,0,0,1295,2095,0],\
        [0,0,1176,0,0,0,0,902,1893,0,0,0,0],\
        [0,0,587,260,0,0,0,548,0,0,0,0,0],\
        [0,0,0,0,639,902,548,0,0,0,0,0,0],\
        [0,0,0,0,0,1893,0,0,0,0,366,0,0],\
        [0,0,0,700,0,0,0,0,0,0,0,0,233],\
        [0,0,0,0,1295,0,0,0,366,0,0,861,0],\
        [0,0,0,0,2095,0,0,0,0,0,861,0,0],\
        [0,0,846,0,0,0,0,0,0,233,0,0,0]]
 
class ofp_match_withHash(of.ofp_match):
        ##Our additions to enable indexing by match specifications
        @classmethod
        def from_ofp_match_Superclass(cls, other):
                match = cls()
               
                match.wildcards = other.wildcards
                match.in_port = other.in_port
                match.dl_src = other.dl_src
                match.dl_dst = other.dl_dst
                match.dl_vlan = other.dl_vlan
                match.dl_vlan_pcp = other.dl_vlan_pcp
                match.dl_type = other.dl_type
                match.nw_tos = other.nw_tos
                match.nw_proto = other.nw_proto
                match.nw_src = other.nw_src
                match.nw_dst = other.nw_dst
                match.tp_src = other.tp_src
                match.tp_dst = other.tp_dst
                return match
               
        def __hash__(self):
                return hash((self.wildcards, self.in_port, self.dl_src, self.dl_dst, self.dl_vlan, self.dl_vlan_pcp, self.dl_type, self.nw_tos, self.nw_proto, self.nw_src, self.nw_dst, self.tp_src, self.tp_dst))
 
 
class Path(object):
        def __init__(self, src, dst, prev, first_port):
                self.src = src
                self.dst = dst
                self.prev = prev
                self.first_port = first_port
       
        def __repr__(self):
                #ret = util.dpid_to_str(self.dst)
                ret = str(self.dst)
                u = self.prev[self.dst]
                while(u != None):
                        #ret = util.dpid_to_str(u) + " -> " + ret
                        ret = str(u) + " -> " + ret
                        u = self.prev[u]
               
                return ret                       
       
        def _tuple_me(self):
               
                list = [self.dst,]
                u = self.prev[self.dst]
                while u != None:
                        list.append(u)
                        u = self.prev[u]
                log.debug("List path: %s", list)
                log.debug("Tuple path: %s", tuple(list))
                return tuple(list)
       
        def __hash__(self):
                return hash(self._tuple_me())
       
        def __eq__(self, other):
                return self._tuple_me() == other._tuple_me()
 
def _get_path(src, dst):
        #Bellman-Ford algorithm
        keys = switches.keys()
        distance = {}
        previous = {}
       
        for dpid in keys:
                distance[dpid] = float("+inf")
                previous[dpid] = None
 
        distance[src] = 0 

        for i in range(len(keys)-1):
                for u in adj.keys(): #nested dict
                        for v in adj[u].keys():
                                #print(u)
                                #print(adj[u].keys())
                                #w = 1
                                w = weights_topo[u][v]
                                if distance[u] + w < distance[v]:
                                        distance[v] = distance[u] + w
                                        previous[v] = u
  
        for u in adj.keys(): #nested dict
                for v in adj[u].keys():
                        #w = 1
                        w = weights_topo[u][v]
                        if distance[u] + w < distance[v]:
                                log.error("Graph contains a negative-weight cycle")
                                return None
       
        first_port = None
        v = dst
        u = previous[v]
        while u is not None:
                if u == src:
                        first_port = adj[u][v]
               
                v = u
                u = previous[v]
                               
        return Path(src, dst, previous, first_port)  #path
 
 
def _install_path(prev_path, match):
        dst_sw = prev_path.dst
        cur_sw = prev_path.dst
        dst_pck = match.dl_dst
       
        msg = of.ofp_flow_mod()
        msg.match = match
        msg.idle_timeout = timeout
        msg.flags = of.OFPFF_SEND_FLOW_REM     
        msg.actions.append(of.ofp_action_output(port = mac_learning[dst_pck].port))
        log.debug("Installing forward from switch %s to output port %s", util.dpid_to_str(cur_sw), mac_learning[dst_pck].port)
        switches[dst_sw].connection.send(msg)
       
        next_sw = cur_sw
        cur_sw = prev_path.prev[next_sw]
        while cur_sw is not None: #for switch in path.keys():
                #FlowTable.add_entry(TableEntry(hard_timeout = 5))
                msg = of.ofp_flow_mod()
                msg.match = match
                #msg.idle_timeout = 1
                msg.hard_timeout = timeout
                msg.flags = of.OFPFF_SEND_FLOW_REM
                log.debug("Installing forward from switch %s to switch %s output port %s", util.dpid_to_str(cur_sw), util.dpid_to_str(next_sw), adj[cur_sw][next_sw])
                msg.actions.append(of.ofp_action_output(port = adj[cur_sw][next_sw]))
                switches[cur_sw].connection.send(msg)
                next_sw = cur_sw
               
                cur_sw = prev_path.prev[next_sw]
 
def _print_rev_path(dst_pck, src, dst, prev_path):
        str = "Reverse path from %s to %s over: [%s->dst over port %s]" % (util.dpid_to_str(src), util.dpid_to_str(dst), util.dpid_to_str(dst), mac_learning[dst_pck].port)
        next_sw = dst
        cur_sw = prev_path[next_sw]
        while cur_sw != None: #for switch in path.keys():
                str += "[%s->%s over port %s]" % (util.dpid_to_str(cur_sw), util.dpid_to_str(next_sw), adj[cur_sw][next_sw])
                next_sw = cur_sw
                cur_sw = prev_path[next_sw]
               
        log.debug(str)
 
 
class NewFlow(Event):
        def __init__(self, prev_path, match, adj):
                Event.__init__(self)
                self.match = match
                self.prev_path = prev_path
                self.adj = adj
       
class Switch(EventMixin):
        _eventMixin_events = set([NewFlow,])

        def __init__(self, connection):
                self.connection = connection
                connection.addListeners(self)
                for p in self.connection.ports.itervalues(): #Enable flooding on all ports until they are classified as links
                        self.enable_flooding(p.port_no)
       
        def __repr__(self):
                return util.dpid_to_str(self.connection.dpid)
       
       
        def disable_flooding(self, port):
                msg = of.ofp_port_mod(port_no = port,
                                                hw_addr = self.connection.ports[port].hw_addr,
                                                config = of.OFPPC_NO_FLOOD,
                                                mask = of.OFPPC_NO_FLOOD)
       
                self.connection.send(msg)
       
 
        def enable_flooding(self, port):
                msg = of.ofp_port_mod(port_no = port,
                                                        hw_addr = self.connection.ports[port].hw_addr,
                                                        config = 0, # opposite of of.OFPPC_NO_FLOOD,
                                                        mask = of.OFPPC_NO_FLOOD)
       
                self.connection.send(msg)
       
        def update_matrices(self):
            for item in link_timeout_matrix.items():
                if item[1] <= time.time():
                    link_flows_matrix.pop(item[0])
                    link_timeout_matrix.pop(item[0])
                    x = item[0][0]
                    y = item[0][1]
                    weights_topo[x][y] = ori_weights_topo[x][y]

        def _handle_PacketIn(self, event):
                def forward(port):
                        """Tell the switch to forward the packet"""
                        msg = of.ofp_packet_out()
                        msg.actions.append(of.ofp_action_output(port = port))       
                        if event.ofp.buffer_id is not None:
                                msg.buffer_id = event.ofp.buffer_id
                        else:
                                msg.data = event.ofp.data
                        msg.in_port = event.port
                        self.connection.send(msg)
                               
                def flood():
                        """Tell all switches to flood the packet, remember that we disable inter-switch flooding at startup"""
                        #forward(of.OFPP_FLOOD)
                        for (dpid,switch) in switches.iteritems():
                                msg = of.ofp_packet_out()
                                if switch == self:
                                        if event.ofp.buffer_id is not None:
                                                msg.buffer_id = event.ofp.buffer_id
                                        else:
                                                msg.data = event.ofp.data
                                        msg.in_port = event.port
                                else:
                                        msg.data = event.ofp.data
                                ports = [p for p in switch.connection.ports if (dpid,p) not in switch_ports]
                                if len(ports) > 0:
                                        for p in ports:
                                                msg.actions.append(of.ofp_action_output(port = p))
                                        switches[dpid].connection.send(msg)
                               
                               
                def drop():
                        """Tell the switch to drop the packet"""
                        if event.ofp.buffer_id is not None: #nothing to drop because the packet is not in the Switch buffer
                                msg = of.ofp_packet_out()
                                msg.buffer_id = event.ofp.buffer_id
                                event.ofp.buffer_id = None # Mark as dead, copied from James McCauley, not sure what it does but it does not work otherwise
                                msg.in_port = event.port
                                self.connection.send(msg)
               
                #log.debug("Received PacketIn")          
                packet = event.parsed

                SwitchPort = namedtuple('SwitchPoint', 'dpid port')
               
                if (event.dpid,event.port) not in switch_ports:                                               # only relearn locations if they arrived from non-interswitch links
                        mac_learning[packet.src] = SwitchPort(event.dpid, event.port)   #relearn the location of the mac-address
               
                if packet.effective_ethertype == packet.LLDP_TYPE:
                        drop()
                        log.debug("Switch %s dropped LLDP packet", self)
                elif packet.dst.is_multicast:
                        flood()
                        log.debug("Switch %s flooded multicast 0x%0.4X type packet", self, packet.effective_ethertype)
                elif packet.dst not in mac_learning:
                        flood() #Let's first learn the location of the recipient before generating and installing any rules for this. We might flood this but that leads to further complications if half way the flood through the network the path has been learned.
                        log.debug("Switch %s flooded unicast 0x%0.4X type packet, due to unlearned MAC address", self, packet.effective_ethertype)
                elif packet.effective_ethertype == packet.ARP_TYPE:
                        #These packets are sent so not-often that they don't deserve a flow
                        #Instead of flooding them, we drop it at the current switch and have it resend by the switch to which the recipient is connected.
                        #flood()
                        drop()
                        dst = mac_learning[packet.dst]
                        #print dst.dpid, dst.port
                        msg = of.ofp_packet_out()
                        msg.data = event.ofp.data
                        msg.actions.append(of.ofp_action_output(port = dst.port))
                        switches[dst.dpid].connection.send(msg)
                        log.debug("Switch %s processed unicast ARP (0x0806) packet, send to recipient by switch %s", self, util.dpid_to_str(dst.dpid))
                else:
                        log.debug("Switch %s received PacketIn of type 0x%0.4X, received from %s.%s", self, packet.effective_ethertype, util.dpid_to_str(event.dpid), event.port)
                        dst = mac_learning[packet.dst]

                        self.update_matrices()                    
    
                        prev_path = _get_path(self.connection.dpid, dst.dpid)
                        
                        path_nodes = map(int, str(prev_path).split(' -> '))
                        hops = len(path_nodes) - 1

                        if hops <= 0:
                            print '*** No more available path to transmit the packet!!!'

                        else:
                            print 'The Shortest Path: %s' %(prev_path)
                            
                            for i in range(hops):
                                if (path_nodes[i], path_nodes[i+1]) in link_flows_matrix:
                                    print 'invalid operation!!!'
                                    #link_flows_matrix[path_nodes[i], path_nodes[i+1]] = \
                                                #link_flows_matrix[path_nodes[i], path_nodes[i+1]] + 1

                                    #if link_flows_matrix[path_nodes[i], path_nodes[i+1]] >= max_flows_per_link:
                                            # link congested, set this link weigth to infinity to disable this link
                                            #weights_topo[path_nodes[i]][path_nodes[i+1]] = float('+inf')

                                            #print 'link %s -> %s currently have reached the maximum traffic flows (%s)' \
                                                #%(path_nodes[i], path_nodes[i+1], link_flows_matrix[path_nodes[i], path_nodes[i+1]])

                                else:
                                    link_flows_matrix[path_nodes[i], path_nodes[i+1]] = 1
                                    link_timeout_matrix[path_nodes[i], path_nodes[i+1]] = time.time() + timeout         
                                    weights_topo[path_nodes[i]][path_nodes[i+1]] = float('+inf')


                        if prev_path is None:
                                flood()
                                return
                        
                        match = ofp_match_withHash.from_packet(packet)
                        _install_path(prev_path, match)
                       
                        #forward the packet directly from the last switch, there is no need to have the packet run through the complete network.
                        drop()
                        dst = mac_learning[packet.dst]
                        msg = of.ofp_packet_out()
                        msg.data = event.ofp.data
                        msg.actions.append(of.ofp_action_output(port = dst.port))
                        switches[dst.dpid].connection.send(msg)
                       
                        self.raiseEvent(NewFlow(prev_path, match, adj))
                        log.debug("Switch %s processed unicast 0x%0.4x type packet, send to recipient by switch %s",\
                             self, packet.effective_ethertype, util.dpid_to_str(dst.dpid))
                    
                        print '\nLink Flows Matrix:\n%s\n' %(link_flows_matrix)
                        print 'Link Timeout Matrix:\n%s\n\n' %(link_timeout_matrix)
                        print '############################################################################################################'

        def _handle_ConnectionDown(self, event):
                log.debug("Switch %s going down", util.dpid_to_str(self.connection.dpid))
                del switches[self.connection.dpid]
                #pprint(switches)
 
               
class NewSwitch(Event):
        def __init__(self, switch):
                Event.__init__(self)
                self.switch = switch
 
 
class Forwarding(EventMixin):
        _core_name = "myforwarding"
        _eventMixin_events = set([NewSwitch,])
        
        def __init__ (self):
                log.debug("Forwarding is initialized")
                               
                def startup():
                        core.openflow.addListeners(self)
                        core.openflow_discovery.addListeners(self)
                        log.debug("Forwarding started")
               
                core.call_when_ready(startup, 'openflow', 'openflow_discovery')
                       
        def _handle_LinkEvent(self, event):
                link = event.link
                #print '************************'
                #print link
                if event.added:
                        log.debug("Received LinkEvent, Link Added from %s to %s over port %d", util.dpid_to_str(link.dpid1), util.dpid_to_str(link.dpid2), link.port1)
                        adj[link.dpid1][link.dpid2] = link.port1
                        switch_ports[link.dpid1,link.port1] = link
                #else:
                        log.debug("Received LinkEvent, Link Removed from %s to %s over port %d", util.dpid_to_str(link.dpid1), util.dpid_to_str(link.dpid2), link.port1)
               
        def _handle_ConnectionUp(self, event):
                log.debug("New switch connection: %s", event.connection)
                sw = Switch(event.connection)
                switches[event.dpid] = sw;
                self.raiseEvent(NewSwitch(sw))
 
def launch (postfix=datetime.now().strftime("%Y%m%d%H%M%S")):
        from log.level import launch
        launch(DEBUG=False)
 
        from samples.pretty_log import launch
        launch()

        from pox.openflow.spanning_tree import launch
        launch()
 
        #from openflow.keepalive import launch
        #launch(interval=15) # 15 seconds
 
        from openflow.discovery import launch
        launch()
        core.registerNew(Forwarding)
