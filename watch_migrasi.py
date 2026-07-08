"""
Pantau progres migrasi secara automatik setiap 30 saat.
Guna: python watch_migrasi.py
"""
import sys, os, time
sys.path.insert(0, 'backend')
from database import get_db

last_count = 0
stalled_checks = 0

while True:
    try:
        db = get_db()
        c = db.cursor()
        c.execute("SELECT COUNT(*) FROM pengundi WHERE sumber_pdm = 'Migrasi P170'")
        count = c.fetchone()[0]
        
        c.execute("SELECT d.kod, COUNT(*) FROM pengundi p LEFT JOIN dun d ON p.dun_id=d.id WHERE p.sumber_pdm='Migrasi P170' GROUP BY d.kod ORDER BY d.kod")
        per_dun = {r[0]: r[1] for r in c.fetchall()}
        db.close()
        
        now = time.strftime("%H:%M:%S")
        
        if count == last_count:
            stalled_checks += 1
        else:
            stalled_checks = 0
        
        delta = count - last_count
        print(f"[{now}] Migrasi: {count} rekod (+{delta}) | Per DUN: {per_dun}")
        
        if count > 0 and stalled_checks >= 20:  # 10 minit tanpa perubahan
            print("⚠️  Migrasi kelihatan terhenti. Sila semak terminal.")
            break
            
        last_count = count
        time.sleep(30)
        
    except Exception as e:
        print(f"Ralat: {e}")
        time.sleep(30)