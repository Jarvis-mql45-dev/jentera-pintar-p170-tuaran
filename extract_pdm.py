import pandas as pd

duns = {
    'N12 SULAMAN': 'DUN N12 SULAMAN/SENARAI PENGUNDI SULAMAN.xlsx',
    'N13 PANTAI DALIT': 'DUN N13 PANTAI DALIT/SENARAI PENGUNDI PANTAI DALIT.xlsx',
    'N14 TAMPARULI': 'DUN N14 TAMPARULI/SENARAI PENGUNDI TAMPARULI.xlsx',
    'N15 KIULU': 'DUN N15 KIULU/SENARAI PENGUNDI KIULU.xlsx'
}

for dun_name, path in duns.items():
    df = pd.read_excel(path)
    pdms = df['DAERAH MENGUNDI'].dropna().unique()
    pdms_sorted = sorted([p.strip().upper() for p in pdms if str(p).strip()])
    print(f'{dun_name} ({len(pdms_sorted)} PDM):')
    for p in pdms_sorted:
        print(f'  "{p}": "{dun_name}",')
    print()