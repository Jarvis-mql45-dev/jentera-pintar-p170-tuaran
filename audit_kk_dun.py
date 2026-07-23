"""
Audit all 26 ketua_keluarga records for DUN completeness.
Then backfill missing dun values using PDM_TO_DUN mapping.
"""
import os, sys
sys.path.insert(0, '.')
from backend.database import get_db

# PDM → DUN mapping
PDM_TO_DUN = {
    "BARU-BARU": "N12", "BATANGAN": "N12", "INDAI": "N12", "KINDU": "N12",
    "PENIMBAWAN": "N12", "SERUSUP": "N12", "TAMBALANG": "N12",
    "BERUNGIS": "N13", "GAYANG": "N13", "MARABAHAI": "N13", "MENGKABONG": "N13",
    "NONGKOULUD": "N13", "TELIPOK": "N13", "TUARAN BANDAR": "N13",
    "GAYARATAU": "N14", "KILANG BATA": "N14", "MENGKALADOI": "N14", "RANI": "N14",
    "RENGALIS": "N14", "RUNGUS": "N14", "SAWAH": "N14", "TAMPARULI": "N14",
    "TELIBONG": "N14", "TENGHILAN": "N14", "TOPOKON": "N14",
    "BONGOL": "N15", "KELAWAT": "N15", "KIULU": "N15", "MALANGANG": "N15",
    "MANTOB": "N15", "PAHU": "N15", "PORING": "N15", "PUKAK": "N15",
    "RANGALAU": "N15", "SIMPANGAN": "N15", "TAGINAMBUR": "N15",
    "TIONG SIMPODON": "N15", "TOGOP": "N15", "TOMIS": "N15", "TUDAN": "N15"
}

# DUN code → DUN name lookup
DUN_CODE_TO_NAME = {"N12": "Sulaman", "N13": "Pantai Dalit", "N14": "Tamparuli", "N15": "Kiulu"}

db = get_db()
cursor = db.cursor()

print("=" * 70)
print("AUDIT: All 26 Ketua Keluarga records")
print("=" * 70)

cursor.execute("""
    SELECT id, nama_penuh, dm, COALESCE(dun, '[NULL]') AS dun
    FROM ketua_keluarga
    WHERE is_active = 1
    ORDER BY id
""")

records = cursor.fetchall()
missing_dun = []
for r in records:
    status = "✅" if r[3] != '[NULL]' else "❌"
    print(f"  {status} ID={r[0]:3d} | {r[1]:35s} | DM={str(r[2]):15s} | DUN={r[3]}")
    if r[3] == '[NULL]':
        missing_dun.append(r)

print()
print(f"Total records: {len(records)}")
print(f"Missing DUN: {len(missing_dun)}")

if missing_dun:
    print()
    print("=" * 70)
    print("BACKFILL: Resolving missing DUN using PDM_TO_DUN")
    print("=" * 70)
    
    for r in missing_dun:
        dm = r[2]
        if dm and dm.upper() in PDM_TO_DUN:
            dun_kod = PDM_TO_DUN[dm.upper()]
            dun_nama = DUN_CODE_TO_NAME.get(dun_kod, dun_kod)
            print(f"  ID={r[0]:3d} | {r[1]:35s} | DM={str(dm):15s} → DUN={dun_kod} ({dun_nama})")
            cursor.execute("UPDATE ketua_keluarga SET dun = ? WHERE id = ?", (dun_kod, r[0]))
        else:
            # Try to find DUN by matching DM to PDM table
            cursor.execute("""
                SELECT d.kod FROM pdm p
                JOIN dun d ON d.id = p.dun_id
                WHERE UPPER(p.nama) = ?
                LIMIT 1
            """, (dm.upper(),))
            dun_row = cursor.fetchone()
            if dun_row:
                dun_kod = dun_row[0]
                print(f"  ID={r[0]:3d} | {r[1]:35s} | DM={str(dm):15s} → DUN={dun_kod} (via PDM table)")
                cursor.execute("UPDATE ketua_keluarga SET dun = ? WHERE id = ?", (dun_kod, r[0]))
            else:
                print(f"  ID={r[0]:3d} | {r[1]:35s} | DM={str(dm):15s} → ❌ CANNOT RESOLVE")
    
    db.commit()
    print(f"\n✅ Backfill complete - updated {len(missing_dun)} records")

# Also check if any DM value needs DUN updated even when dun exists
print()
print("=" * 70)
print("VERIFY: Check DM→DUN consistency")
print("=" * 70)

cursor.execute("""
    SELECT id, nama_penuh, dm, COALESCE(dun, '[NULL]') AS dun
    FROM ketua_keluarga
    WHERE is_active = 1
    ORDER BY id
""")
for r in cursor.fetchall():
    status = "✅" if r[3] != '[NULL]' else "❌"
    expected = PDM_TO_DUN.get(r[2].upper()) if r[2] else None
    match = ""
    if r[3] != '[NULL]' and expected and r[3] != expected:
        match = f" ⚠️ Expected {expected} but stored {r[3]}"
    print(f"  {status} ID={r[0]:3d} | {r[1]:35s} | DM={str(r[2]):15s} | DUN={r[3]}{match}")

db.close()
print()
print("Done.")