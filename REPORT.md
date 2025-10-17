# Experiment Report: Local DNS Server

## 1. Introduction

The purpose of this experiment was to implement a local DNS server.  
It can search in two modes: **public DNS query** and **iterative searching**.  
It has a cache function.  
The implementation was done in **Python 3.9**.

---

## 2. System Design and Implementation

### 2.1 Server Function
The local DNS server is designed to:
1. Listen for DNS queries on `127.0.0.1:1234`.
2. Send DNS responses back to clients.
3. Maintain a cache with a TTL of 300 seconds.
4. Support iterative resolution starting from root DNS servers.
5. Query public DNS servers when `flag=0`.

---

### 2.2 Public DNS Query
- When `flag=0`, the server forwards queries to a **public DNS server (Google 8.8.8.8)**.
- Responses from the public DNS are returned to the client.

---

### 2.3 Iterative Search
- When `flag=1`, iterative search starts from the **root DNS servers**.
- The server queries each DNS server in turn until the final A record for the domain is found.
- **All server IPs contacted** during the search are printed.
- CNAME records are handled recursively to resolve the canonical name.

---

### 2.4 Cache Mechanism
- The cache stores responses from **both modes** in a dictionary:  
  `{domain: (response_data, timestamp)}`
- Before querying, the server checks if the domain exists in the cache.
- **Cache hits**: return the stored response immediately.
- **Cache misses**: trigger iterative or public DNS queries.
- A thread cleans expired cache entries every 60 seconds.

---

### 2.5 Libraries Used
- socket
- threading
- time
- dnslib

---

## 3. Experiment Results

### 3.1 Testing Procedure
**1. Start the local DNS server:**
```
python LocalDNS.py
```
**2. Use `dig` to test queries:**
```
dig www.example.com @127.0.0.1 -p 1234
dig www.baidu.com @127.0.0.1 -p 1234
```
**3. Switch between modes by setting `flag` in LocalDNS.py:**
- `flag = 1` → iterative search
- `flag = 0` → public DNS query

---

### 3.2 Observations
**1. Public DNS Mode**
- Queries were directly forwarded to Google DNS.
- Responses were faster.
- IP addresses of the public server were printed for logging.

**2. Iterative Mode**
- All root and intermediate DNS server IPs were printed during resolution.
- CNAME resolution worked correctly, returning both canonical and final A records.

**3. Cache**
- Subsequent queries for the same domain returned results from cache without performing network queries.
- TTL expiration caused entries to be removed and subsequent queries re-resolved.

---

### 3.3 Sample Output
```
[System] Cache cleaner started, will run every 60 seconds
[System] Local DNS Server running on 127.0.0.1:1234
[System] Use flag=1 for iterative mode, flag=0 for public DNS mode

[Query] Domain requested: www.example.com
[Query] Original ID: 39540

[Cache] Miss for www.example.com

[Mode] Using Public DNS mode

[Public DNS] Querying 8.8.8.8

[Public DNS] CNAME record: www.example.com. -> www.example.com-v4.edgesuite.net.
[Public DNS] CNAME record: www.example.com-v4.edgesuite.net. -> a1422.dscr.akamai.net.
[Public DNS] A record: a1422.dscr.akamai.net. -> 23.197.202.238
[Public DNS] A record: a1422.dscr.akamai.net. -> 23.197.202.241

[Cache Update] www.example.com -> CNAME:www.example.com-v4.edgesuite.net., CNAME:a1422.dscr.akamai.net., A:23.197.202.238, A:23.197.202.241
```
```
[Cache] Miss for www.example.com

[Iterative] Hop 1: trying servers ['198.41.0.4', '199.9.14.201', ...]
[Iterative] Querying: 198.41.0.4
[Iterative] Resolved NS server -> 93.184.216.34
[Iterative] A record: 93.184.216.34
```
```
[Cache] Hit for www.python.org

[Cache] TTL remaining: 299s

[Cache] Records: CNAME:dualstack.python.map.fastly.net., A:167.82.0.223
```
---

## 4. Conclusion
- The local DNS server successfully handles queries for multiple domains, using iterative resolution or public DNS depending on the flag.
- The caching mechanism effectively reduces repeated query time and network traffic.
- All functional requirements, including printing server IPs, handling CNAMEs, and cache maintenance, were satisfied.
- The server can be easily tested with standard dig commands, and switching modes is controlled by a simple flag variable.