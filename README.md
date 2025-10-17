# Local DNS Server
The first assignment of CUHKSZ course ECE4016

## How to use

### 1. Run the DNS server:
```
python LocalDNS.py  
```

### 2. Use `dig` to test the server:
**Query example.com:**  
```
dig www.example.com @127.0.0.1 -p 1234
```

**Query baidu.com:**  
```
dig www.baidu.com @127.0.0.1 -p 1234
```

### 3. Set the mode:
`flag = 0` → use public DNS server  
`flag = 1` → iterative searching  

### 4. Console output shows:
The IP of all servers passed during iterative search  
Cache hits and updates  