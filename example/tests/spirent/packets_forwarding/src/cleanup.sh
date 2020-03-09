echo 1 | sudo tee /sys/class/nfb/nfb0/net/nfb0p0/nocarrier

# remove routes
sudo ip route del 192.168.2.0/24 via 192.168.0.100 table 10
sudo ip route del 192.168.1.0/24 via 192.168.0.100 table 10
sudo ip -6 route del 2001::/64 via 2000::0100 table 10
sudo ip -6 route del 2002::/64 via 2000::0100 table 10
# remove ip addresses
sudo ip addr del 192.168.0.11/24 dev nfb0p0
sudo ip -6 address del 2000::0011/64 dev nfb0p0
# shutdown the interface
sudo ip link set dev nfb0p0 down