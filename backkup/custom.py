
from mininet.net  import Mininet
from mininet.node import RemoteController
from mininet.link import TCLink
from mininet.cli  import CLI
from mininet.util import quietRun
 
net = Mininet(link=TCLink);
 
# Add links
# set link speeds to 10Mbit/s
linkopts = dict(bw=10)

# initialize switches
s1 = net.addSwitch('s1')
s2 = net.addSwitch('s2')
s3 = net.addSwitch('s3')
s4 = net.addSwitch('s4')
s5 = net.addSwitch('s5')
s6 = net.addSwitch('s6')
s7 = net.addSwitch('s7')
s8 = net.addSwitch('s8')
s9 = net.addSwitch('s9')
s10 = net.addSwitch('s10')
s11 = net.addSwitch('s11')
s12 = net.addSwitch('s12')

# initialize hosts
h1 = net.addHost('h1')
h2 = net.addHost('h2')
h3 = net.addHost('h3')
h4 = net.addHost('h4')
h5 = net.addHost('h5')
h6 = net.addHost('h6')
h7 = net.addHost('h7')
h8 = net.addHost('h8')
h9 = net.addHost('h9')
h10 = net.addHost('h10')
h11 = net.addHost('h11')
h12 = net.addHost('h12')

# Add links between network nodes (Abilene Network)
net.addLink(s1, s2, **linkopts)
net.addLink(s2, s5, **linkopts)
net.addLink(s2, s6, **linkopts)
net.addLink(s2, s12, **linkopts)
net.addLink(s9, s12, **linkopts)
net.addLink(s9, s3, **linkopts)
net.addLink(s3, s6, **linkopts)
net.addLink(s6, s7, **linkopts)
net.addLink(s7, s4, **linkopts)
net.addLink(s4, s11, **linkopts)
net.addLink(s11, s10, **linkopts)
net.addLink(s10, s8, **linkopts)
net.addLink(s8, s5, **linkopts)
net.addLink(s7, s5, **linkopts)
net.addLink(s4, s10, **linkopts)

# attach a host to a switch 
# (creating nodes which allows to communicate to each other)
net.addLink(h1, s1, **linkopts)
net.addLink(h2, s2, **linkopts)
net.addLink(h3, s3, **linkopts)
net.addLink(h4, s4, **linkopts)
net.addLink(h5, s5, **linkopts)
net.addLink(h6, s6, **linkopts)
net.addLink(h7, s7, **linkopts)
net.addLink(h8, s8, **linkopts)
net.addLink(h9, s9, **linkopts)
net.addLink(h10, s10, **linkopts)
net.addLink(h11, s11, **linkopts)
net.addLink(h12, s12, **linkopts)

# Start
net.addController('c', controller=RemoteController,ip='127.0.0.1',port=6633)
net.build()
net.start()
 
# CLI
#CLI( net )
 
# Clean up
net.stop()
