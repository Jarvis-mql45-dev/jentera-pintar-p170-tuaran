import pandas as pd
import os

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 400)
pd.set_option('display.max_colwidth', 30)

# Mapping PDM -> sheet name for data (not Dashboard)
pdm_sheet_map = {
    'BINGOLON': 'PENGUNDI BINGOLON',
    'DUALOG': 'PDM DUALOG',
    'INDARASON': 'PDM INDARASON',
    'KANDAWAYON': 'PDM Kandawayon',
    'LAJONG': 'PDM LAJONG',
    'LODUNG': 'PDM LODUNG'
}

base = 'DUN N05 MATUNGGUNG'

for pdm, sheet_name in pdm_sheet_map.items():
    path = os.path.join(base, f'PDM {pdm}', f'PDM {pdm}.xlsx')
    print(f'\n{"="*60}')
    print(f'=== {pdm} === Sheet: "{sheet_name}"')
    print(f'{"="*60}')
    
    # Baca header row (row 0)
    df_header = pd.read_excel(path, sheet_name=sheet_name, header=None, nrows=2)
    headers = list(df_header.iloc[0].values)
    print(f'Headers (row 0): {headers}')
    print(f'Number of columns: {len(headers)}')
    
    # Baca 3 baris data (skip header)
    df_data = pd.read_excel(path, sheet_name=sheet_name, header=None, skiprows=1, nrows=3)
    for i in range(len(df_data)):
        print(f'Data row {i}: {list(df_data.iloc[i].values)}')