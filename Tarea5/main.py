from dnserver import DNSServer
from dnslib import DNSRecord
import time

server = DNSServer.from_toml('zones.toml', port=5053)
server.start()
assert server.is_running

queries = [
    ("misitio.com", "A"),
    ("alias.com", "CNAME"),
    ("email.com", "MX"),
    ("group.com", "NS"),
    ("text.com", "TXT"),
    ("soaex.com", "SOA"),
    ("testing.com", "TXT"),
    ("_caldavs._tcp.example.com", "SRV"),
]

try:
    for name, qtype in queries:
        q = DNSRecord.question(name, qtype)
        resp = q.send("127.0.0.1", 5053, timeout=2)
        print(f"== {name} {qtype} ==")
        print(DNSRecord.parse(resp))
        time.sleep(0.1)
finally:
    server.stop()