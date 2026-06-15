"""
historical_geo_list.py
======================
Historikus geopolitikai pontszámok számítása 2005–2024-re.
AZONOS logika mint geo_list.py – az eredmények összehasonlíthatók
az aktuális éves dashboard-dal.

Cache: historical_raw_cache.csv  (nyers WB adatok, csak egyszer kell letölteni)
Output: historical_scores_optimalized.xlsx  (éves pontszámok, 7 sheet)

Futtatás: python historical_geo_list.py
  Első futás:  ~20–30 perc (letöltés)
  Második futás: ~1 perc (cache-ből)
"""

import wbgapi as wb
import pandas as pd
import numpy as np
import os
import time
from datetime import datetime

# =============================================================================
# BEÁLLÍTÁSOK
# =============================================================================
RAW_CACHE_FILE = "historical_raw_cache.csv"
SCORES_FILE    = "historical_scores_optimalized.xlsx"
FORCE_DOWNLOAD = False   # True -> mindent újra letölt
START_YEAR     = 2005
END_YEAR       = 2024
FETCH_FROM     = 2000    # korábbi évek a forward-fill ablakhoz

# =============================================================================
# UGYANAZ MINT GEO_LIST.PY
# =============================================================================
global_powers = [
    'USA','CAN','GBR','FRA','DEU','ITA','ESP','NLD','BEL','CHE','SWE','DNK','NOR','FIN','IRL','PRT','AUT','ISL',
    'RUS','UKR','BLR','POL','ROU','CZE','HUN','SVK','LTU','LVA','EST',
    'GRC','SRB','BGR','HRV','SVN','BIH','ALB','MKD','MNE',
    'CHN','JPN','IND','KOR','AUS','NZL','IDN','VNM','PHL','MYS','SGP','THA','PAK','BGD','LKA','MNG','NPL','KHM','MMR',
    'KAZ','UZB','AZE','GEO','ARM',
    'ISR','SAU','TUR','ARE','IRN','EGY','MAR','DZA','QAT','KWT','OMN','JOR','IRQ','TUN',
    'BRA','MEX','ARG','COL','CHL','PER','VEN','ECU','DOM','GTM','URY','CRI','PAN','BOL','PRY',
    'NGA','ZAF','KEN','ETH','GHA','AGO','CIV','RWA','TZA','CMR','UGA',
]

indicators_db2 = {
    'TX.VAL.TECH.MF.ZS': 'Energy_HighTech',
    'GB.XPD.RSDV.GD.ZS': 'Energy_RnD',
    'IP.PAT.RESD':        'Energy_Patents',
    'SI.DST.10TH.10':     'Openness_Top10Income_INV',
    'HD.HCI.OVRL':        'Openness_HumanCapital',
    'SI.POV.GINI':        'Cohesion_Gini_INV',
    'VC.IHR.PSRC.P5':     'Cohesion_Homicide_INV',
    'SP.DYN.TFRT.IN':     'Demography_Fertility',
    'SP.POP.TOTL':        'Hard_Population',
    'NY.GDP.MKTP.CD':     'Hard_GDP_USD',
    'MS.MIL.XPND.GD.ZS': 'Hard_Military_Pct',
    'ER.H2O.INTR.K3':     'Geo_Freshwater',
    'AG.LND.ARBL.HA':     'Geo_ArableLand',
    'EG.IMP.CONS.ZS':     'Hard_EnergyVulnerability_INV',
}
indicators_db3 = {
    'RQ.EST': 'Openness_RegQuality',
    'GE.EST': 'Cohesion_GovEffectiveness',
}
all_indicator_cols = list(indicators_db2.values()) + list(indicators_db3.values())
strict_cols = ['Energy_RnD','Energy_Patents','Energy_HighTech','Hard_Military_Pct','Hard_EnergyVulnerability_INV']

score_cols = ['Dim_Energy','Dim_Openness','Dim_Cohesion','Dim_Demography',
              'Score_OSCI','Score_HardPower','FINAL_SCORE_1_10']

# =============================================================================
# SCORE SZÁMÍTÁS – PONTOSAN UGYANAZ MINT GEO_LIST.PY
# =============================================================================
def compute_scores(df_raw):
    """Kap egy (ország × mutató) DataFrame-et, visszaad pontszámokat."""
    df = df_raw[all_indicator_cols].copy().astype(float)

    for col in strict_cols:
        if col in df.columns:
            df[col] = df[col].fillna(0)
    df = df.fillna(df.median(numeric_only=True))

    for col in df.columns:
        if '_INV' in col:
            df[col] = df[col] * -1

    df['Energy_Patents_PerCapita'] = df['Energy_Patents'] / df['Hard_Population'].replace(0, 1)
    df['Energy_Patents_Log'] = np.log10(df['Energy_Patents_PerCapita'].replace(0, np.nan).fillna(0.0001))
    df['Hard_Asym_Power']    = df['Hard_Military_Pct'] * (df['Energy_HighTech'] + df['Energy_RnD'])
    df['Hard_Pop_Log']       = np.log10(df['Hard_Population'].replace(0, np.nan))
    df['Hard_GDP_Log']       = np.log10(df['Hard_GDP_USD'].replace(0, np.nan))
    df['Geo_Freshwater_Log'] = np.log10(df['Geo_Freshwater'].replace(0, np.nan).fillna(1))
    df['Geo_ArableLand_Log'] = np.log10(df['Geo_ArableLand'].replace(0, np.nan).fillna(1))

    calc_cols = [
        'Energy_HighTech','Energy_RnD','Energy_Patents_Log',
        'Openness_RegQuality','Openness_HumanCapital','Openness_Top10Income_INV',
        'Cohesion_GovEffectiveness','Cohesion_Gini_INV','Cohesion_Homicide_INV',
        'Demography_Fertility',
        'Hard_Pop_Log','Hard_GDP_Log','Hard_Asym_Power',
        'Geo_Freshwater_Log','Geo_ArableLand_Log','Hard_EnergyVulnerability_INV',
    ]
    df_c = df[calc_cols].replace([np.inf, -np.inf], np.nan)
    df_c = df_c.fillna(df_c.mean()).fillna(0)

    df_z = (df_c - df_c.mean()) / df_c.std().replace(0, 1)
    df_1 = pd.DataFrame(index=df.index)
    for col in df_z.columns:
        zc = np.clip(df_z[col], -2.5, 2.5)
        df_1[col] = 1 + 9 * ((zc - (-2.5)) / 5.0)

    res = pd.DataFrame(index=df.index)
    res['Dim_Energy']     = df_1['Energy_HighTech']*0.40 + df_1['Energy_Patents_Log']*0.30 + df_1['Energy_RnD']*0.30
    res['Dim_Openness']   = df_1['Openness_RegQuality']*0.40 + df_1['Openness_HumanCapital']*0.30 + df_1['Openness_Top10Income_INV']*0.30
    res['Dim_Cohesion']   = df_1['Cohesion_GovEffectiveness']*0.40 + df_1['Cohesion_Gini_INV']*0.30 + df_1['Cohesion_Homicide_INV']*0.30
    res['Dim_Demography'] = df_1['Demography_Fertility']
    res['Score_OSCI'] = (res['Dim_Energy'] * res['Dim_Openness'] * res['Dim_Cohesion'] * res['Dim_Demography']) ** 0.25
    hp_geo = df_1[['Geo_Freshwater_Log','Geo_ArableLand_Log']].mean(axis=1)
    res['Score_HardPower'] = (
        df_1['Hard_GDP_Log']    * 0.25 +
        df_1['Hard_Asym_Power'] * 0.25 +
        df_1['Hard_Pop_Log']    * 0.20 +
        hp_geo                   * 0.20 +
        df_1['Hard_EnergyVulnerability_INV'] * 0.10
    )
    res['FINAL_SCORE_1_10'] = res['Score_OSCI'] * 0.60 + res['Score_HardPower'] * 0.40
    return res[score_cols]

# =============================================================================
# CACHE ELLENŐRZÉS
# =============================================================================
def _cache_valid():
    if not os.path.exists(RAW_CACHE_FILE):
        return False
    try:
        header = pd.read_csv(RAW_CACHE_FILE, nrows=0)
        needed = ['country','year'] + all_indicator_cols
        missing = [x for x in needed if x not in header.columns]
        if missing:
            print(f"Cache hiányos ({missing}), újra letöltöm...")
            return False
        return True
    except Exception:
        return False

# =============================================================================
# LETÖLTÉS VAGY CACHE BETÖLTÉS
# =============================================================================
if not FORCE_DOWNLOAD and _cache_valid():
    age = (datetime.now() - datetime.fromtimestamp(os.path.getmtime(RAW_CACHE_FILE))).days
    print(f"Historikus cache betöltése ({age} napos) -> {RAW_CACHE_FILE}")
    raw_df = pd.read_csv(RAW_CACHE_FILE)
else:
    reason = "FORCE_DOWNLOAD=True" if FORCE_DOWNLOAD else "cache nem található"
    print(f"Historikus letöltés ({reason}): {FETCH_FROM}–{END_YEAR}, {len(global_powers)} ország × {len(all_indicator_cols)} mutató")
    print("Ez 20–30 percet vehet igénybe (egyszer fut le, utána cache-ből tölt).")

    years     = list(range(FETCH_FROM, END_YEAR + 1))
    yr_cols   = [f'YR{y}' for y in years]
    chunks    = [global_powers[i:i+15] for i in range(0, len(global_powers), 15)]
    series    = {}  # {col_name: DataFrame(countries × yr_cols), forward-filled}

    def _download(ind_code, col_name, db_id):
        print(f"  (db={db_id}) {col_name}...", end=" ", flush=True)
        combined = pd.DataFrame(np.nan, index=global_powers, columns=yr_cols, dtype=float)
        for chunk in chunks:
            for attempt in range(3):
                try:
                    tmp = wb.data.DataFrame(ind_code, chunk, time=years, db=db_id)
                    if tmp is not None and not tmp.empty:
                        valid = [c for c in tmp.columns if c in yr_cols]
                        for iso in chunk:
                            if iso in tmp.index:
                                combined.loc[iso, valid] = tmp.loc[iso, valid].values
                    break
                except Exception:
                    if attempt < 2:
                        time.sleep(3)
                    else:
                        print("[hiba]", end=" ")
            time.sleep(0.8)
        # Forward-fill hiányos éveket (ha 2018 hiányzik, 2017-et örökli)
        combined = combined.ffill(axis=1)
        series[col_name] = combined
        print("OK")

    for code, name in indicators_db2.items():
        _download(code, name, 2)
    for code, name in indicators_db3.items():
        _download(code, name, 3)

    # Long-format cache összeállítása
    records = []
    for country in global_powers:
        for i, year in enumerate(years):
            yc = yr_cols[i]
            row = {'country': country, 'year': year}
            for col_name in all_indicator_cols:
                row[col_name] = series[col_name].loc[country, yc] if col_name in series else np.nan
            records.append(row)
    raw_df = pd.DataFrame(records)
    raw_df.to_csv(RAW_CACHE_FILE, index=False)
    print(f"Cache mentve: {RAW_CACHE_FILE}")

# =============================================================================
# ÉVES PONTSZÁMOK SZÁMÍTÁSA
# =============================================================================
print(f"\nPontszámok számítása {START_YEAR}–{END_YEAR}...")

yearly_scores = {}  # {year: DataFrame(countries × score_cols)}

for year in range(START_YEAR, END_YEAR + 1):
    slice_df = raw_df[raw_df['year'] == year].copy()
    slice_df = slice_df.set_index('country')[all_indicator_cols].reindex(global_powers)
    scores = compute_scores(slice_df)
    yearly_scores[year] = scores.round(4)

    top3 = scores['FINAL_SCORE_1_10'].sort_values(ascending=False).head(3)
    print(f"  {year}: {', '.join(f'{c}={v:.2f}' for c,v in top3.items())}")

# =============================================================================
# MENTÉS EXCEL-BE (7 sheet, 1 sheet/mutató)
# =============================================================================
print(f"\nMentés: {SCORES_FILE}")
with pd.ExcelWriter(SCORES_FILE, engine='openpyxl') as writer:
    for col in score_cols:
        sheet_df = pd.DataFrame(
            {year: yearly_scores[year][col] for year in range(START_YEAR, END_YEAR + 1)},
            index=global_powers
        )
        sheet_df.index.name = 'country'
        # Excel sheet névkorlát: 31 karakter
        sheet_df.to_excel(writer, sheet_name=col[:31])

print(f"Kesz! -> {SCORES_FILE}")
print("Következő lépés: python dashboard.py  (bekerül az index.html-be)")
