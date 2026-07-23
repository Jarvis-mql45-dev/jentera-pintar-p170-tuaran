"""
Database Cleanup Script: Pegawai Penyelaras DUN/PDM Mapping
============================================================
1. Maps each pegawai_penyelaras.dm (PDM name) to the correct dun_id via the pdm table
2. Cleans up phone numbers (removes trailing .0)
3. Run: python cleanup_pegawai_dun_pdm.py
"""

import sys
import os
from datetime import datetime

# Ensure backend modules are importable
sys.path.insert(0, os.path.dirname(__file__))

try:
    from backend.database import get_db
    from backend.config import settings
except ImportError as e:
    print(f"❌ Import failed: {e}")
    print("Make sure dependencies are installed: pip install -r backend/requirements.txt")
    sys.exit(1)

def sanitize_phone(phone):
    """Remove trailing .0 from phone numbers"""
    if not phone:
        return None
    cleaned = str(phone).strip()
    if cleaned.endswith('.0'):
        cleaned = cleaned[:-2]
    return cleaned if cleaned else None

def main():
    print("=" * 60)
    print("PEGAWAI PENYELARAS DUN/PDM MAPPING CLEANUP")
    print("=" * 60)
    
    db = get_db()
    cursor = db.cursor()
    
    # Step 1: Get all active pegawai_penyelaras with dm set
    cursor.execute("""
        SELECT pp.id, pp.nama_penuh, pp.dm, pp.dun_id, pp.no_telefon
        FROM pegawai_penyelaras pp
        WHERE pp.aktif = 1
        ORDER BY pp.id
    """)
    rows = cursor.fetchall()
    print(f"\n📊 Found {len(rows)} active pegawai penyelaras records")
    
    dun_updated = 0
    phone_cleaned = 0
    phone_issues = []
    
    for row in rows:
        pp_id = row['id']
        nama = row['nama_penuh']
        dm_val = row['dm']
        current_dun_id = row['dun_id']
        phone = row['no_telefon']
        
        # Step 1: Update phone number if it has trailing .0
        if phone:
            cleaned_phone = sanitize_phone(phone)
            if cleaned_phone != str(phone).strip():
                cursor.execute(
                    "UPDATE pegawai_penyelaras SET no_telefon = ? WHERE id = ?",
                    (cleaned_phone, pp_id)
                )
                phone_cleaned += 1
                phone_issues.append(f"  ✅ {nama}: '{phone}' → '{cleaned_phone}'")
        
        # Step 2: Map DUN from PDM name
        if dm_val and dm_val.strip():
            dm_upper = dm_val.strip().upper()
            
            # Try to find DUN via pdm table
            cursor.execute("""
                SELECT d.id, d.kod, d.nama FROM dun d
                JOIN pdm p ON p.dun_id = d.id
                WHERE UPPER(p.nama) = ?
                LIMIT 1
            """, (dm_upper,))
            dun_row = cursor.fetchone()
            
            if not dun_row:
                # Try matching dm as DUN code directly
                cursor.execute(
                    "SELECT id, kod, nama FROM dun WHERE kod = ? LIMIT 1",
                    (dm_upper,)
                )
                dun_row = cursor.fetchone()
            
            if not dun_row and len(dm_upper) >= 3:
                # Try fuzzy matching: check if dm starts with or contains a DUN code
                for kod in ['N12', 'N13', 'N14', 'N15']:
                    if dm_upper.startswith(kod) or dm_upper == kod:
                        cursor.execute(
                            "SELECT id, kod, nama FROM dun WHERE kod = ? LIMIT 1",
                            (kod,)
                        )
                        dun_row = cursor.fetchone()
                        break
            
            if dun_row:
                new_dun_id = dun_row['id']
                dun_kod = dun_row['kod']
                dun_nama = dun_row['nama']
                
                if current_dun_id != new_dun_id:
                    cursor.execute(
                        "UPDATE pegawai_penyelaras SET dun_id = ?, dikemaskini_pada = ? WHERE id = ?",
                        (new_dun_id, datetime.now().isoformat(), pp_id)
                    )
                    dun_updated += 1
                    old_dun_str = f" (was DUN ID {current_dun_id})" if current_dun_id else " (was NULL)"
                    print(f"  🔗 {nama}: DM='{dm_val}' → DUN {dun_kod} {dun_nama}{old_dun_str}")
            else:
                print(f"  ⚠️  {nama}: DM='{dm_val}' — could not resolve DUN (no matching PDM or DUN code)")
    
    db.commit()
    
    # Summary
    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")
    print(f"✅ DUN mappings updated: {dun_updated}")
    print(f"✅ Phone numbers cleaned: {phone_cleaned}")
    
    if phone_issues:
        print(f"\n📞 Phone numbers cleaned:")
        for issue in phone_issues:
            print(issue)
    
    # If no DUN ID was resolved, also try to infer DUN from dm field using the PDM_DUN_MAP
    cursor.execute("""
        SELECT COUNT(*) FROM pegawai_penyelaras 
        WHERE aktif = 1 AND dun_id IS NULL AND dm IS NOT NULL AND dm != ''
    """)
    still_unmapped = cursor.fetchone()[0]
    if still_unmapped > 0:
        print(f"\n⚠️  {still_unmapped} records still have no DUN mapping.")
        print("These may have PDM names not yet in the pdm table.")
    
    db.close()
    print(f"\n✅ Cleanup completed successfully!")

if __name__ == "__main__":
    main()