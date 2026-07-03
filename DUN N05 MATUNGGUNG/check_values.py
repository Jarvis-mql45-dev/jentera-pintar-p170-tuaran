import pandas as pd
import os

base = 'DUN N05 MATUNGGUNG'

# Check BINGOLON
path = os.path.join(base, 'PDM BINGOLON', 'PDM BINGOLON.xlsx')
df = pd.read_excel(path, sheet_name='PENGUNDI BINGOLON', header=None, skiprows=1)

# Check columns 11 (P), 12 (AP), 13 (H), 14 (TAK KENAL)
for col_idx, name in [(11, 'P'), (12, 'AP'), (13, 'H'), (14, 'TAK KENAL')]:
    vals = df.iloc[:, col_idx]
    non_null = vals.dropna()
    print(f'BINGOLON col {col_idx} ({name}): non-null count={len(non_null)}, unique={non_null.unique()[:20]}')

# Check INDARASON
path2 = os.path.join(base, 'PDM INDARASON', 'PDM INDARASON.xlsx')
df2 = pd.read_excel(path2, sheet_name='PDM INDARASON', header=None, skiprows=1)
for col_idx, name in [(12, 'P'), (13, 'AP'), (14, 'H'), (15, 'TAK KENAL')]:
    vals = df2.iloc[:, col_idx]
    non_null = vals.dropna()
    print(f'INDARASON col {col_idx} ({name}): non-null count={len(non_null)}, unique={non_null.unique()[:20]}')

# Check also column 15 (X DUNIA) for BINGOLON
vals_x = df.iloc[:, 15].dropna()
print(f'BINGOLON col 15 (X DUNIA): non-null count={len(vals_x)}, unique={vals_x.unique()[:20]}')

# Check X DUNIA for INDARASON
vals_x2 = df2.iloc[:, 16].dropna()
print(f'INDARASON col 16 (X DUNIA): non-null count={len(vals_x2)}, unique={vals_x2.unique()[:20]}')