#nfb-eth -Pvc 100GBASE-SR4
nfb-eth -e1
dcprofilterctl -f filter.txt
dcproprfilterctl -l prfilter.txt
dcprowatchdogctl -e0
dcproctl -s 1
echo 0 | sudo tee /sys/class/nfb/nfb0/net/nfb0p0/nocarrier