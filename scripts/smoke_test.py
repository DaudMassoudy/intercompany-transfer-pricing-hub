import urllib.request,json
for u in ['http://localhost:8000/api/v1/health']:
    with urllib.request.urlopen(u,timeout=5) as r: print(u, r.status, r.read().decode())
