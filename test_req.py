import urllib.request, json, urllib.error
req = urllib.request.Request(
    'http://127.0.0.1:8002/api/v1/workspace/chat', 
    data=json.dumps({'message': 'paper giai quyêt bài toan nào vậy?'}).encode(), 
    headers={'Content-Type': 'application/json'}, 
    method='POST'
)
try:
    resp = urllib.request.urlopen(req, timeout=30)
    print(resp.read().decode())
except urllib.error.HTTPError as e:
    print(f'HTTP {e.code}: {e.read().decode()}')
except Exception as e:
    print(f'Error: {e}')
