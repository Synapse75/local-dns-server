import socket
import time
from dnslib import DNSRecord, QTYPE, RR, A

# ========================
# CONFIGURATION PARAMETERS
# ========================
LOCAL_IP = "127.0.0.1"
LOCAL_PORT = 1234
CACHE_TTL = 300  # seconds
PUBLIC_DNS = ("8.8.8.8", 53)

# Flag: 1 = recursive/iterative, 0 = use public DNS
flag = 0

# Cache format: {domain: (ip, timestamp)}
dns_cache = {}

# Root DNS servers (subset)
ROOT_SERVERS = [
    "198.41.0.4",       # a.root-servers.net
    "199.9.14.201",     # b.root-servers.net
    "192.33.4.12",      # c.root-servers.net
    "199.7.91.13",      # d.root-servers.net
    "192.203.230.10",   # e.root-servers.net
]


# ==========================
# DNS QUERY IMPLEMENTATION
# ==========================
def resolve_from_public_server(query_data):
    """Forward query to public DNS server (8.8.8.8)."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.sendto(query_data, PUBLIC_DNS)
        print(f"[Public DNS] Querying {PUBLIC_DNS[0]}")
        response, _ = s.recvfrom(4096)
    return response


def iterative_query(domain):
    """Perform iterative DNS resolution manually."""
    print(f"[Iterative] Starting resolution for {domain}")
    query = DNSRecord.question(domain)
    current_servers = ROOT_SERVERS.copy()
    max_hops = 10
    
    for hop in range(max_hops):
        print(f"[Iterative] --- Hop {hop+1} ---")
        print(f"[Iterative] Servers to try: {current_servers}")
        
        next_servers = []  # 为下一跳准备服务器列表
        
        for server_ip in current_servers:
            try:
                print(f"[Iterative] Querying server: {server_ip}")
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                    s.settimeout(5)
                    s.sendto(query.pack(), (server_ip, 53))
                    data, _ = s.recvfrom(4096)
                
                reply = DNSRecord.parse(data)
                print(f"[Iterative] Received response from {server_ip}")
                
                # 检查是否有答案
                if reply.rr:
                    print(f"[Iterative] [Success] Found answer at {server_ip}")
                    for rr in reply.rr:
                        if rr.rtype == QTYPE.A:
                            print(f"[Iterative] Final IP: {rr.rdata}")
                    return data
                
                # 详细分析响应内容
                print(f"[Iterative] Response analysis:")
                print(f"  - Answers: {len(reply.rr)}")
                print(f"  - Authority: {len(reply.auth)}")
                print(f"  - Additional: {len(reply.ar)}")
                
                # 处理权威部分（NS记录）
                ns_records = []
                for rr in reply.auth:
                    if rr.rtype == QTYPE.NS:
                        ns_domain = str(rr.rdata)
                        ns_records.append(ns_domain)
                        print(f"[Iterative] Found NS record: {ns_domain}")
                
                # 处理附加部分（A记录）
                a_records = []
                for rr in reply.ar:
                    if rr.rtype == QTYPE.A:
                        ip = str(rr.rdata)
                        a_records.append(ip)
                        print(f"[Iterative] Found A record: {ip}")
                
                # 构建下一级服务器列表
                if a_records:
                    # 优先使用附加记录中的IP
                    next_servers.extend(a_records)
                    print(f"[Iterative] Using A records from additional section: {a_records}")
                elif ns_records:
                    # 如果没有附加记录，解析NS域名
                    print(f"[Iterative] Resolving NS domains: {ns_records}")
                    for ns_domain in ns_records:
                        try:
                            # 注意：这里可能需要简化，避免复杂情况
                            if ns_domain.endswith('.com.') or ns_domain.endswith('.net.'):
                                # 对于常见的TLD，使用系统解析
                                ns_ip = socket.gethostbyname(ns_domain.rstrip('.'))
                                next_servers.append(ns_ip)
                                print(f"[Iterative] Resolved {ns_domain} -> {ns_ip}")
                            else:
                                print(f"[Iterative] Skipping complex NS: {ns_domain}")
                        except Exception as e:
                            print(f"[Iterative] Failed to resolve {ns_domain}: {e}")
                            continue
                
                if next_servers:
                    print(f"[Iterative] Next hop servers: {next_servers}")
                    break  # 跳出当前服务器循环
                else:
                    print(f"[Iterative] No next servers found from {server_ip}")
                    
            except socket.timeout:
                print(f"[Iterative] Timeout from {server_ip}")
                continue
            except Exception as e:
                print(f"[Iterative] Error querying {server_ip}: {e}")
                continue
        
        # 准备下一跳
        if next_servers:
            current_servers = next_servers
        else:
            print(f"[Iterative] No more servers to try")
            break
    
    print(f"[Iterative] Resolution failed after {max_hops} hops")
    return None


# ==========================
# MAIN DNS SERVER FUNCTION  
# ==========================
def local_dns_server():
    """Main DNS server loop."""
    print(f"[*] Local DNS Server running on {LOCAL_IP}:{LOCAL_PORT}")
    print("[*] Use flag=1 for iterative mode, flag=0 for public DNS mode\n")

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server_socket:
        server_socket.bind((LOCAL_IP, LOCAL_PORT))

        while True:
            query_data, client_addr = server_socket.recvfrom(4096)
            query = DNSRecord.parse(query_data)
            qname = str(query.q.qname).strip(".")
            original_id = query.header.id
            
            print(f"\n[Query] Domain requested: {qname}")
            print(f"[Query] Original ID: {original_id}")

            # Check cache - 修改缓存检查逻辑
            if qname in dns_cache:
                cached_data, timestamp = dns_cache[qname]
                if time.time() - timestamp < CACHE_TTL:
                    print(f"[Cache] Found cached record for {qname}")
                    
                    # 直接返回缓存的完整响应数据，但更新ID
                    cached_response = DNSRecord.parse(cached_data)
                    cached_response.header.id = original_id
                    
                    remaining_ttl = CACHE_TTL - int(time.time() - timestamp)
                    print(f"[Cache] TTL remaining: {remaining_ttl}s")
                    
                    # 更新响应中的TTL
                    for rr in cached_response.rr:
                        rr.ttl = remaining_ttl
                    
                    server_socket.sendto(cached_response.pack(), client_addr)
                    print(f"[Cache] Sent cached response to client")
                    continue
                else:
                    print(f"[Cache] Cache expired for {qname}")
                    del dns_cache[qname]

            # Query resolution
            if flag == 0:
                response_data = resolve_from_public_server(query_data)
            else:
                response_data = iterative_query(qname)
                if not response_data:
                    print("[!] Iterative resolution failed. Using public DNS fallback.")
                    response_data = resolve_from_public_server(query_data)

            # Parse and cache response - 修改缓存存储逻辑
            if response_data:
                response = DNSRecord.parse(response_data)
                
                # 关键修复：缓存完整的响应数据，而不是只缓存A记录
                dns_cache[qname] = (response_data, time.time())
                
                # 恢复原始ID
                response.header.id = original_id
                response_data = response.pack()
                
                print(f"[Response] Sending response with ID: {original_id}")
                
                # 打印缓存的内容信息
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


if __name__ == "__main__":
    local_dns_server()
