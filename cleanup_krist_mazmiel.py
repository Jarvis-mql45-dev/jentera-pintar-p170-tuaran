"""
Cleanup script: Deactivate "Krist Mazmiel" from ketua_keluarga table
and unlink any pengundi referencing that record.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from backend.database import get_db, USE_POSTGRES

def main():
    db = get_db()
    cursor = db.cursor()
    
    # First, ensure is_active column exists (add via raw SQL for PostgreSQL)
    print("📦 Step 0: Ensure is_active column exists on ketua_keluarga...")
    try:
        if USE_POSTGRES:
            cursor.execute("""
                ALTER TABLE ketua_keluarga
                ADD COLUMN IF NOT EXISTS is_active INTEGER DEFAULT 1
            """)
        else:
            try:
                cursor.execute("ALTER TABLE ketua_keluarga ADD COLUMN is_active INTEGER DEFAULT 1")
            except Exception:
                pass  # Already exists
        db.commit()
        print("✅ Column is_active ensured.")
    except Exception as e:
        print(f"⚠️  Could not add column (may already exist): {e}")
        db.rollback()
    
    # Find Krist Mazmiel in ketua_keluarga table
    cursor.execute("""
        SELECT id, nama_penuh FROM ketua_keluarga 
        WHERE UPPER(nama_penuh) LIKE '%KRIST MAZMIEL%' 
           OR UPPER(nama_penuh) LIKE '%KRIST%MAZMIEL%'
           OR UPPER(nama_penuh) LIKE '%KRIST%'
    """)
    records = cursor.fetchall()
    
    if not records:
        print("❌ No record found for 'Krist Mazmiel' in ketua_keluarga table.")
        db.close()
        return
    
    print(f"\n📋 Found {len(records)} matching record(s):")
    for r in records:
        print(f"  ID: {r[0]}, Nama: {r[1]}")
    
    krist_ids = [r[0] for r in records]
    krist_nama = records[0][1]
    
    # Step 1: Unlink all pengundi referencing these ketua_keluarga_ids
    placeholders = ', '.join(['?'] * len(krist_ids))
    cursor.execute(f"SELECT COUNT(*) FROM pengundi WHERE ketua_keluarga_id IN ({placeholders})", krist_ids)
    pengundi_count = cursor.fetchone()[0]
    
    if pengundi_count > 0:
        print(f"\n⚠️  {pengundi_count} pengundi currently reference these Ketua Keluarga records.")
        cursor.execute(f"UPDATE pengundi SET ketua_keluarga_id = NULL WHERE ketua_keluarga_id IN ({placeholders})", krist_ids)
        db.commit()
        print(f"✅ Unlinked {pengundi_count} pengundi records.")
    else:
        print("\n✅ No pengundi currently reference these Ketua Keluarga records.")
    
    # Step 2: Delete the duplicate records directly (since no FK references exist)
    cursor.execute(f"DELETE FROM ketua_keluarga WHERE id IN ({placeholders})", krist_ids)
    deleted_count = cursor.rowcount
    db.commit()
    print(f"✅ Deleted {deleted_count} duplicate 'Krist Mazmiel' record(s) from ketua_keluarga table.")
    
    db.close()
    print("\n✅ Cleanup complete! All 'Krist Mazmiel' references removed from database.")

if __name__ == "__main__":
    main()