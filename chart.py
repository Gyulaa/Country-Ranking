import wbgapi as wb
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import time

# Csak a Top 15 legfontosabb hatalmat vizsgáljuk az átlátható grafikon miatt
top_countries = ['IND', 'USA', 'RUS', 'DEU', 'GBR', 'ISR', 'CHN', 'FRA', 'KAZ', 'NLD', 'JPN', 'CAN', 'SWE', 'POL', 'KOR']

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

years = range(2010, 2023)
data_dict = {}

print("Évtizedes történelmi adatok lekérése a Világbanktól (Hibatűrő mód, ez eltarthat pár percig)...")
for ind_code, col_name in indicators.items():
    print(f"Lekérdezés: {col_name}...", end=" ", flush=True)
    success = False
    
    # ÚJRAPRÓBÁLKOZÓ LOGIKA (3-szor fut neki, ha a JSON elromlik)
    for attempt in range(3):
        try:
            temp = wb.data.DataFrame(ind_code, top_countries, time=years)
            if temp is not None and not temp.empty:
                temp = temp.ffill(axis=1).bfill(axis=1)
                data_dict[col_name] = temp
            success = True
            break
        except Exception:
            time.sleep(2) # Várunk 2 másodpercet a szerver miatt
            
    if success:
        print("OK")
    else:
        print("HIBA (Üres adatokkal pótolva a stabilitásért)")
        # Biztonsági háló: létrehoz egy üres oszlopot, hogy ne kapjunk KeyError-t
        data_dict[col_name] = pd.DataFrame(np.nan, index=top_countries, columns=[f'YR{y}' for y in years])
        
    time.sleep(1)

yearly_scores = pd.DataFrame(index=top_countries)

print("A birodalmi mátrix kiszámítása évről évre...")
for y in years:
    yr_col = f'YR{y}'
    df_y = pd.DataFrame(index=top_countries)
    
    # BIZTONSÁGI JAVÍTÁS: Kényszerítjük, hogy MINDEN indikátor oszlop létezzen
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
    
    # 65/35-ös súlyozás
    FINAL_SCORE = (Score_OSCI * 0.65) + (Score_HardPower * 0.35)
    yearly_scores[y] = FINAL_SCORE

# --- GRAFIKON RAJZOLÁSA (matplotlib) ---
print("Grafikon generálása...")
plt.figure(figsize=(14, 8))

# Szép színskála
cmap = plt.get_cmap('tab20')

for i, country in enumerate(top_countries):
    # Kiemeljük vastagabb vonallal a legnagyobb játékosokat
    if country in ['USA', 'CHN', 'IND', 'RUS']:
        plt.plot(years, yearly_scores.loc[country], marker='o', linewidth=3.5, label=country)
    else:
        plt.plot(years, yearly_scores.loc[country], marker='', linewidth=1.5, alpha=0.5, label=country)

plt.title('Birodalmi Ciklusok: Geopolitikai Erő Trendjei (2010-2022)\n(70% Belső Vitalitás - 30% Nyers Erő)', fontsize=16, fontweight='bold')
plt.xlabel('Év', fontsize=12)
plt.ylabel('Geopolitikai Pontszám (1-10)', fontsize=12)
plt.xticks(years)

# Jelmagyarázat formázása
plt.legend(bbox_to_anchor=(1.02, 1), loc='upper left', fontsize=10)
plt.grid(True, linestyle='--', alpha=0.4)
plt.tight_layout()

# Mentés
plt.savefig('historical_ranking.png', dpi=300)
print("Kész! Nyisd meg a 'historical_ranking.png' fájlt a mappádban!")