import urllib.request, json

# Login
req = urllib.request.Request('http://localhost:8000/api/login',
    data=json.dumps({'username':'admin','kata_laluan':'admin123'}).encode(),
    headers={'Content-Type':'application/json'})
resp = json.loads(urllib.request.urlopen(req).read())
token = resp['access_token']
print('Login: OK -', resp['user']['peranan'])

# Dashboard
req2 = urllib.request.Request('http://localhost:8000/api/dashboard',
    headers={'Authorization': 'Bearer ' + token})
resp2 = json.loads(urllib.request.urlopen(req2).read())
print('Dashboard: OK -', resp2['jumlah_pengundi'], 'pengundi')

# Audit logs
req3 = urllib.request.Request('http://localhost:8000/api/audit-logs',
    headers={'Authorization': 'Bearer ' + token})
resp3 = json.loads(urllib.request.urlopen(req3).read())
print('Audit Logs: OK -', resp3['total'], 'log entries')
for log in resp3['data'][:5]:
    print('  [' + log['tindakan'] + '] ' + log['username'] + ': ' + log['penerangan'][:60])