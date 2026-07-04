"""Test dashboard endpoint and verify fix."""
import requests
import sys

BASE = 'https://jenterapintar-backend.onrender.com'

# Login
r = requests.post(f'{BASE}/api/login', json={'username': 'admin', 'kata_laluan': 'admin123'})
if r.status_code != 200:
    print(f'Login failed: {r.status_code} - {r.text}')
    sys.exit(1)

token = r.json()['access_token']
print(f'Login OK. User: {r.json()["user"]["nama_penuh"]}')

headers = {'Authorization': f'Bearer {token}'}

# Test dashboard
r2 = requests.get(f'{BASE}/api/dashboard', headers=headers)
print(f'Dashboard: HTTP {r2.status_code}')
if r2.status_code == 200:
    data = r2.json()
    print(f'  Jumlah Pengundi: {data["jumlah_pengundi"]}')
    print(f'  Sokongan: {data["sokongan"]}')
    print(f'  Jantina: {data["jantina"]}')
    print(f'  Purata Umur: {data["purata_umur"]}')
    print('✅ DASHBOARD BERJAYA!')
else:
    print(f'Dashboard response: {r2.text[:500]}')
    print('❌ Dashboard gagal')