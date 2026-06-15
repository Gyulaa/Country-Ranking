import wbgapi as wb
import pandas as pd
import numpy as np
import os
import time
from datetime import datetime

# =============================================================================
# BEÁLLÍTÁSOK
# =============================================================================
CACHE_FILE     = "geo_list_cache.csv"   # Nyers WB adatok helyi tárolója
FORCE_DOWNLOAD = False                  # True → mindig újra letölt (pl. éves frissítés)

# --- ORSZÁGLISTA (102 Ország) ---
global_powers = [
    # Észak-Amerika és Nyugat-Európa (18)
    'USA', 'CAN', 'GBR', 'FRA', 'DEU', 'ITA', 'ESP', 'NLD', 'BEL', 'CHE', 'SWE', 'DNK', 'NOR', 'FIN', 'IRL', 'PRT', 'AUT', 'ISL',
    # Kelet-Európa, Baltikum és Oroszország (11)
    'RUS', 'UKR', 'BLR', 'POL', 'ROU', 'CZE', 'HUN', 'SVK', 'LTU', 'LVA', 'EST',
    # Balkán (9)
    'GRC', 'SRB', 'BGR', 'HRV', 'SVN', 'BIH', 'ALB', 'MKD', 'MNE',
    # Ázsia és Óceánia (19)
    'CHN', 'JPN', 'IND', 'KOR', 'AUS', 'NZL', 'IDN', 'VNM', 'PHL', 'MYS', 'SGP', 'THA', 'PAK', 'BGD', 'LKA', 'MNG', 'NPL', 'KHM', 'MMR',
    # Közép-Ázsia és Kaukázus (5)
    'KAZ', 'UZB', 'AZE', 'GEO', 'ARM',
    # Közel-Kelet és Észak-Afrika (14)
    'ISR', 'SAU', 'TUR', 'ARE', 'IRN', 'EGY', 'MAR', 'DZA', 'QAT', 'KWT', 'OMN', 'JOR', 'IRQ', 'TUN',
    # Latin-Amerika (15)
    'BRA', 'MEX', 'ARG', 'COL', 'CHL', 'PER', 'VEN', 'ECU', 'DOM', 'GTM', 'URY', 'CRI', 'PAN', 'BOL', 'PRY',
    # Szaharától délre fekvő Afrika (11)
    'NGA', 'ZAF', 'KEN', 'ETH', 'GHA', 'AGO', 'CIV', 'RWA', 'TZA', 'CMR', 'UGA',
]

# --- WDI (db=2) mutatók ---
indicators_db2 = {
    'TX.VAL.TECH.MF.ZS': 'Energy_HighTech',            # Csúcstechnológiai export (az innováció piaci tesztje)
    'GB.XPD.RSDV.GD.ZS': 'Energy_RnD',                 # K+F ráfordítások – Input
    'IP.PAT.RESD':        'Energy_Patents',             # Szabadalmak – Output volumen

    'SI.DST.10TH.10':     'Openness_Top10Income_INV',   # Felső 10% vagyonrészesedése (Inverz: koncentráció = büntetés)
    'HD.HCI.OVRL':        'Openness_HumanCapital',      # Humán Tőke Index (egészség + oktatás)

    'SI.POV.GINI':        'Cohesion_Gini_INV',          # Gini-index (Inverz)
    'VC.IHR.PSRC.P5':     'Cohesion_Homicide_INV',      # Gyilkossági ráta (Inverz)

    'SP.DYN.TFRT.IN':     'Demography_Fertility',       # Termékenységi ráta

    'SP.POP.TOTL':        'Hard_Population',            # Teljes népesség
    'NY.GDP.MKTP.CD':     'Hard_GDP_USD',               # GDP (folyó USD)
    'MS.MIL.XPND.GD.ZS': 'Hard_Military_Pct',          # Katonai kiadások (GDP %)
    'ER.H2O.INTR.K3':     'Geo_Freshwater',             # Megújuló édesvízkészlet
    'AG.LND.ARBL.HA':     'Geo_ArableLand',             # Szántóterület
    'EG.IMP.CONS.ZS':     'Hard_EnergyVulnerability_INV', # Nettó energiaimport (Inverz)
}

# --- WGI (db=3) mutatók ---
indicators_db3 = {
    'RQ.EST': 'Openness_RegQuality',       # Szabályozási Minőség – intézményi környezet tisztasága
    'GE.EST': 'Cohesion_GovEffectiveness', # Kormányzati Hatékonyság
}

all_indicator_cols = list(indicators_db2.values()) + list(indicators_db3.values())

# =============================================================================
# ADATLETÖLTŐ FÜGGVÉNY
# =============================================================================
def fetch_all_indicators():
    """Letölti az összes mutatót a Világbanktól. Eredmény: nyers DataFrame."""
    df_raw = pd.DataFrame(index=global_powers)
    chunks  = [global_powers[i:i+15] for i in range(0, len(global_powers), 15)]

    def _fetch_dict(ind_dict, db_id):
        for ind_code, col_name in ind_dict.items():
            print(f"  (db={db_id}) {col_name}...", end=" ", flush=True)
            try:
                series = pd.Series(dtype=float)
                for chunk in chunks:
                    for attempt in range(3):
                        try:
                            # mrv=10: 10 éves visszatekintés – kiküszöböli a ritka mérések hiányát
                            temp = wb.data.DataFrame(ind_code, chunk, mrv=10, db=db_id)
                            if temp is not None and not temp.empty:
                                series = pd.concat([series, temp.ffill(axis=1).iloc[:, -1]])
                            break
                        except Exception:
                            if attempt < 2:
                                time.sleep(2)
                            else:
                                print("[blokk hiba]", end=" ")
                    time.sleep(1)
                df_raw[col_name] = series
                print("OK")
            except Exception as e:
                print(f"HIBA: {e}")
                df_raw[col_name] = np.nan

    _fetch_dict(indicators_db2, db_id=2)
    _fetch_dict(indicators_db3, db_id=3)
    return df_raw

# =============================================================================
# CACHE KEZELÉS
# =============================================================================
def _cache_is_valid():
    """Ellenőrzi, hogy a cache létezik és tartalmazza az összes szükséges oszlopot."""
    if not os.path.exists(CACHE_FILE):
        return False
    try:
        cached = pd.read_csv(CACHE_FILE, index_col=0, nrows=0)  # csak a fejléc
        missing = [c for c in all_indicator_cols if c not in cached.columns]
        if missing:
            print(f"Cache hiányos (hiányzó mutatók: {missing}), újra letöltöm...")
            return False
        return True
    except Exception:
        return False

if not FORCE_DOWNLOAD and _cache_is_valid():
    age_days = (datetime.now() - datetime.fromtimestamp(os.path.getmtime(CACHE_FILE))).days
    print(f"Cache betöltése ({age_days} napos) → {CACHE_FILE}")
    print("(Friss letöltéshez állítsd: FORCE_DOWNLOAD = True)")
    df = pd.read_csv(CACHE_FILE, index_col=0)
    # Biztosítjuk, hogy csak az ismert országok szerepelnek
    df = df.reindex(global_powers)
else:
    reason = "FORCE_DOWNLOAD=True" if FORCE_DOWNLOAD else "Cache nem található"
    print(f"Adatok letöltése ({reason}) – {len(global_powers)} ország, ~3-5 perc...")
    df = fetch_all_indicators()
    df.to_csv(CACHE_FILE)
    print(f"Cache elmentve: {CACHE_FILE}")

# =============================================================================
# 3. ELŐKÉSZÍTÉS ÉS LOGARITMIZÁLÁS
# =============================================================================
# Ahol a hiány valódi nulla értéket jelent (nem mérte = nem is költ rá)
strict_cols = ['Energy_RnD', 'Energy_Patents', 'Energy_HighTech', 'Hard_Military_Pct', 'Hard_EnergyVulnerability_INV']
for col in strict_cols:
    if col in df.columns:
        df[col] = df[col].fillna(0)

# A maradék mutatókat mediánnal töltjük – robusztusabb az átlagnál, outlierekre kevésbé érzékeny
df = df.fillna(df.median(numeric_only=True))

# Inverz mutatók megfordítása (magasabb = jobb logika fenntartásához)
for col in df.columns:
    if '_INV' in col:
        df[col] = df[col] * -1

# Szabadalmak: lakosságra vetítve, majd logaritmizálva (nagy népességű országok torzítása ellen)
df['Energy_Patents_PerCapita'] = df['Energy_Patents'] / df['Hard_Population'].replace(0, 1)
df['Energy_Patents_Log'] = np.log10(df['Energy_Patents_PerCapita'].replace(0, np.nan).fillna(0.0001))

# Aszimmetrikus katonai erő: katonai kiadás × (tech export + K+F) – nem a tankok száma számít
df['Hard_Asym_Power'] = df['Hard_Military_Pct'] * (df['Energy_HighTech'] + df['Energy_RnD'])

# Nyers erő és földrajzi mutatók logaritmizálása (erősen jobbra ferde eloszlások egyenítése)
df['Hard_Pop_Log']        = np.log10(df['Hard_Population'].replace(0, np.nan))
df['Hard_GDP_Log']        = np.log10(df['Hard_GDP_USD'].replace(0, np.nan))
df['Geo_Freshwater_Log']  = np.log10(df['Geo_Freshwater'].replace(0, np.nan).fillna(1))
df['Geo_ArableLand_Log']  = np.log10(df['Geo_ArableLand'].replace(0, np.nan).fillna(1))

calc_columns = [
    'Energy_HighTech', 'Energy_RnD', 'Energy_Patents_Log',
    'Openness_RegQuality', 'Openness_HumanCapital', 'Openness_Top10Income_INV',
    'Cohesion_GovEffectiveness', 'Cohesion_Gini_INV', 'Cohesion_Homicide_INV',
    'Demography_Fertility',
    'Hard_Pop_Log', 'Hard_GDP_Log', 'Hard_Asym_Power',
    'Geo_Freshwater_Log', 'Geo_ArableLand_Log', 'Hard_EnergyVulnerability_INV',
]

df_calc = df[calc_columns].replace([np.inf, -np.inf], np.nan)
df_calc = df_calc.fillna(df_calc.mean()).fillna(0)

# =============================================================================
# 4. Z-SCORE SKÁLÁZÁS (1–10)
# =============================================================================
df_z = (df_calc - df_calc.mean()) / df_calc.std().replace(0, 1)

df_1to10 = pd.DataFrame(index=df.index)
for col in df_z.columns:
    z_clipped = np.clip(df_z[col], -2.5, 2.5)
    df_1to10[col] = 1 + 9 * ((z_clipped - (-2.5)) / 5.0)

# =============================================================================
# 5. DIMENZIÓK ÉS VÉGSŐ INDEX
# =============================================================================
df_results = pd.DataFrame(index=df.index)

# Energia & Innováció: piaci bizonyíték (40%) + tudományos output (30%) + K+F input (30%)
df_results['Dim_Energy'] = (
    (df_1to10['Energy_HighTech']    * 0.40) +
    (df_1to10['Energy_Patents_Log'] * 0.30) +
    (df_1to10['Energy_RnD']         * 0.30)
)

# Nyitottság & Intézményrendszer:
#   Szabályozási Minőség (40%): az intézményi környezet tisztasága – angolszász bias-mentes
#   Humán Tőke Index (30%): jövőbeli esélyegyenlőség és egészségügy/oktatás minősége
#   Elit vagyonkoncentráció, Inverz (30%): a felső 10% kisajátítási mértékének büntetése
df_results['Dim_Openness'] = (
    (df_1to10['Openness_RegQuality']       * 0.40) +
    (df_1to10['Openness_HumanCapital']     * 0.30) +
    (df_1to10['Openness_Top10Income_INV']  * 0.30)
)

# Kohézió & Stabilitás: kormányzati hatékonyság (40%) + egyenlőség (30%) + fizikai biztonság (30%)
df_results['Dim_Cohesion'] = (
    (df_1to10['Cohesion_GovEffectiveness'] * 0.40) +
    (df_1to10['Cohesion_Gini_INV']         * 0.30) +
    (df_1to10['Cohesion_Homicide_INV']     * 0.30)
)

# Demográfia: termékenységi ráta (biológiai jövő – egy kihaló társadalom kiesik a formálók közül)
df_results['Dim_Demography'] = df_1to10['Demography_Fertility']

# Belső Vitalitás (OSCI) – geometriai átlag: egyetlen gyenge pillér az egész pontszámot lerántja
df_results['Score_OSCI'] = (
    df_results['Dim_Energy']   *
    df_results['Dim_Openness'] *
    df_results['Dim_Cohesion'] *
    df_results['Dim_Demography']
) ** 0.25

# Hard Power alkatrészek
df_results['HP_Pop']            = df_1to10['Hard_Pop_Log']
df_results['HP_GDP']            = df_1to10['Hard_GDP_Log']
df_results['HP_Military_Asym']  = df_1to10['Hard_Asym_Power']
df_results['HP_Geo']            = df_1to10[['Geo_Freshwater_Log', 'Geo_ArableLand_Log']].mean(axis=1)
df_results['HP_EnergySecurity'] = df_1to10['Hard_EnergyVulnerability_INV']

df_results['Score_HardPower'] = (
    df_results['HP_GDP']            * 0.25 +
    df_results['HP_Military_Asym']  * 0.25 +
    df_results['HP_Pop']            * 0.20 +
    df_results['HP_Geo']            * 0.20 +
    df_results['HP_EnergySecurity'] * 0.10
)

# VÉGSŐ SÚLYOZÁS: OSCI 60% – Hard Power 40%
df_results['FINAL_SCORE_1_10'] = (df_results['Score_OSCI'] * 0.60) + (df_results['Score_HardPower'] * 0.40)

# =============================================================================
# 6. EXPORTÁLÁS
# =============================================================================
final_columns = [
    'Dim_Energy', 'Dim_Openness', 'Dim_Cohesion', 'Dim_Demography', 'Score_OSCI',
    'HP_Pop', 'HP_GDP', 'HP_Military_Asym', 'HP_Geo', 'HP_EnergySecurity',
    'Score_HardPower', 'FINAL_SCORE_1_10',
]
df_final = df_results[final_columns].sort_values(by='FINAL_SCORE_1_10', ascending=False).round(2)

current_time     = datetime.now().strftime("%Y%m%d_%H%M")
output_filename  = f"Geopolitical_Ranking_Optimalized_{current_time}.xlsx"
df_final.to_excel(output_filename)

print(f"\nKész! {len(global_powers)} ország, eredmény mentve: {output_filename}")
print("\n--- TOP 15 ORSZÁG ---")
print(df_final[['Score_OSCI', 'Score_HardPower', 'FINAL_SCORE_1_10']].head(15))
