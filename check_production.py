import urllib.request
url = 'https://jentera-pintar-p170-tuaran.vercel.app/'
r = urllib.request.urlopen(url, timeout=15)
c = r.read().decode('utf-8')
print(f'HTTP Status: {r.status}')
print(f'Content length: {len(c)}')

# Check key features
checks = [
    'PANEL STRATEGI',
    'ringkasanTableBody',
    'PANEL STRATEGI PILIHAN RAYA P170 TUARAN',
    'fetchRingkasanData',
    '/api/dashboard/ringkasan',
    'JUMLAH',
    'Belum Dikenal Pasti',
    'Ketua Keluarga',
    'interact-draggable',
    'toggleDashboardEditMode',
    'initDashboardInteract',
    'interact(card).unset'
]
for check in checks:
    found = check in c
    print(f'  {check}: {"✅" if found else "❌"}')

# Check for git hash
import re
hashes = re.findall(r'[a-f0-9]{7,40}', c)
if hashes:
    print(f'\nPotential git hashes in output: {hashes[:5]}')