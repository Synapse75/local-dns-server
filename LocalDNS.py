import socket
import time
import threading
from dnslib import DNSRecord, QTYPE

LOCAL_IP = "127.0.0.1"
LOCAL_PORT = 1234
CACHE_TTL = 300
PUBLIC_DNS = ("8.8.8.8", 53)

# 0 = public DNS, 1 = iterative
flag = 1

# Cache format: {domain: (ip, timestamp)}
dns_cache = {}

# Root DNS servers
ROOT_SERVERS = [
    "198.41.0.4",
    "199.9.14.201",
    "192.33.4.12",
    "199.7.91.13",
    "192.203.230.10",
]


def public_dns_server(query_data):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.sendto(query_data, PUBLIC_DNS)
        print(f"[Public DNS] Querying {PUBLIC_DNS[0]}")
        response, _ = s.recvfrom(4096)
    return response


def iterative_searching(domain):
    print(f"[Iterative] Starting resolution for {domain}")
    query = DNSRecord.question(domain)
    current_servers = ROOT_SERVERS.copy()
    max_hops = 10
    
    for hop in range(max_hops):       
        next_servers = []
        
        for server_ip in current_servers:
            try:
                print(f"[Iterative] Querying server: {server_ip}")
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                    s.settimeout(5)
                    s.sendto(query.pack(), (server_ip, 53))
                    data, _ = s.recvfrom(4096)
                
                reply = DNSRecord.parse(data)
                print(f"[Iterative] Received response from {server_ip}\n")
                
                if reply.rr:
                    for rr in reply.rr:
                        if rr.rtype == QTYPE.A:
                            print(f"[Iterative] [Success] Found A record: {rr.rdata}\n")
                            return data
                        elif rr.rtype == QTYPE.CNAME:
                            cname_target = str(rr.rdata).rstrip('.')
                            print(f"[Iterative] Found CNAME: {domain} -> {cname_target}")
                            cname_response = iterative_searching(cname_target)
                            if cname_response:
                                final_response = DNSRecord.question(domain)
                                final_response.header.id = reply.header.id
                                final_response.header.qr = 1
                                final_response.add_answer(rr)
                                
                                cname_reply = DNSRecord.parse(cname_response)
                                for cname_rr in cname_reply.rr:
                                    if cname_rr.rtype == QTYPE.A:
                                        final_response.add_answer(cname_rr)
                                
                                return final_response.pack()
                
                ns_records = []
                for rr in reply.auth:
                    if rr.rtype == QTYPE.NS:
                        ns_domain = str(rr.rdata)
                        ns_records.append(ns_domain)
                
                a_records = []
                for rr in reply.ar:
                    if rr.rtype == QTYPE.A:
                        ip = str(rr.rdata)
                        a_records.append(ip)
                
                if a_records:
                    next_servers.extend(a_records)
                elif ns_records:
                    for ns_domain in ns_records:
                        try:
                            print(f"[Iterative] Resolving NS: {ns_domain}")
                            ns_response = iterative_searching(ns_domain)
                            if ns_response:
                                ns_reply = DNSRecord.parse(ns_response)
                                for ns_rr in ns_reply.rr:
                                    if ns_rr.rtype == QTYPE.A:
                                        ns_ip = str(ns_rr.rdata)
                                        next_servers.append(ns_ip)
                                        print(f"[Iterative] Resolved {ns_domain} -> {ns_ip}")
                                        break
                        except Exception as e:
                            print(f"[Iterative] Failed to resolve {ns_domain}: {e}")
                            continue
                
                if next_servers:
                    break
                    
            except socket.timeout:
                print(f"[Iterative] Timeout from {server_ip}")
                continue
            except Exception as e:
                print(f"[Iterative] Error querying {server_ip}: {e}")
                continue
        
        if next_servers:
            current_servers = next_servers
        else:
            break
    
    print(f"[Iterative] Resolution failed after {max_hops} hops")
    return None


def local_dns_server():
    print(f"[System] Local DNS Server running on {LOCAL_IP}:{LOCAL_PORT}")
    print("[System] Use flag=1 for iterative mode, flag=0 for public DNS mode\n")

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server_socket:
        server_socket.bind((LOCAL_IP, LOCAL_PORT))

        while True:
            query_data, client_addr = server_socket.recvfrom(4096)
            query = DNSRecord.parse(query_data)
            qname = str(query.q.qname).strip(".")
            original_id = query.header.id
            
            print(f"[Query] Domain requested: {qname}")
            print(f"[Query] Original ID: {original_id}\n")

            # Check cache
            if qname in dns_cache:
                cached_data, timestamp = dns_cache[qname]
                print(f"[Cache] Found cached record for {qname}")
                
                cached_response = DNSRecord.parse(cached_data)
                cached_response.header.id = original_id
                
                remaining_ttl = CACHE_TTL - int(time.time() - timestamp)
                print(f"[Cache] TTL remaining: {remaining_ttl}s")
                
                server_socket.sendto(cached_response.pack(), client_addr)
                continue

            if flag == 0:
                response_data = public_dns_server(query_data)
            else:
                response_data = iterative_searching(qname)
                if not response_data:
                    print("[!] Iterative resolution failed. Using public DNS fallback.")
                    response_data = public_dns_server(query_data)

            if response_data:
                response = DNSRecord.parse(response_data)
                
                dns_cache[qname] = (response_data, time.time())
                
                response.header.id = original_id
                response_data = response.pack()
                
                print(f"[Response] Sending response with ID: {original_id}")
                
                cached_records = []
                for rr in response.rr:
                    if rr.rtype == QTYPE.A:
                        cached_records.append(f"A:{rr.rdata}")
                    elif rr.rtype == QTYPE.CNAME:
                        cached_records.append(f"CNAME:{rr.rdata}")
                
                if cached_records:
                    print(f"[Cache Update] {qname} -> {', '.join(cached_records)}")
                
                server_socket.sendto(response_data, client_addr)
            else:
                print("[!] No valid response found.")


def background_cache_cleaner():
    while True:
        time.sleep(60)
        clean_expired_cache()


def clean_expired_cache():
    print("[Cache Cleaner] Running cache cleanup...\n")
    current_time = time.time()
    expired_domains = []
    
    for domain, (cached_data, timestamp) in dns_cache.items():
        if current_time - timestamp >= CACHE_TTL:
            expired_domains.append(domain)
    
    for domain in expired_domains:
        del dns_cache[domain]
    
    if expired_domains:
        print(f"[Cache Cleaner] Cleaned {len(expired_domains)} expired entries: {expired_domains}\n")


if __name__ == "__main__":
    cleaner_thread = threading.Thread(target=background_cache_cleaner, daemon=True)
    cleaner_thread.start()
    print(f"[System] Cache cleaner started, will run every 60 seconds")
    
    local_dns_server()