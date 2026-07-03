import pandas as pd
import os

base = 'DUN N05 MATUNGGUNG'
pdms = ['BINGOLON', 'DUALOG', 'INDARASON', 'KANDAWAYON', 'LAJONG', 'LODUNG']

for pdm in pdms:
    path = os.path.join(base, f'PDM {pdm}', f'PDM {pdm}.xlsx')
    xl = pd.ExcelFile(path)
    print(f'{pdm}: {xl.sheet_names}')