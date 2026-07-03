import pandas as pd
import sqlite3
import os
from datetime import datetime

# ===== KONFIGURASI =====
BASE_PATH = 'DUN N05 MATUNGGUNG'
DB_PATH = 'pengundi.db'

# Mapping PDM -> sheet name
PDM_SHEET_MAP = {
    'BINGOLON': 'PENGUNDI BINGOLON',
    'DUALOG': 'PDM DUALOG',
    'INDARASON': 'PDM INDARASON',
    'KANDAWAYON': 'PDM Kandawayon',
    'LAJONG': 'PDM LAJONG',
    'LODUNG': 'PDM LODUNG'
}

# Column indices (0-based) for BINGOLON vs others
# BINGOLON: 24 columns, no 'DUN' column
# Others: 25 columns, has 'DUN' column
COLS_BINGOLON = {
    'no_kp': 1, 'nama': 5, 'jantina': 3, 'lahir': 4,
    'dm': 7, 'lokaliti': 8, 'telefon': 9,
    'p': 11, 'ap': 12, 'h': 13, 'tak_kenal': 14, 'x_dunia': 15
}
COLS_OTHER = {
    'no_kp': 1, 'nama': 5, 'jantina': 3, 'lahir': 4,
    'dm': 8, 'lokaliti': 9, 'telefon': 10,
    'p': 12, 'ap': 13, 'h': 14, 'tak_kenal': 15, 'x_dunia': 16
}


def parse_value(val):
    """Convert NaN to None for SQLite"""
    if pd.isna(val):
        return None
    if isinstance(val, (int, float)):
        if val == int(val):
            return int(val)
        return val
    return str(val).strip()


def determine_sokongan(row, cols):
    """Determine status support based on P, AP, H, TAK KENAL columns"""
    p = str(row[cols['p']]).strip()
    ap = str(row[cols['ap']]).strip()
    h = str(row[cols['h']]).strip()
    tk = str(row[cols['tak_kenal']]).strip()

    # Check if the string equals '1', '1.0', or simply not 'nan' / 'None'
    if p in ['1', '1.0', '1.00']:
        return 'Putih'
    elif ap in ['1', '1.0', '1.00']:
        return 'Atas Pagar'
    elif h in ['1', '1.0', '1.00']:
        return 'Hitam'
    elif tk in ['1', '1.0', '1.00']:
        return 'Tidak Kenal'
    return None


def determine_fizikal(row, cols):
    """Determine physical status based on X DUNIA column"""
    x = str(row[cols['x_dunia']]).strip()
    # If the cell has any value like '1', 'Meninggal', etc., tag as Meninggal Dunia
    if x not in ['nan', 'None', '']:
        return 'Meninggal Dunia'
    return 'Hidup'


def process_pdm(pdm_name, sheet_name):
    """Process a single PDM Excel file and return list of dict records"""
    file_path = os.path.join(BASE_PATH, f'PDM {pdm_name}', f'PDM {pdm_name}.xlsx')
    print(f'  Membaca: {file_path} -> Sheet: {sheet_name}')
    
    # Read all data skipping header row
    df = pd.read_excel(file_path, sheet_name=sheet_name, header=None, skiprows=1)
    
    # Choose column mapping
    is_bingolon = (pdm_name == 'BINGOLON')
    cols = COLS_BINGOLON if is_bingolon else COLS_OTHER
    
    records = []
    skip_count = 0
    for idx, row in df.iterrows():
        no_kp = parse_value(row[cols['no_kp']])
        nama = parse_value(row[cols['nama']])
        
        # Skip rows with no IC and no name
        if not no_kp and not nama:
            skip_count += 1
            continue
        
        # Convert no_kp to string if it's an integer
        if isinstance(no_kp, (int, float)):
            no_kp_str = str(int(no_kp)).strip()
        else:
            no_kp_str = str(no_kp).strip() if no_kp else None
        
        # Handle IC numbers - take last 12 digits if longer
        if no_kp_str and len(no_kp_str) >= 12:
            no_kp_str = no_kp_str[-12:]
        
        record = {
            'no_kp': no_kp_str,
            'nama_penuh': str(nama).strip() if nama else None,
            'jantina': str(row[cols['jantina']]).strip() if pd.notna(row[cols['jantina']]) else None,
            'tahun_lahir': int(row[cols['lahir']]) if pd.notna(row[cols['lahir']]) else None,
            'dm': pdm_name,
            'lokaliti': str(row[cols['lokaliti']]).strip() if pd.notna(row[cols['lokaliti']]) else None,
            'no_telefon': str(parse_value(row[cols['telefon']])) if pd.notna(row[cols['telefon']]) else None,
            'status_sokongan': determine_sokongan(row, cols),
            'status_fizikal': determine_fizikal(row, cols),
            'adalah_pemilik_apps': False,
            'status_rekod': 'Sah',
            'sumber_pdm': pdm_name,
            'dicipta_pada': datetime.now().isoformat()
        }
        records.append(record)
    
    print(f'    -> {len(records)} rekod diproses, {skip_count} baris dikosongkan')
    return records


def main():
    print('=' * 60)
    print('SKRIP MIGRASI DATA PENGUNDI DUN N05 MATUNGGONG')
    print('=' * 60)
    
    all_records = []
    total_files = len(PDM_SHEET_MAP)
    
    for i, (pdm, sheet) in enumerate(PDM_SHEET_MAP.items(), 1):
        print(f'\n[{i}/{total_files}] Memproses {pdm}...')
        records = process_pdm(pdm, sheet)
        all_records.extend(records)
    
    print(f'\n{"=" * 60}')
    print(f'JUMLAH KESELURUHAN: {len(all_records)} rekod')
    print(f'{"=" * 60}')
    
    # Create SQLite database
    print(f'\nMencipta pangkalan data SQLite: {DB_PATH}')
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Drop table if exists
    cursor.execute('DROP TABLE IF EXISTS pengundi')
    
    # Create table
    cursor.execute('''
        CREATE TABLE pengundi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            no_kp TEXT,
            nama_penuh TEXT,
            jantina TEXT,
            tahun_lahir INTEGER,
            dm TEXT,
            lokaliti TEXT,
            no_telefon TEXT,
            status_sokongan TEXT,
            status_fizikal TEXT,
            adalah_pemilik_apps INTEGER DEFAULT 0,
            status_rekod TEXT DEFAULT 'Sah',
            sumber_pdm TEXT,
            dicipta_pada TEXT
        )
    ''')
    
    # Insert data
    insert_sql = '''
        INSERT INTO pengundi 
        (no_kp, nama_penuh, jantina, tahun_lahir, dm, lokaliti, no_telefon, 
         status_sokongan, status_fizikal, adalah_pemilik_apps, status_rekod, sumber_pdm, dicipta_pada)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    '''
    
    batch_size = 500
    total_inserted = 0
    for i in range(0, len(all_records), batch_size):
        batch = all_records[i:i+batch_size]
        values = [
            (
                r['no_kp'], r['nama_penuh'], r['jantina'], r['tahun_lahir'],
                r['dm'], r['lokaliti'], r['no_telefon'],
                r['status_sokongan'], r['status_fizikal'],
                1 if r['adalah_pemilik_apps'] else 0,
                r['status_rekod'], r['sumber_pdm'], r['dicipta_pada']
            )
            for r in batch
        ]
        cursor.executemany(insert_sql, values)
        total_inserted += len(batch)
        print(f'  Dimasukkan {total_inserted}/{len(all_records)} rekod...')
    
    conn.commit()
    
    # Create indexes
    print('Mencipta indeks...')
    cursor.execute('CREATE INDEX idx_pengundi_no_kp ON pengundi(no_kp)')
    cursor.execute('CREATE INDEX idx_pengundi_nama ON pengundi(nama_penuh)')
    cursor.execute('CREATE INDEX idx_pengundi_dm ON pengundi(dm)')
    cursor.execute('CREATE INDEX idx_pengundi_status_rekod ON pengundi(status_rekod)')
    cursor.execute('CREATE INDEX idx_pengundi_status_sokongan ON pengundi(status_sokongan)')
    
    conn.commit()
    conn.close()
    
    print(f'\n✅ MIGRASI SELESAI!')
    print(f'   Pangkalan data: {DB_PATH}')
    print(f'   Jumlah rekod: {total_inserted}')
    
    # Summary stats
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT dm, COUNT(*) FROM pengundi GROUP BY dm ORDER BY dm')
    print(f'\n📊 RINGKASAN MENGIKUT PDM:')
    for row in cursor.fetchall():
        print(f'   {row[0]}: {row[1]} pengundi')
    
    cursor.execute('SELECT status_sokongan, COUNT(*) FROM pengundi GROUP BY status_sokongan')
    print(f'\n📊 RINGKASAN STATUS SOKONGAN:')
    for row in cursor.fetchall():
        print(f'   {row[0] or "Tiada"}: {row[1]}')
    
    cursor.execute('SELECT status_fizikal, COUNT(*) FROM pengundi GROUP BY status_fizikal')
    print(f'\n📊 RINGKASAN STATUS FIZIKAL:')
    for row in cursor.fetchall():
        print(f'   {row[0]}: {row[1]}')
    
    conn.close()


if __name__ == '__main__':
    main()