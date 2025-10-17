# Experiment Report: Local DNS Server

## 1. Introduction
The purpose of this experiment was to implement a local DNS server that can handle DNS queries from clients, maintain a cache for faster responses, and support both iterative DNS resolution and public DNS queries.  
The implementation was done in **Python 3.9** using the `dnslib` library.

---

## 2. System Design and Implementation

### 2.1 Server Functionality
The local DNS server is designed to:

1. Listen for DNS queries from clients on `127.0.0.1:1234`.
2. Send appropriate DNS responses back to clients.
3. Maintain a cache of previous queries with a TTL of 300 seconds.
4. Support iterative resolution starting from root DNS servers.
5. Query public DNS servers when `flag=0`.

---

### 2.2 Cache Mechanism
- The cache stores responses in a dictionary:  
  `{domain: (response_data, timestamp)}`
- Before performing a query, the server checks if the domain exists in the cache and whether its TTL is still valid.
- Cache hits return the stored response immediately; cache misses trigger iterative or public DNS queries.
- A background thread cleans expired cache entries every 60 seconds.

---

### 2.3 Iterative Search
- Iterative search starts from the **root DNS servers**.
- The server queries each DNS server in turn, following NS and A records until the final A record for the domain is found.
- **All server IPs contacted** during the search are printed for logging purposes.
- CNAME records are handled recursively to resolve the canonical name.

---

### 2.4 Public DNS Query
- When `flag=0`, the server forwards queries to a public DNS server (Google 8.8.8.8).
- Responses from the public DNS are cached and returned to the client.

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
- Responses were faster, and cache was updated accordingly.
- IP addresses of the public server were printed for logging.

**2. Iterative Mode**
- All root and intermediate DNS server IPs were printed during resolution.
- Cache hits were observed when querying the same domain multiple times.
- CNAME resolution worked correctly, returning both canonical and final A records.

**3. Cache**
- Subsequent queries for the same domain returned results from cache without performing network queries.
- TTL expiration caused entries to be removed and subsequent queries re-resolved.

---

### 3.3 Sample Output
```
[Query] Domain requested: www.example.com
[Cache] Miss for www.example.com
[Iterative] Hop 1: trying servers ['198.41.0.4', '199.9.14.201', ...]
[Iterative] Querying: 198.41.0.4
[Iterative] Resolved NS server -> 93.184.216.34
[Iterative] A record: 93.184.216.34
[Cache Update] www.example.com -> A:93.184.216.34
```

## 4. Conclusion
- The local DNS server successfully handles queries for multiple domains, using iterative resolution or public DNS depending on the flag.
- The caching mechanism effectively reduces repeated query time and network traffic.
- All functional requirements, including printing server IPs, handling CNAMEs, and cache maintenance, were satisfied.
- The server can be easily tested with standard dig commands, and switching modes is controlled by a simple flag variable.

## 5. Optional Remarks
- Screenshots of dig queries and server console outputs can be included.
- Tables showing cache hits and misses for repeated queries can be added for clarity.
- Timeout handling and exceptions are logged to help debug network issues.