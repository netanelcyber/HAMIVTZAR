# Networking Basics

## Inspecting interfaces and addresses

The `ip` command from iproute2 is the modern tool for network configuration.

```
ip addr show           # list interfaces and their IP addresses
ip link show           # show link-layer state (up/down)
ip route show          # display the routing table
ip -br addr            # brief, columnar address summary
```

Bring an interface up or down:

```
ip link set eth0 up
ip link set eth0 down
```

The older `ifconfig` and `route` tools (net-tools) do similar things but are
deprecated in favor of `ip`.

## Testing connectivity

```
ping -c 4 example.com      # send 4 ICMP echo requests
traceroute example.com     # show the path packets take
mtr example.com            # combined ping + traceroute, live
```

## DNS lookups

```
dig example.com            # detailed DNS query
dig +short example.com     # just the answer
host example.com           # simpler lookup
nslookup example.com       # interactive-capable lookup
```

The resolver configuration lives in `/etc/resolv.conf`, and static hostname
mappings in `/etc/hosts`.

## Ports and sockets

`ss` shows socket statistics and is the modern replacement for `netstat`.

```
ss -tlnp        # TCP listening sockets with the owning process
ss -tunap       # all TCP and UDP sockets, numeric, with PIDs
ss -s           # summary statistics
```

To find what process is listening on a port:

```
ss -tlnp | grep :8080
lsof -i :8080
```

## Firewall

Many systems use `firewalld` (`firewall-cmd`) or `ufw` as a friendly front end
to the kernel's netfilter. With `ufw`:

```
ufw allow 22/tcp     # allow SSH
ufw enable           # turn the firewall on
ufw status verbose   # show active rules
```

## Transferring data and files

```
curl -O https://example.com/file.tar.gz   # download to a file
wget https://example.com/file.tar.gz       # download with wget
scp file.txt user@host:/path/              # copy over SSH
rsync -avz src/ user@host:/dest/           # efficient sync over SSH
```
