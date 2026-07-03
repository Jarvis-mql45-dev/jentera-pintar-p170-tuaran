import pandas as pd
import os

base = 'DUN N05 MATUNGGUNG'
pdms = ['BINGOLON', 'DUALOG', 'INDARASON', 'KANDAWAYON', 'LAJONG', 'LODUNG']

for pdm in pdms:
    path = os.path.join(base, f'PDM {pdm}', f'PDM {pdm}.xlsx')
    if not os.path.exists(path):
        print(f'{pdm}: FAIL TIDAK WUJUD')
        continue
    xl = pd.ExcelFile(path)
    sheets = xl.sheet_names
    print(f'\n=== {pdm} === (Sheets: {sheets})')
    for s in sheets:
        df = pd.read_excel(path, sheet_name=s, nrows=3)
        print(f'  Sheet: "{s}"')
        print(f'  Columns: {list(df.columns)}')
        for i in range(len(df)):
            print(f'  Row {i}: {list(df.iloc[i].values)}')