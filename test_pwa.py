"""Test PWA assets on Vercel."""
import requests

BASE = 'https://jentera-pintar-n05-matunggong.vercel.app'

# Test manifest.json
r = requests.get(BASE + '/manifest.json')
print(f'manifest.json: HTTP {r.status_code}, size: {len(r.content)} bytes')
if r.status_code == 200:
    data = r.json()
    print(f'  start_url: {data.get("start_url")}')
    print(f'  scope: {data.get("scope")}')
    print(f'  icons: {len(data.get("icons", []))} icons')

# Test icons
for icon in ['icon-192x192.png', 'icon-512x512.png']:
    r2 = requests.get(f'{BASE}/icons/{icon}')
    print(f'{icon}: HTTP {r2.status_code}, size: {len(r2.content)} bytes, type: {r2.headers.get("content-type")}')

# Test service worker
r4 = requests.get(BASE + '/service-worker.js')
print(f'service-worker.js: HTTP {r4.status_code}, size: {len(r4.content)} bytes')

# Test index.html has manifest link
r5 = requests.get(BASE + '/')
print(f'index.html: HTTP {r5.status_code}')
if b'manifest' in r5.content:
    print('  manifest link: FOUND')
else:
    print('  manifest link: NOT FOUND')

print('PWA test complete')