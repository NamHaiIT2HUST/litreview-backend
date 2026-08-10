import urllib.request
import json

try:
    req = urllib.request.Request(
        'http://127.0.0.1:8000/api/v1/papers/00a567cb-d588-4e1c-92e5-7b38e8bb5aab/quality-check',
        method='POST',
        headers={'Accept': 'application/json'}
    )
    with urllib.request.urlopen(req) as response:
        print(response.status)
        print(response.read())
except Exception as e:
    print(e)
    if hasattr(e, 'read'):
        print(e.read().decode('utf-8'))
