"""Custom topology example

Two directly connected switches plus a host for each switch:

   host --- switch --- switch --- host

Adding the 'topos' dict with a key/value pair to generate our newly defined
topology enables one to pass in '--topo=mytopo' from the command line.
"""

from mininet.topo import Topo

class MyTopo( Topo ):
    "Simple topology example."

    def __init__( self ):
        "Create custom topo."

        # Initialize topology
        Topo.__init__( self )

        # Add 12 switches
        switch1 = self.addSwitch('s1')
        switch2 = self.addSwitch('s2')
        switch3 = self.addSwitch('s3')
        switch4 = self.addSwitch('s4')
        switch5 = self.addSwitch('s5')
        switch6 = self.addSwitch('s6')
        switch7 = self.addSwitch('s7')
        switch8 = self.addSwitch('s8')
        switch9 = self.addSwitch('s9')
        switch10 = self.addSwitch('s10')
        switch11 = self.addSwitch('s11')
        switch12 = self.addSwitch('s12')
        
        # Add 12 hosts
        # Each host connect to the corresponding switch
        h1 = self.addHost('h1')
        h2 = self.addHost('h2')
        h3 = self.addHost('h3')
        h4 = self.addHost('h4')
        h5 = self.addHost('h5')
        h6 = self.addHost('h6')
        h7 = self.addHost('h7')
        h8 = self.addHost('h8')
        h9 = self.addHost('h9')
        h10 = self.addHost('h10')
        h11 = self.addHost('h11')
        h12 = self.addHost('h12')

        # Add links between switches, followed Abilene Topology
        self.addLink(switch1, switch2)
        self.addLink(switch2, switch5)
        self.addLink(switch2, switch6)
        self.addLink(switch2, switch12)
        self.addLink(switch9, switch12)
        self.addLink(switch9, switch3)
        self.addLink(switch3, switch6)
        self.addLink(switch6, switch7)
        self.addLink(switch7, switch4)
        self.addLink(switch4, switch11)
        self.addLink(switch11, switch10)
        self.addLink(switch10, switch8)
        self.addLink(switch8, switch5)
        self.addLink(switch7, switch5)
        self.addLink(switch4, switch10)
        
        # Add links between host and switch
        self.addLink(h1, switch1)
        self.addLink(h2, switch2)
        self.addLink(h3, switch3)
        self.addLink(h4, switch4)
        self.addLink(h5, switch5)
        self.addLink(h6, switch6)
        self.addLink(h7, switch7)
        self.addLink(h8, switch8)
        self.addLink(h9, switch9)
        self.addLink(h10, switch10)
        self.addLink(h11, switch11)
        self.addLink(h12, switch12)

topos = { 'mytopo': ( lambda: MyTopo() ) }
