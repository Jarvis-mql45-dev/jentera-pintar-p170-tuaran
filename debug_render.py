"""Diagnostic - check if Render is using SQLite or PostgreSQL, and test each dashboard query."""
import requests
import json
import sys

BASE = 'https://jenterapintar-backend.onrender.com'

print('=== DIAGNOSTIC RENDER BACKEND ===')
print()

# 1. Login
r = requests.post(f'{BASE}/api/login', json={'username': 'admin', 'kata_laluan': 'admin123'})
if r.status_code != 200:
    print(f'Login FAILED: {r.text}')
    sys.exit(1)

token = r.json()['access_token']
headers = {'Authorization': f'Bearer {token}'}
print(f'Login: OK - User: {r.json()["user"]["nama_penuh"]}')

# 2. Test pengundi endpoint - check status_fizikal values
r2 = requests.get(f'{BASE}/api/pengundi?per_page=10', headers=headers)
if r2.status_code == 200:
    d = r2.json()
    print(f'Pengundi: {d["total"]} total')
    # Check status_fizikal values
    fizikal_values = set()
    jantina_values = set()
    for item in d['data']:
        fizikal_values.add(item['status_fizikal'])
        jantina_values.add(str(item['jantina']))
    print(f'  status_fizikal values: {fizikal_values}')
    print(f'  jantina values: {jantina_values}')
else:
    print(f'Pengundi FAILED: {r2.status_code}')

# 3. Test dashboard
r3 = requests.get(f'{BASE}/api/dashboard', headers=headers)
print(f'Dashboard: HTTP {r3.status_code}')
if r3.status_code != 200:
    print(f'  Response: {r3.text[:500]}')

# 4. Test dashboard with dm filter
for dm in ['BINGOLON', 'DUALOG']:
    r4 = requests.get(f'{BASE}/api/dashboard?dm={dm}', headers=headers)
    print(f'Dashboard dm={dm}: HTTP {r4.status_code}')
    if r4.status_code != 200:
        print(f'  Response: {r4.text[:300]}')

print()
print('=== SELESAI ===')