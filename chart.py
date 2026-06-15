import wbgapi as wb
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import time

# --- 1. A TELJES 102 ORSZÁGOS LISTA ---
global_powers = [
    'USA', 'CAN', 'GBR', 'FRA', 'DEU', 'ITA', 'ESP', 'NLD', 'BEL', 'CHE', 'SWE', 'DNK', 'NOR', 'FIN', 'IRL', 'PRT', 'AUT', 'ISL',
    'RUS', 'UKR', 'BLR', 'POL', 'ROU', 'CZE', 'HUN', 'SVK', 'LTU', 'LVA', 'EST',
    'GRC', 'SRB', 'BGR', 'HRV', 'SVN', 'BIH', 'ALB', 'MKD', 'MNE',
    'CHN', 'JPN', 'IND', 'KOR', 'AUS', 'NZL', 'IDN', 'VNM', 'PHL', 'MYS', 'SGP', 'THA', 'PAK', 'BGD', 'LKA', 'MNG', 'NPL', 'KHM', 'MMR',
    'KAZ', 'UZB', 'AZE', 'GEO', 'ARM',
    'ISR', 'SAU', 'TUR', 'ARE', 'IRN', 'EGY', 'MAR', 'DZA', 'QAT', 'KWT', 'OMN', 'JOR', 'IRQ', 'TUN',
    'BRA', 'MEX', 'ARG', 'COL', 'CHL', 'PER', 'VEN', 'ECU', 'DOM', 'GTM', 'URY', 'CRI', 'PAN', 'BOL', 'PRY',
    'NGA', 'ZAF', 'KEN', 'ETH', 'GHA', 'AGO', 'CIV', 'RWA', 'TZA', 'CMR', 'UGA'
]

# Csak ezeket rajzoljuk ki
countries_to_plot = ['IND', 'USA', 'RUS', 'DEU', 'GBR', 'ISR', 'CHN', 'FRA', 'KAZ', 'NLD', 'JPN', 'CAN', 'SWE', 'POL', 'KOR']

indicators = {
    'GB.XPD.RSDV.GD.ZS': 'Energy_RnD',           
    'SL.UEM.1524.ZS': 'Energy_YouthUnemp_INV',   
    'IP.PAT.RESD': 'Energy_Patents',             
    'IC.REG.DURS': 'Openness_Bureaucracy_INV',   
    'SL.UEM.TERT.ZS': 'Openness_TertiaryUnemp_INV', 
    'SI.DST.10TH.10': 'Openness_Top10Income_INV',   
    'SI.POV.GINI': 'Cohesion_Gini_INV',          
    'VC.IHR.PSRC.P5': 'Cohesion_Homicide_INV',   
    'SP.DYN.TFRT.IN': 'Demography_Fertility',    
    'SP.POP.TOTL': 'Hard_Population',            
    'NY.GDP.MKTP.CD': 'Hard_GDP_USD',            
    'MS.MIL.XPND.GD.ZS': 'Hard_Military_Pct',
    'ER.H2O.INTR.K3': 'Geo_Freshwater',          
    'AG.LND.ARBL.HA': 'Geo_ArableLand',
    'TM.VAL.FUEL.ZS.UN': 'Hard_EnergyVulnerability_INV'
}

# 1990-től kérjük le, hogy legyen történelmi "lendület" a hiányzó adatok pótlására!
fetch_years = range(1990, 2025)
plot_years = range(2000, 2025)
data_dict = {}

print("Évtizedes történelmi adatok letöltése és tisztítása (ez beletelhet 2-3 percbe)...")
chunk_size = 15
country_chunks = [global_powers[i:i + chunk_size] for i in range(0, len(global_powers), chunk_size)]

for ind_code, col_name in indicators.items():
    print(f"Lekérdezés: {col_name}...", end=" ", flush=True)
    try:
        # Üres DataFrame a teljes időtávra
        series_data_df = pd.DataFrame(index=global_powers, columns=[f'YR{y}' for y in fetch_years])
        
        for chunk in country_chunks:
            success = False
            for attempt in range(3):
                try:
                    temp = wb.data.DataFrame(ind_code, chunk, time=fetch_years)
                    if temp is not None and not temp.empty:
                        # 1. Biztosítjuk a kronológiai sorrendet!
                        valid_cols = sorted([c for c in temp.columns if c.startswith('YR')])
                        temp = temp[valid_cols]
                        
                        # 2. A MÁGIA: Előrefelé másoljuk a valós adatokat az időben!
                        temp = temp.ffill(axis=1).bfill(axis=1)
                        
                        # Frissítjük a fő táblát
                        series_data_df.update(temp)
                    success = True
                    break
                except Exception:
                    time.sleep(2)
                    
            if not success:
                print(f"[Blokk hiba]", end=" ")
            time.sleep(1)
            
        data_dict[col_name] = series_data_df
        print("OK")
    except Exception as e:
        print(f"HIBA: {e}")
        data_dict[col_name] = pd.DataFrame(np.nan, index=global_powers, columns=[f'YR{y}' for y in fetch_years])

yearly_scores_all = pd.DataFrame(index=global_powers)

print("A globális birodalmi mátrix kiszámítása évről évre...")
for y in plot_years:
    yr_col = f'YR{y}'
    df_y = pd.DataFrame(index=global_powers)
    
    for col_name in indicators.values():
        if col_name in data_dict and yr_col in data_dict[col_name].columns:
            df_y[col_name] = data_dict[col_name][yr_col]
        else:
            df_y[col_name] = np.nan
            
    strict_cols = ['Energy_RnD', 'Energy_Patents', 'Hard_Military_Pct', 'Hard_EnergyVulnerability_INV']
    for col in strict_cols:
        if col in df_y.columns:
            df_y[col] = df_y[col].fillna(0)
    
    df_y = df_y.fillna(df_y.mean()).fillna(0)
    
    for col in df_y.columns:
        if '_INV' in col:
            df_y[col] = df_y[col] * -1
            
    df_y['Energy_Patents_PerCapita'] = df_y['Energy_Patents'] / df_y['Hard_Population'].replace(0, 1)
    df_y['Energy_Patents_Log'] = np.log10(df_y['Energy_Patents_PerCapita'].replace(0, np.nan).fillna(0.0001))
    df_y['Hard_Asym_Power'] = df_y['Hard_Military_Pct'] * df_y['Energy_RnD']
    df_y['Hard_Pop_Log'] = np.log10(df_y['Hard_Population'].replace(0, np.nan))
    df_y['Hard_GDP_Log'] = np.log10(df_y['Hard_GDP_USD'].replace(0, np.nan))
    df_y['Geo_Freshwater_Log'] = np.log10(df_y['Geo_Freshwater'].replace(0, np.nan))
    df_y['Geo_ArableLand_Log'] = np.log10(df_y['Geo_ArableLand'].replace(0, np.nan))
    
    calc_columns = [
        'Energy_RnD', 'Energy_YouthUnemp_INV', 'Energy_Patents_Log',
        'Openness_Bureaucracy_INV', 'Openness_TertiaryUnemp_INV', 'Openness_Top10Income_INV',
        'Cohesion_Gini_INV', 'Cohesion_Homicide_INV',
        'Demography_Fertility',
        'Hard_Pop_Log', 'Hard_GDP_Log', 'Hard_Asym_Power', 'Geo_Freshwater_Log', 'Geo_ArableLand_Log', 'Hard_EnergyVulnerability_INV'
    ]
    
    df_calc = df_y[calc_columns]
    df_calc = df_calc.replace([np.inf, -np.inf], np.nan)
    df_calc = df_calc.fillna(df_calc.mean()).fillna(0)
    
    std_dev = df_calc.std().replace(0, 1)
    df_z = ((df_calc - df_calc.mean()) / std_dev).fillna(0)
    
    df_1to10 = pd.DataFrame(index=df_y.index)
    for col in df_z.columns:
        z_clipped = np.clip(df_z[col], -2.5, 2.5) 
        df_1to10[col] = 1 + 9 * ((z_clipped - (-2.5)) / 5.0)
        
    Dim_Energy = (df_1to10['Energy_Patents_Log'] * 0.50) + (df_1to10['Energy_RnD'] * 0.30) + (df_1to10['Energy_YouthUnemp_INV'] * 0.20)
    Dim_Openness = df_1to10[['Openness_Bureaucracy_INV', 'Openness_TertiaryUnemp_INV', 'Openness_Top10Income_INV']].mean(axis=1)
    Dim_Cohesion = df_1to10[['Cohesion_Gini_INV', 'Cohesion_Homicide_INV']].mean(axis=1)
    Dim_Demography = df_1to10['Demography_Fertility'] 
    
    Score_OSCI = (Dim_Energy * Dim_Openness * Dim_Cohesion * Dim_Demography) ** 0.25
    
    HP_Pop = df_1to10['Hard_Pop_Log']
    HP_GDP = df_1to10['Hard_GDP_Log']
    HP_Military_Asym = df_1to10['Hard_Asym_Power']
    HP_Geo = df_1to10[['Geo_Freshwater_Log', 'Geo_ArableLand_Log']].mean(axis=1)
    HP_EnergySecurity = df_1to10['Hard_EnergyVulnerability_INV']
    
    Score_HardPower = (HP_GDP * 0.25 + HP_Military_Asym * 0.25 + HP_Pop * 0.20 + HP_Geo * 0.20 + HP_EnergySecurity * 0.10)
    
    FINAL_SCORE = (Score_OSCI * 0.65) + (Score_HardPower * 0.35)
    yearly_scores_all[y] = FINAL_SCORE

# --- GRAFIKON RAJZOLÁSA ---
print("Grafikon generálása...")
yearly_scores_plot = yearly_scores_all.loc[countries_to_plot]

plt.figure(figsize=(14, 8))
cmap = plt.get_cmap('tab20')

for i, country in enumerate(countries_to_plot):
    if country in ['USA', 'CHN', 'IND', 'RUS']:
        plt.plot(plot_years, yearly_scores_plot.loc[country], marker='o', linewidth=3.5, label=country)
    else:
        plt.plot(plot_years, yearly_scores_plot.loc[country], marker='', linewidth=1.5, alpha=0.5, label=country)

plt.title('Birodalmi Ciklusok: Geopolitikai Erő Trendjei (2000-2024)\n(Valós adatokkal, 102 országos referencia)', fontsize=16, fontweight='bold')
plt.xlabel('Év', fontsize=12)
plt.ylabel('Geopolitikai Pontszám (1-10)', fontsize=12)
plt.xticks(list(range(2000, 2025, 2))) 

plt.legend(bbox_to_anchor=(1.02, 1), loc='upper left', fontsize=10)
plt.grid(True, linestyle='--', alpha=0.4)
plt.tight_layout()

plt.savefig('historical_ranking_FINAL.png', dpi=300)
print("Kész! A történelmi adatfolyam javítva. Nyisd meg a 'historical_ranking_FINAL.png' fájlt!")