"""Verify Excel data before import"""
import pandas as pd

f = "DUN N05 MATUNGGUNG/DASHBOARD N05 MATUNGGUNG.xlsx"
df = pd.read_excel(f)
print(f"Total rows: {len(df)}")
print(f"Columns: {list(df.columns)}")

dm_col = [c for c in df.columns if c.strip().upper() in ["DM", "DUN", "DAERAH", "LOKASI"]]
if dm_col:
    dm_vals = df[dm_col[0]].dropna().unique()
    pdm = [d for d in dm_vals if str(d).strip().upper().startswith("PDM ")]
    print(f"DM unique values ({len(dm_vals)}): {list(dm_vals)[:20]}")
    print(f"PDM prefix found: {len(pdm)}")
    if pdm:
        print(f"PDM values: {pdm}")
    else:
        print("✅ No PDM data in Excel!")
else:
    print(f"DM column not found, checking first few values of each column...")
    for c in df.columns[:10]:
        print(f"  {c}: {df[c].dropna().unique()[:5]}")