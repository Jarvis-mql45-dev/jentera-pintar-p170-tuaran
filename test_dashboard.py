"""Full API diagnostic test."""
import requests
import sys

BASE = 'https://jenterapintar-backend.onrender.com'

print(f'Diagnostic tests for {BASE}')
print('=' * 50)

# 1. Login
r = requests.post(f'{BASE}/api/login', json={'username': 'admin', 'kata_laluan': 'admin123'})
print(f'1. Login: HTTP {r.status_code}')
if r.status_code != 200:
    print(f'   FAILED: {r.text}')
    sys.exit(1)

token = r.json()['access_token']
user = r.json()['user']
print(f'   OK - User: {user["nama_penuh"]} ({user["peranan"]})')

headers = {'Authorization': f'Bearer {token}'}

# 2. Pengundi list
r2 = requests.get(f'{BASE}/api/pengundi?per_page=3', headers=headers)
print(f'2. Pengundi list: HTTP {r2.status_code}')
if r2.status_code == 200:
    d = r2.json()
    total = d.get('total', '?')
    nama = d['data'][0]['nama_penuh'] if d.get('data') else '(empty)'
    print(f'   OK - Total: {total}, Sample: {nama}')
else:
    print(f'   FAILED: {r2.text[:200]}')

# 3. PDM list
r3 = requests.get(f'{BASE}/api/pdm', headers=headers)
print(f'3. PDM list: HTTP {r3.status_code}')
if r3.status_code == 200:
    print(f'   OK - PDM: {r3.json()}')
else:
    print(f'   FAILED: {r3.text[:200]}')

# 4. Dashboard
r4 = requests.get(f'{BASE}/api/dashboard', headers=headers)
print(f'4. Dashboard: HTTP {r4.status_code}')
if r4.status_code == 200:
    data = r4.json()
    print(f'   OK - Jumlah: {data["jumlah_pengundi"]}, Umur: {data["purata_umur"]}')
else:
    print(f'   FAILED: {r4.text[:500]}')

print('=' * 50)
if r2.status_code == 200 and r4.status_code == 200:
    print('ALL TESTS PASSED')
else:
    print('SOME TESTS FAILED')
