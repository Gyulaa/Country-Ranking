import wbgapi as wb
import pandas as pd
import numpy as np
import time
from datetime import datetime  # ÚJ: Időbélyeghez szükséges modul

# --- 1. BEÁLLÍTÁSOK ÉS BŐVÍTETT ORSZÁGLISTA (85 Ország) ---
global_powers = [
    'USA', 'CAN', 'GBR', 'FRA', 'DEU', 'ITA', 'ESP', 'NLD', 'BEL', 'CHE', 'SWE', 'DNK', 'NOR', 'FIN', 'IRL', 'PRT', 'AUT',
    'RUS', 'UKR', 'POL', 'ROU', 'CZE', 'HUN', 'GRC', 'SRB', 'BGR', 'HRV', 'SVK', 'LTU',
    'CHN', 'JPN', 'IND', 'KOR', 'AUS', 'NZL', 'IDN', 'VNM', 'PHL', 'MYS', 'SGP', 'THA', 'PAK', 'BGD', 'LKA', 'KAZ', 'UZB',
    'ISR', 'SAU', 'TUR', 'ARE', 'IRN', 'EGY', 'MAR', 'DZA', 'QAT', 'KWT', 'OMN', 'JOR', 'IRQ',
    'BRA', 'MEX', 'ARG', 'COL', 'CHL', 'PER', 'VEN', 'ECU', 'DOM', 'GTM',
    'NGA', 'ZAF', 'KEN', 'ETH', 'GHA', 'AGO', 'CIV'
]

indicators = {
    # Energia és Vitalitás
    'GB.XPD.RSDV.GD.ZS': 'Energy_RnD',           
    'SL.UEM.1524.ZS': 'Energy_YouthUnemp_INV',   
    'IP.PAT.RESD': 'Energy_Patents',             
    
    # Nyitottság
    'IC.REG.DURS': 'Openness_Bureaucracy_INV',   
    'SL.UEM.TERT.ZS': 'Openness_TertiaryUnemp_INV', 
    'SI.DST.10TH.10': 'Openness_Top10Income_INV',   
    
    # Kohézió
    'SI.POV.GINI': 'Cohesion_Gini_INV',          
    'VC.IHR.PSRC.P5': 'Cohesion_Homicide_INV',   
    
    # Demográfia
    'SP.DYN.TFRT.IN': 'Demography_Fertility',    
    
    # Nyers Erő és Földrajz
    'SP.POP.TOTL': 'Hard_Population',            
    'NY.GDP.MKTP.CD': 'Hard_GDP_USD',            
    'MS.MIL.XPND.GD.ZS': 'Hard_Military_Pct',
    'ER.H2O.INTR.K3': 'Geo_Freshwater',          
    'AG.LND.ARBL.HA': 'Geo_ArableLand',
    
    # Energiafüggőség
    'TM.VAL.FUEL.ZS.UN': 'Hard_EnergyVulnerability_INV'
}

print(f"Adatok biztonságos letöltése {len(global_powers)} országhoz (Hibatűrő mód)...")
df = pd.DataFrame(index=global_powers)

# --- 2. GOLYÓÁLLÓ ADATLETÖLTÉS (CHUNKING + RETRY) ---
chunk_size = 15
country_chunks = [global_powers[i:i + chunk_size] for i in range(0, len(global_powers), chunk_size)]

for ind_code, col_name in indicators.items():
    print(f"Lekérdezés: {col_name}...", end=" ", flush=True)
    try:
        series_data = pd.Series(dtype=float)
        for chunk in country_chunks:
            success = False
            max_retries = 3 
            
            for attempt in range(max_retries):
                try:
                    temp = wb.data.DataFrame(ind_code, chunk, mrv=5)
                    if temp is not None and not temp.empty:
                        last_vals = temp.ffill(axis=1).iloc[:, -1]
                        series_data = pd.concat([series_data, last_vals])
                    success = True
                    break 
                except Exception:
                    if attempt < max_retries - 1:
                        time.sleep(2) 
                    else:
                        print(f"[Blokk hiba]", end=" ")
            
            time.sleep(1) 
            
        df[col_name] = series_data
        print("OK")
    except Exception as e:
        print(f"HIBA: {e}")
        df[col_name] = np.nan

# --- 3. ELŐKÉSZÍTÉS ÉS LOGARITMIZÁLÁS ---
strict_cols = ['Energy_RnD', 'Energy_Patents', 'Hard_Military_Pct', 'Hard_EnergyVulnerability_INV']
for col in strict_cols:
    if col in df.columns:
        df[col] = df[col].fillna(0)

# A maradék társadalmi mutatót átlaggal töltjük
df = df.fillna(df.mean())

for col in df.columns:
    if '_INV' in col:
        df[col] = df[col] * -1

df['Energy_Patents_PerCapita'] = df['Energy_Patents'] / df['Hard_Population'].replace(0, 1)
df['Energy_Patents_Log'] = np.log10(df['Energy_Patents_PerCapita'].replace(0, np.nan).fillna(0.0001))

df['Hard_Asym_Power'] = df['Hard_Military_Pct'] * df['Energy_RnD']

df['Hard_Pop_Log'] = np.log10(df['Hard_Population'].replace(0, np.nan))
df['Hard_GDP_Log'] = np.log10(df['Hard_GDP_USD'].replace(0, np.nan))
df['Geo_Freshwater_Log'] = np.log10(df['Geo_Freshwater'].replace(0, np.nan))
df['Geo_ArableLand_Log'] = np.log10(df['Geo_ArableLand'].replace(0, np.nan))

calc_columns = [
    'Energy_RnD', 'Energy_YouthUnemp_INV', 'Energy_Patents_Log',
    'Openness_Bureaucracy_INV', 'Openness_TertiaryUnemp_INV', 'Openness_Top10Income_INV',
    'Cohesion_Gini_INV', 'Cohesion_Homicide_INV',
    'Demography_Fertility',
    'Hard_Pop_Log', 'Hard_GDP_Log', 'Hard_Asym_Power', 'Geo_Freshwater_Log', 'Geo_ArableLand_Log', 'Hard_EnergyVulnerability_INV'
]

df_calc = df[calc_columns].fillna(df[calc_columns].mean())

# --- 4. Z-SCORE SKÁLÁZÁS (1-10) ---
df_z = (df_calc - df_calc.mean()) / df_calc.std()

df_1to10 = pd.DataFrame(index=df.index)
for col in df_z.columns:
    z_clipped = np.clip(df_z[col], -2.5, 2.5) 
    df_1to10[col] = 1 + 9 * ((z_clipped - (-2.5)) / 5.0)

# --- 5. DIMENZIÓK ÉS VÉGSŐ INDEX KISZÁMÍTÁSA ---
df_results = pd.DataFrame(index=df.index)

df_results['Dim_Energy'] = (df_1to10['Energy_Patents_Log'] * 0.50) + (df_1to10['Energy_RnD'] * 0.30) + (df_1to10['Energy_YouthUnemp_INV'] * 0.20)
df_results['Dim_Openness'] = df_1to10[['Openness_Bureaucracy_INV', 'Openness_TertiaryUnemp_INV', 'Openness_Top10Income_INV']].mean(axis=1)
df_results['Dim_Cohesion'] = df_1to10[['Cohesion_Gini_INV', 'Cohesion_Homicide_INV']].mean(axis=1)
df_results['Dim_Demography'] = df_1to10['Demography_Fertility'] 

df_results['Score_OSCI'] = (
    df_results['Dim_Energy'] * df_results['Dim_Openness'] * df_results['Dim_Cohesion'] * df_results['Dim_Demography']
) ** 0.25

df_results['HP_Pop'] = df_1to10['Hard_Pop_Log']
df_results['HP_GDP'] = df_1to10['Hard_GDP_Log']
df_results['HP_Military_Asym'] = df_1to10['Hard_Asym_Power']
df_results['HP_Geo'] = df_1to10[['Geo_Freshwater_Log', 'Geo_ArableLand_Log']].mean(axis=1)
df_results['HP_EnergySecurity'] = df_1to10['Hard_EnergyVulnerability_INV']

df_results['Score_HardPower'] = (
    df_results['HP_GDP'] * 0.25 + 
    df_results['HP_Military_Asym'] * 0.25 + 
    df_results['HP_Pop'] * 0.20 + 
    df_results['HP_Geo'] * 0.20 +
    df_results['HP_EnergySecurity'] * 0.10
)

# VÉGSŐ SÚLYOZÁS: OSCI 65% - Hard Power 35%
df_results['FINAL_SCORE_1_10'] = (df_results['Score_OSCI'] * 0.65) + (df_results['Score_HardPower'] * 0.35)

# --- 6. EXPORTÁLÁS DINAMIKUS FÁJLNÉVVEL ---
final_columns = [
    'Dim_Energy', 'Dim_Openness', 'Dim_Cohesion', 'Dim_Demography', 'Score_OSCI', 
    'HP_Pop', 'HP_GDP', 'HP_Military_Asym', 'HP_Geo', 'HP_EnergySecurity', 'Score_HardPower', 'FINAL_SCORE_1_10'
]
df_final = df_results[final_columns].sort_values(by='FINAL_SCORE_1_10', ascending=False).round(2)

# ÚJ: Aktuális dátum és idő lekérése (ÉvHónapNap_ÓraPerc formátumban)
current_time = datetime.now().strftime("%Y%m%d_%H%M")
output_filename = f"Geopolitical_Ranking_{current_time}.xlsx"

df_final.to_excel(output_filename)

print(f"\nKész! A végső 65/35 súlyozás alkalmazva. Mátrix mentve: {output_filename}")
print("\n--- TOP 15 ORSZÁG ---")
print(df_final[['Score_OSCI', 'Score_HardPower', 'FINAL_SCORE_1_10']].head(15))