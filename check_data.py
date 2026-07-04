import sqlite3, urllib.request, json

# Check local database
conn = sqlite3.connect('pengundi.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Count seed data
cursor.execute("SELECT COUNT(*) as cnt FROM pengundi WHERE sumber_pdm = 'Seed Data'")
seed_count = cursor.fetchone()['cnt']
print(f'Sample data (Seed Data) di tempatan: {seed_count}')

# Count records with 'import' source  
cursor.execute("SELECT COUNT(*) as cnt FROM pengundi WHERE sumber_pdm != 'Seed Data' OR sumber_pdm IS NULL")
real_count = cursor.fetchone()['cnt']
print(f'Data sebenar: {real_count}')

# Group by support status
cursor.execute('SELECT status_sokongan, COUNT(*) as jumlah FROM pengundi GROUP BY status_sokongan ORDER BY jumlah DESC')
print('Sokongan tempatan:')
for r in cursor.fetchall():
    print(f'  {r["status_sokongan"] or "Tiada"}: {r["jumlah"]}')

conn.close()

# Check Render
data = json.dumps({'username':'admin','kata_laluan':'admin123'}).encode()
req = urllib.request.Request('https://jenterapintar-backend.onrender.com/api/login', data=data, headers={'Content-Type':'application/json'})
resp = urllib.request.urlopen(req, timeout=30)
token = json.loads(resp.read())['access_token']

req2 = urllib.request.Request('https://jenterapintar-backend.onrender.com/api/dashboard', headers={'Authorization':'Bearer '+token})
resp2 = urllib.request.urlopen(req2, timeout=30)
dash = json.loads(resp2.read())
print(f'\nDashboard Render:')
print(f'  Jumlah: {dash["jumlah_pengundi"]}')
print(f'  Sokongan: {dash["sokongan"]}')