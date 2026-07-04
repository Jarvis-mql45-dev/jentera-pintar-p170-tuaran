"""
Import data pengundi dari fail Excel PDM terus ke PostgreSQL via get_db().
Guna: python import_excel_to_pg.py
"""
import os
import sys
import glob
import pandas as pd
from datetime import datetime

# Pastikan boleh import dari folder backend
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
from database import get_db
from auth import hash_kata_laluan

# Mapping kolum Excel -> kolum database
COLUMN_MAP = {
    'NO KP': 'no_kp',
    'IC LAMA': None,  # skip
    'NAMA PENUH': 'nama_penuh',
    'S': 'jantina',  # L/P
    'LAHIR': 'tahun_lahir',
    'DM': 'dm',
    'LOKALITI': 'lokaliti',
    'NO TELEFON': 'no_telefon',
    'K10': None,  # skip - metadata
    'P': None,  # akan dipetakan ke status_sokongan
    'AP': None,
    'H': None,
    'TAK KENAL': None,
    'X                DUNIA': None,
    'SABAH LABUAN': None,
    'LUAR SABAH': None,
    'Perincian': None,
    ' TAGING': None,
    'D': None,
    'TAMBANG': None,
    'SEWA KERETA': None,
    'Delivered': None,
}

def map_status_sokongan(row):
    """Tentukan status_sokongan berdasarkan kolum P / AP / H / TAK KENAL / etc."""
    p = str(row.get('P', '')).strip()
    ap = str(row.get('AP', '')).strip()
    h = str(row.get('H', '')).strip()
    tak_kenal = str(row.get('TAK KENAL', '')).strip()
    x_dunia = str(row.get('X                DUNIA', '')).strip()
    sabah_labuan = str(row.get('SABAH LABUAN', '')).strip()
    luar_sabah = str(row.get('LUAR SABAH', '')).strip()
    
    if p and p.upper() == '1':
        return 'Putih'
    elif ap and ap.upper() == '1':
        return 'Atas Pagar'
    elif h and h.upper() == '1':
        return 'Hitam'
    elif tak_kenal and tak_kenal.upper() == '1':
        return 'Tidak Kenal'
    elif x_dunia and x_dunia.upper() == '1':
        return 'Meninggal Dunia'
    elif sabah_labuan and sabah_labuan.upper() == '1':
        return 'Pengundi Luar Sabah'
    elif luar_sabah and luar_sabah.upper() == '1':
        return 'Pengundi Luar Parlimen'
    else:
        return 'Belum Dikenal Pasti'

def import_excel_to_pg():
    """Baca semua fail Excel PDM dan import ke PostgreSQL."""
    print("=" * 60)
    print("  📤 IMPORT DATA PENGUNDI KE POSTGRESQL (Neon)")
    print("=" * 60)
    
    # Cari semua fail PDM
    pdm_dir = os.path.join(os.path.dirname(__file__), 'DUN N05 MATUNGGUNG')
    excel_files = []
    
    for pdm_folder in sorted(os.listdir(pdm_dir)):
        pdm_path = os.path.join(pdm_dir, pdm_folder)
        if os.path.isdir(pdm_path):
            for f in os.listdir(pdm_path):
                if f.endswith('.xlsx'):
                    excel_files.append(os.path.join(pdm_path, f))
    
    # Cari sheet data PENGUNDI (bukan Dashboard)
    sheet_names = {}
    for f in excel_files:
        xl = pd.ExcelFile(f)
        # Pilih sheet yang bukan 'Dashboard' (sheet data)
        data_sheets = [s for s in xl.sheet_names if s.upper() != 'DASHBOARD']
        if data_sheets:
            sheet_names[f] = data_sheets[0]  # guna sheet data pertama
        else:
            print(f"⚠️  Tiada sheet data dijumpai dalam {os.path.basename(f)}")
    
    if not sheet_names:
        print("❌ Tiada sheet data dijumpai dalam fail Excel!")
        return
    
    print(f"\nDijumpai {len(sheet_names)} fail dengan data pengundi:")
    for f, s in sheet_names.items():
        print(f"  📄 {os.path.basename(f)} -> Sheet '{s}'")
    
    # Sambung ke PostgreSQL
    print("\n🔗 Menyambung ke PostgreSQL...")
    db = get_db()
    cursor = db.cursor()
    print("✅ Sambungan berjaya!")
    
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    total_imported = 0
    total_errors = 0
    
    for filepath, sheet_name in sheet_names.items():
        dm_name = os.path.basename(os.path.dirname(filepath)).replace('PDM ', '')
        print(f"\n📥 Memproses {os.path.basename(filepath)} (DM: {dm_name})...")
        
        df = pd.read_excel(filepath, sheet_name=sheet_name, dtype=str)
        print(f"   Baris dalam Excel: {len(df)}")
        
        # Bersihkan data
        df = df.fillna('')
        
        imported = 0
        errors = 0
        
        for idx, row in df.iterrows():
            no_kp = str(row.get('NO KP', '')).strip()
            nama = str(row.get('NAMA PENUH', '')).strip()
            
            if not no_kp and not nama:
                continue  # skip empty rows
            
            # Sediakan nilai
            jantina = str(row.get('S', '')).strip().upper()
            if jantina not in ('L', 'P'):
                jantina = ''
            
            tahun_lahir = ''
            try:
                tahun_str = str(row.get('LAHIR', '')).strip()
                if tahun_str:
                    tahun_int = int(float(tahun_str))
                    if 1900 <= tahun_int <= 2026:
                        tahun_lahir = tahun_int
            except (ValueError, TypeError):
                pass
            
            no_kp_clean = str(row.get('NO KP', '')).strip().replace('.0', '') if pd.notna(row.get('NO KP')) else ''
            if no_kp_clean and no_kp_clean.isdigit() and len(no_kp_clean) > 12:
                no_kp_clean = no_kp_clean[:12]  # ambil 12 digit pertama
            
            no_telefon_raw = str(row.get('NO TELEFON', '')).strip()
            no_telefon = no_telefon_raw if no_telefon_raw and no_telefon_raw != 'nan' else ''
            
            lokaliti = str(row.get('LOKALITI', '')).strip()
            # Gunakan nama folder sebagai DM jika tiada dalam Excel
            dm_value = str(row.get('DM', '')).strip() or dm_name
            
            status_sokongan = map_status_sokongan(row)
            
            try:
                cursor.execute(
                    """
                    INSERT INTO pengundi (no_kp, nama_penuh, jantina, tahun_lahir, dm, lokaliti, 
                                         no_telefon, status_sokongan, status_fizikal, 
                                         adalah_pemilik_apps, status_rekod, sumber_pdm, dicipta_pada)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    (
                        no_kp_clean if no_kp_clean else None,
                        nama,
                        jantina if jantina else None,
                        tahun_lahir if tahun_lahir else None,
                        dm_value,
                        lokaliti if lokaliti else None,
                        no_telefon if no_telefon else None,
                        status_sokongan,
                        'Hadir',  # status_fizikal default
                        0,        # adalah_pemilik_apps
                        'Sah',    # status_rekod - auto approve
                        os.path.basename(filepath),
                        now
                    )
                )
                imported += 1
            except Exception as e:
                errors += 1
                if errors <= 3:
                    print(f"   ⚠️  Error baris {idx}: {e}")
        
        db.commit()
        total_imported += imported
        total_errors += errors
        print(f"   ✅ {imported} diimport, {errors} gagal")
    
    db.close()
    
    print("\n" + "=" * 60)
    print(f"  📊 RINGKASAN IMPORT:")
    print(f"     ✅ Berjaya: {total_imported}")
    print(f"     ❌ Gagal: {total_errors}")
    print(f"     📈 Jumlah: {total_imported + total_errors}")
    print("=" * 60)
    
    return total_imported

def create_admin():
    """Cipta akaun admin jika belum wujud."""
    print("\n👤 Mencipta akaun admin...")
    db = get_db()
    cursor = db.cursor()
    
    # Semak jika admin sudah wujud
    cursor.execute("SELECT id FROM users WHERE username = %s", ('admin',))
    existing = cursor.fetchone()
    
    if existing:
        print("✅ Akaun admin sudah wujud.")
        db.close()
        return
    
    # Cipta admin baru
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    hashed_pw = hash_kata_laluan('admin123')
    
    cursor.execute(
        """
        INSERT INTO users (username, nama_penuh, kata_laluan, peranan, aktif, dicipta_pada)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        ('admin', 'Admin Utama', hashed_pw, 'Admin', 1, now)
    )
    db.commit()
    db.close()
    print("✅ Akaun admin berjaya dicipta (admin / admin123)")

def verify_results():
    """Verifikasi data dalam PostgreSQL."""
    print("\n🔍 Verifikasi data dalam PostgreSQL...")
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute("SELECT count(*) FROM pengundi")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT count(*) FROM pengundi WHERE status_rekod = 'Sah'")
    approved = cursor.fetchone()[0]
    
    cursor.execute("SELECT count(*) FROM users")
    users = cursor.fetchone()[0]
    
    cursor.execute("SELECT username, peranan FROM users WHERE username = 'admin'")
    admin = cursor.fetchone()
    
    cursor.execute("SELECT dm, count(*) FROM pengundi GROUP BY dm ORDER BY dm")
    by_dm = cursor.fetchall()
    
    db.close()
    
    print(f"\n📊 STATUS DATABASE:")
    print(f"   👥 Pengundi: {total}")
    print(f"   ✅ Diluluskan (Sah): {approved}")
    print(f"   🔐 Pengguna: {users}")
    if admin:
        print(f"   👤 Admin: {admin[0]} ({admin[1]})")
    print(f"\n   📋 Pengundi mengikut DM:")
    for dm, count in by_dm:
        print(f"      - {dm}: {count}")
    
    return total

def main():
    print("=" * 60)
    print("  🚀 IMPORT & SETUP POSTGRESQL (Neon)")
    print("  DUN N05 MATUNGGONG")
    print("=" * 60)
    
    # Langkah 1: Import data
    total = import_excel_to_pg()
    if total is None:
        print("\n❌ Import gagal!")
        return
    
    # Langkah 2: Cipta admin
    create_admin()
    
    # Langkah 3: Verifikasi
    verify_results()
    
    print("\n" + "=" * 60)
    print("  ✅ SEMUA LANGKAH BERJAYA!")
    print("  Data pengundi telah diimport, admin dicipta,")
    print("  dan auto-approve pukal telah dilaksanakan.")
    print("=" * 60)

if __name__ == "__main__":
    main()