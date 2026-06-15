# historical_dashboard.py
# Generates historical_dashboard.html: interactive geopolitical trend chart (2010-2023)
# Uses cached historical_scores.xlsx if available, otherwise downloads from World Bank.

import pandas as pd
import numpy as np
import os, sys, time, json as _json, colorsys
import glob as _glob
import wbgapi as wb

CACHE_FILE  = "historical_scores.xlsx"
OUTPUT_HTML = "historical_dashboard.html"
YEARS       = list(range(2000, 2025))

global_powers = [
    'USA', 'CAN', 'GBR', 'FRA', 'DEU', 'ITA', 'ESP', 'NLD', 'BEL', 'CHE', 'SWE', 'DNK', 'NOR', 'FIN', 'IRL', 'PRT', 'AUT', 'ISL',
    'RUS', 'UKR', 'BLR', 'POL', 'ROU', 'CZE', 'HUN', 'SVK', 'LTU', 'LVA', 'EST',
    'GRC', 'SRB', 'BGR', 'HRV', 'SVN', 'BIH', 'ALB', 'MKD', 'MNE',
    'CHN', 'JPN', 'IND', 'KOR', 'AUS', 'NZL', 'IDN', 'VNM', 'PHL', 'MYS', 'SGP', 'THA', 'PAK', 'BGD', 'LKA', 'MNG', 'NPL', 'KHM', 'MMR',
    'KAZ', 'UZB', 'AZE', 'GEO', 'ARM',
    'ISR', 'SAU', 'TUR', 'ARE', 'IRN', 'EGY', 'MAR', 'DZA', 'QAT', 'KWT', 'OMN', 'JOR', 'IRQ', 'TUN',
    'BRA', 'MEX', 'ARG', 'COL', 'CHL', 'PER', 'VEN', 'ECU', 'DOM', 'GTM', 'URY', 'CRI', 'PAN', 'BOL', 'PRY',
    'NGA', 'ZAF', 'KEN', 'ETH', 'GHA', 'AGO', 'CIV', 'RWA', 'TZA', 'CMR', 'UGA',
]

COUNTRY_NAMES = {
    'USA': 'United States', 'CAN': 'Canada', 'GBR': 'United Kingdom',
    'FRA': 'France', 'DEU': 'Germany', 'ITA': 'Italy', 'ESP': 'Spain',
    'NLD': 'Netherlands', 'BEL': 'Belgium', 'CHE': 'Switzerland',
    'SWE': 'Sweden', 'DNK': 'Denmark', 'NOR': 'Norway', 'FIN': 'Finland',
    'IRL': 'Ireland', 'PRT': 'Portugal', 'AUT': 'Austria',
    'RUS': 'Russia', 'UKR': 'Ukraine', 'POL': 'Poland', 'ROU': 'Romania',
    'CZE': 'Czech Republic', 'HUN': 'Hungary', 'GRC': 'Greece',
    'SRB': 'Serbia', 'BGR': 'Bulgaria', 'HRV': 'Croatia', 'SVK': 'Slovakia',
    'LTU': 'Lithuania', 'CHN': 'China', 'JPN': 'Japan', 'IND': 'India',
    'KOR': 'South Korea', 'AUS': 'Australia', 'NZL': 'New Zealand',
    'IDN': 'Indonesia', 'VNM': 'Vietnam', 'PHL': 'Philippines',
    'MYS': 'Malaysia', 'SGP': 'Singapore', 'THA': 'Thailand',
    'PAK': 'Pakistan', 'BGD': 'Bangladesh', 'LKA': 'Sri Lanka',
    'KAZ': 'Kazakhstan', 'UZB': 'Uzbekistan', 'ISR': 'Israel',
    'SAU': 'Saudi Arabia', 'TUR': 'Turkey', 'ARE': 'UAE', 'IRN': 'Iran',
    'EGY': 'Egypt', 'MAR': 'Morocco', 'DZA': 'Algeria', 'QAT': 'Qatar',
    'KWT': 'Kuwait', 'OMN': 'Oman', 'JOR': 'Jordan', 'IRQ': 'Iraq',
    'BRA': 'Brazil', 'MEX': 'Mexico', 'ARG': 'Argentina', 'COL': 'Colombia',
    'CHL': 'Chile', 'PER': 'Peru', 'VEN': 'Venezuela', 'ECU': 'Ecuador',
    'DOM': 'Dominican Rep.', 'GTM': 'Guatemala', 'NGA': 'Nigeria',
    'ZAF': 'South Africa', 'KEN': 'Kenya', 'ETH': 'Ethiopia',
    'GHA': 'Ghana', 'AGO': 'Angola', 'CIV': 'Ivory Coast',
    'ISL': 'Iceland', 'BLR': 'Belarus', 'LVA': 'Latvia', 'EST': 'Estonia',
    'SVN': 'Slovenia', 'BIH': 'Bosnia & Herz.', 'ALB': 'Albania',
    'MKD': 'North Macedonia', 'MNE': 'Montenegro',
    'MNG': 'Mongolia', 'NPL': 'Nepal', 'KHM': 'Cambodia', 'MMR': 'Myanmar',
    'AZE': 'Azerbaijan', 'GEO': 'Georgia', 'ARM': 'Armenia',
    'TUN': 'Tunisia',
    'URY': 'Uruguay', 'CRI': 'Costa Rica', 'PAN': 'Panama',
    'BOL': 'Bolivia', 'PRY': 'Paraguay',
    'RWA': 'Rwanda', 'TZA': 'Tanzania', 'CMR': 'Cameroon', 'UGA': 'Uganda',
}

REGIONS = {}
for c in ['USA','CAN','BRA','MEX','ARG','COL','CHL','PER','VEN','ECU','DOM','GTM']:
    REGIONS[c] = 'Americas'
for c in ['GBR','FRA','DEU','ITA','ESP','NLD','BEL','CHE','SWE','DNK','NOR','FIN',
          'IRL','PRT','AUT','POL','ROU','CZE','HUN','GRC','SRB','BGR','HRV','SVK',
          'LTU','UKR','RUS']:
    REGIONS[c] = 'Europe'
for c in ['CHN','JPN','IND','KOR','AUS','NZL','IDN','VNM','PHL','MYS','SGP','THA',
          'PAK','BGD','LKA','KAZ','UZB']:
    REGIONS[c] = 'Asia'
for c in ['ISR','SAU','TUR','ARE','IRN','EGY','MAR','DZA','QAT','KWT','OMN','JOR','IRQ']:
    REGIONS[c] = 'Middle East'
for c in ['NGA','ZAF','KEN','ETH','GHA','AGO','CIV','RWA','TZA','CMR','UGA']:
    REGIONS[c] = 'Africa'
for c in ['ISL','BLR','LVA','EST','SVN','BIH','ALB','MKD','MNE']:
    REGIONS[c] = 'Europe'
for c in ['MNG','NPL','KHM','MMR','AZE','GEO','ARM']:
    REGIONS[c] = 'Asia'
for c in ['TUN']:
    REGIONS[c] = 'Middle East'
for c in ['URY','CRI','PAN','BOL','PRY']:
    REGIONS[c] = 'Americas'

REGION_BASE = {
    'Europe':      (78,  121, 167),
    'Asia':        (242, 142, 43),
    'Americas':    (89,  161, 79),
    'Middle East': (237, 201, 72),
    'Africa':      (176, 122, 161),
}
REGION_COLORS_HEX = {
    'Europe': '#4e79a7', 'Asia': '#f28e2b', 'Americas': '#59a14f',
    'Middle East': '#edc948', 'Africa': '#b07aa1',
}

METRICS = {
    'FINAL_SCORE_1_10': 'Végső Geopolitikai Pontszám',
    'Score_OSCI':       'OSCI (Belső Vitalitás)',
    'Score_HardPower':  'Hard Power',
    'Dim_Energy':       'Energia & Innováció',
    'Dim_Openness':     'Nyitottság',
    'Dim_Cohesion':     'Kohézió',
    'Dim_Demography':   'Demográfia',
}

indicators = {
    'GB.XPD.RSDV.GD.ZS': 'Energy_RnD',
    'SL.UEM.1524.ZS':     'Energy_YouthUnemp_INV',
    'IP.PAT.RESD':        'Energy_Patents',
    'IC.REG.DURS':        'Openness_Bureaucracy_INV',
    'SL.UEM.TERT.ZS':     'Openness_TertiaryUnemp_INV',
    'SI.DST.10TH.10':     'Openness_Top10Income_INV',
    'SI.POV.GINI':        'Cohesion_Gini_INV',
    'VC.IHR.PSRC.P5':     'Cohesion_Homicide_INV',
    'SP.DYN.TFRT.IN':     'Demography_Fertility',
    'SP.POP.TOTL':        'Hard_Population',
    'NY.GDP.MKTP.CD':     'Hard_GDP_USD',
    'MS.MIL.XPND.GD.ZS': 'Hard_Military_Pct',
    'ER.H2O.INTR.K3':     'Geo_Freshwater',
    'AG.LND.ARBL.HA':     'Geo_ArableLand',
    'TM.VAL.FUEL.ZS.UN':  'Hard_EnergyVulnerability_INV',
}

calc_columns = [
    'Energy_RnD', 'Energy_YouthUnemp_INV', 'Energy_Patents_Log',
    'Openness_Bureaucracy_INV', 'Openness_TertiaryUnemp_INV', 'Openness_Top10Income_INV',
    'Cohesion_Gini_INV', 'Cohesion_Homicide_INV', 'Demography_Fertility',
    'Hard_Pop_Log', 'Hard_GDP_Log', 'Hard_Asym_Power',
    'Geo_Freshwater_Log', 'Geo_ArableLand_Log', 'Hard_EnergyVulnerability_INV',
]

# ── SCORE CALCULATION ─────────────────────────────────────────────────────────
def calc_scores(df_y):
    for col in ['Energy_RnD', 'Energy_Patents', 'Hard_Military_Pct', 'Hard_EnergyVulnerability_INV']:
        if col in df_y.columns:
            df_y[col] = df_y[col].fillna(0)
    df_y = df_y.fillna(df_y.mean(numeric_only=True))
    for col in df_y.columns:
        if '_INV' in col:
            df_y[col] = df_y[col] * -1
    df_y['Energy_Patents_PerCapita'] = df_y['Energy_Patents'] / df_y['Hard_Population'].replace(0, 1)
    df_y['Energy_Patents_Log']       = np.log10(df_y['Energy_Patents_PerCapita'].replace(0, np.nan).fillna(0.0001))
    df_y['Hard_Asym_Power']          = df_y['Hard_Military_Pct'] * df_y['Energy_RnD']
    df_y['Hard_Pop_Log']             = np.log10(df_y['Hard_Population'].replace(0, np.nan))
    df_y['Hard_GDP_Log']             = np.log10(df_y['Hard_GDP_USD'].replace(0, np.nan))
    df_y['Geo_Freshwater_Log']       = np.log10(df_y['Geo_Freshwater'].replace(0, np.nan))
    df_y['Geo_ArableLand_Log']       = np.log10(df_y['Geo_ArableLand'].replace(0, np.nan))
    df_c = df_y[calc_columns].replace([np.inf, -np.inf], np.nan)
    df_c = df_c.fillna(df_c.mean()).fillna(0)
    std  = df_c.std().replace(0, 1)
    df_z = ((df_c - df_c.mean()) / std).fillna(0)
    df_1 = pd.DataFrame(index=df_y.index)
    for col in df_z.columns:
        z = np.clip(df_z[col], -2.5, 2.5)
        df_1[col] = 1 + 9 * ((z + 2.5) / 5.0)
    res = pd.DataFrame(index=df_y.index)
    res['Dim_Energy']    = df_1['Energy_Patents_Log']*0.50 + df_1['Energy_RnD']*0.30 + df_1['Energy_YouthUnemp_INV']*0.20
    res['Dim_Openness']  = df_1[['Openness_Bureaucracy_INV','Openness_TertiaryUnemp_INV','Openness_Top10Income_INV']].mean(axis=1)
    res['Dim_Cohesion']  = df_1[['Cohesion_Gini_INV','Cohesion_Homicide_INV']].mean(axis=1)
    res['Dim_Demography']= df_1['Demography_Fertility']
    res['Score_OSCI']    = (res['Dim_Energy'] * res['Dim_Openness'] * res['Dim_Cohesion'] * res['Dim_Demography']) ** 0.25
    res['HP_GDP']        = df_1['Hard_GDP_Log']
    res['HP_Pop']        = df_1['Hard_Pop_Log']
    res['HP_Military_Asym'] = df_1['Hard_Asym_Power']
    res['HP_Geo']        = df_1[['Geo_Freshwater_Log','Geo_ArableLand_Log']].mean(axis=1)
    res['HP_EnergySecurity'] = df_1['Hard_EnergyVulnerability_INV']
    res['Score_HardPower']   = res['HP_GDP']*0.25 + res['HP_Military_Asym']*0.25 + res['HP_Pop']*0.20 + res['HP_Geo']*0.20 + res['HP_EnergySecurity']*0.10
    res['FINAL_SCORE_1_10']  = res['Score_OSCI']*0.65 + res['Score_HardPower']*0.35
    return res

# ── LOAD OR DOWNLOAD ──────────────────────────────────────────────────────────
metric_cols = list(METRICS.keys())

if os.path.exists(CACHE_FILE):
    print(f"Cache betöltése: {CACHE_FILE}")
    df_hist = pd.read_excel(CACHE_FILE, index_col=[0, 1])
    df_hist.index.names = ['ISO', 'Year']
    print(f"Betöltve: {len(df_hist)} sor")
else:
    print(f"Adatok letöltése {len(global_powers)} országhoz, {len(YEARS)} évre (ez 2-5 percet vesz igénybe)...")
    chunk_size = 15
    chunks = [global_powers[i:i+chunk_size] for i in range(0, len(global_powers), chunk_size)]
    raw = {}
    for ind_code, col_name in indicators.items():
        print(f"  {col_name}...", end=" ", flush=True)
        series = pd.DataFrame(index=global_powers, columns=YEARS, dtype=float)
        for chunk in chunks:
            for attempt in range(3):
                try:
                    temp = wb.data.DataFrame(ind_code, chunk, time=YEARS)
                    if temp is not None and not temp.empty:
                        tf = temp.ffill(axis=1).bfill(axis=1)
                        for iso in chunk:
                            if iso in tf.index:
                                for y in YEARS:
                                    c = f'YR{y}'
                                    if c in tf.columns:
                                        series.loc[iso, y] = tf.loc[iso, c]
                    break
                except Exception:
                    if attempt < 2:
                        time.sleep(3)
            time.sleep(0.8)
        raw[col_name] = series
        print("OK")

    print("Pontszámok kiszámítása évenként...")
    records = []
    for y in YEARS:
        df_y = pd.DataFrame(index=global_powers)
        for col_name in indicators.values():
            df_y[col_name] = raw[col_name][y] if y in raw[col_name].columns else np.nan
        scores = calc_scores(df_y.copy())
        for iso in global_powers:
            row = {'ISO': iso, 'Year': y}
            for m in metric_cols:
                row[m] = scores.loc[iso, m] if iso in scores.index else np.nan
            records.append(row)
    df_hist = pd.DataFrame(records).set_index(['ISO', 'Year'])
    df_hist.index.names = ['ISO', 'Year']
    df_hist.to_excel(CACHE_FILE)
    print(f"Cache elmentve: {CACHE_FILE}")

# ── COLORS ────────────────────────────────────────────────────────────────────
def _gen_color(iso):
    region = REGIONS.get(iso, 'Egyéb')
    base   = REGION_BASE.get(region, (100, 100, 100))
    members = [c for c in global_powers if REGIONS.get(c) == region]
    idx   = members.index(iso) if iso in members else 0
    total = max(len(members), 1)
    r, g, b = [x/255 for x in base]
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    h = (h + idx * 0.21 / total) % 1.0
    v = max(0.40, v + ((idx % 3) - 1) * 0.06)
    r2, g2, b2 = colorsys.hsv_to_rgb(h, s, v)
    return f'rgba({int(r2*255)},{int(g2*255)},{int(b2*255)},0.9)'

country_colors = {iso: _gen_color(iso) for iso in global_powers}

# ── TOP 10 from latest xlsx ───────────────────────────────────────────────────
_xlsx = sorted(_glob.glob("Geopolitical*.xlsx"), key=os.path.getmtime)
if _xlsx:
    _df_cur = pd.read_excel(_xlsx[-1], index_col=0)
    _top10  = [c for c in _df_cur['FINAL_SCORE_1_10'].nlargest(10).index if c in global_powers]
else:
    _top10 = ['IND','NLD','SWE','KOR','ISR','USA','DEU','FIN','NOR','CHE']

PRESET_GROUPS = {
    'Top 10 (jelenlegi)': _top10,
    'G7':                 ['USA','CAN','GBR','FRA','DEU','ITA','JPN'],
    'BRICS+':             ['BRA','RUS','IND','CHN','ZAF','ARE','SAU','EGY','IRN','ETH'],
    'NATO Nagyok':        ['USA','GBR','FRA','DEU','TUR','POL','NLD','ESP','ITA'],
    'Kelet-Ázsia':        ['CHN','JPN','KOR','IND','SGP','VNM','THA','MYS','IDN'],
    'Öböl-menti':         ['SAU','ARE','QAT','KWT','OMN','IRN','IRQ'],
    'Kelet-Európa':       ['POL','HUN','CZE','ROU','SVK','LTU','LVA','EST','UKR','BLR'],
    'Balkán':             ['GRC','SRB','BGR','HRV','SVN','BIH','ALB','MKD','MNE'],
    'Kaukázus+Közép-Ázsia': ['KAZ','UZB','AZE','GEO','ARM','MNG'],
    'Latin-Amerika':      ['BRA','MEX','ARG','COL','CHL','PER','URY','CRI'],
    'Afrika':             ['NGA','ZAF','KEN','ETH','GHA','AGO','RWA','TZA','CMR','UGA'],
}

# ── JS DATA ───────────────────────────────────────────────────────────────────
hist_js = {}
for iso in global_powers:
    hist_js[iso] = {}
    for m in metric_cols:
        vals = []
        for y in YEARS:
            try:
                v = df_hist.loc[(iso, y), m]
                vals.append(round(float(v), 3) if pd.notna(v) else None)
            except Exception:
                vals.append(None)
        hist_js[iso][m] = vals

# ── SIDEBAR HTML ──────────────────────────────────────────────────────────────
def _region_order(iso):
    order = ['Europe','Asia','Americas','Middle East','Africa']
    r = REGIONS.get(iso,'Egyéb')
    return (order.index(r) if r in order else 99, COUNTRY_NAMES.get(iso, iso))

sidebar_items = ""
cur_region = None
for iso in sorted(global_powers, key=_region_order):
    r  = REGIONS.get(iso, 'Egyéb')
    if r != cur_region:
        cur_region = r
        rc = REGION_COLORS_HEX.get(r, '#888')
        sidebar_items += f'<div class="region-hdr" style="color:{rc}">{r}</div>\n'
    name    = COUNTRY_NAMES.get(iso, iso)
    checked = 'checked' if iso in _top10 else ''
    sidebar_items += (
        f'<label class="cb-label" data-name="{name.lower()}" data-iso="{iso.lower()}">'
        f'<input type="checkbox" id="cb-{iso}" class="country-cb" data-iso="{iso}" {checked}>'
        f'<span class="iso-t">{iso}</span>{name}</label>\n'
    )

preset_btns = "".join(
    f'<button class="preset-btn" onclick="applyPreset({_json.dumps(k)})">{k}</button>\n'
    for k in PRESET_GROUPS
)

metric_opts = "\n".join(
    f'    <option value="{i}">{lbl}</option>'
    for i, (_, lbl) in enumerate(METRICS.items())
)

# ── JSON payloads ─────────────────────────────────────────────────────────────
year_labels_json    = _json.dumps(YEARS)
metric_keys_json    = _json.dumps(metric_cols)
metric_labels_json  = _json.dumps(list(METRICS.values()))
hist_json           = _json.dumps(hist_js)
country_list_json   = _json.dumps(global_powers)
country_names_json  = _json.dumps(COUNTRY_NAMES)
country_colors_json = _json.dumps(country_colors)
preset_groups_json  = _json.dumps(PRESET_GROUPS)
top10_json          = _json.dumps(_top10)

# ── HTML TEMPLATE ─────────────────────────────────────────────────────────────
html = f"""<!DOCTYPE html>
<html lang="hu">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Birodalmi Ciklusok – Geopolitikai Trendek 2010–2023</title>
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ background: #0d1117; color: #e6edf3; font-family: 'Segoe UI', Arial, sans-serif; padding: 16px 20px; }}
    a {{ color: #58a6ff; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}

    header {{ text-align: center; margin-bottom: 16px; }}
    header h1 {{
      font-size: 23px; font-weight: 700;
      background: linear-gradient(90deg, #f28e2b 0%, #58a6ff 100%);
      -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
    }}
    header p {{ color: #8b949e; font-size: 12px; margin-top: 5px; }}

    .top-controls {{
      background: #161b22; border: 1px solid #30363d; border-radius: 10px;
      padding: 10px 16px; margin-bottom: 14px;
      display: flex; flex-wrap: wrap; align-items: center; gap: 10px;
    }}
    .ctrl-label {{ color: #8b949e; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.7px; white-space: nowrap; }}
    select#metric-sel {{
      background: #21262d; color: #e6edf3; border: 1px solid #58a6ff;
      border-radius: 6px; padding: 6px 12px; font-size: 13px; cursor: pointer; outline: none;
    }}
    .preset-row {{ display: flex; flex-wrap: wrap; gap: 6px; align-items: center; margin-left: auto; }}
    .preset-btn {{
      background: #21262d; color: #8b949e; border: 1px solid #30363d;
      border-radius: 5px; padding: 4px 10px; font-size: 11px; cursor: pointer; transition: all 0.15s;
    }}
    .preset-btn:hover {{ background: #30363d; color: #e6edf3; border-color: #58a6ff; }}

    .main-layout {{ display: grid; grid-template-columns: 215px 1fr; gap: 14px; align-items: start; }}

    .sidebar {{
      background: #161b22; border: 1px solid #30363d; border-radius: 10px;
      padding: 10px; position: sticky; top: 10px; max-height: 82vh; overflow-y: auto;
    }}
    .sidebar-title {{ color: #58a6ff; font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 8px; }}
    .sidebar-search {{
      width: 100%; background: #21262d; color: #e6edf3;
      border: 1px solid #30363d; border-radius: 5px;
      padding: 5px 8px; font-size: 12px; outline: none; margin-bottom: 6px;
    }}
    .sidebar-search:focus {{ border-color: #58a6ff; }}
    .sb-actions {{ display: flex; gap: 6px; margin-bottom: 8px; }}
    .sb-btn {{
      flex: 1; background: #21262d; color: #8b949e; border: 1px solid #30363d;
      border-radius: 5px; padding: 4px 0; font-size: 10px; cursor: pointer; text-align: center;
    }}
    .sb-btn:hover {{ color: #e6edf3; border-color: #58a6ff; }}
    .region-hdr {{ font-size: 9.5px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; margin: 8px 0 3px; }}
    .cb-label {{
      display: flex; align-items: center; gap: 5px; padding: 3px 4px;
      border-radius: 4px; cursor: pointer; font-size: 12px; color: #c9d1d9; transition: background 0.1s;
    }}
    .cb-label:hover {{ background: #21262d; }}
    .cb-label input {{ cursor: pointer; accent-color: #58a6ff; flex-shrink: 0; }}
    .iso-t {{
      background: #21262d; border: 1px solid #30363d; border-radius: 3px;
      padding: 0 4px; font-size: 9px; color: #8b949e; font-family: monospace; flex-shrink: 0;
    }}

    .chart-card {{ background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 12px 12px 4px; }}
    .card-title {{ font-size: 10px; color: #58a6ff; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; }}
    .selected-count {{ color: #6e7681; font-size: 11px; margin-left: auto; }}

    footer {{ text-align: center; color: #30363d; font-size: 11px; margin-top: 14px; }}

    @media (max-width: 768px) {{
      body {{ padding: 10px; }}
      .main-layout {{ grid-template-columns: 1fr; }}
      .sidebar {{ position: static; max-height: 260px; }}
      header h1 {{ font-size: 17px; }}
      .preset-row {{ margin-left: 0; }}
      .top-controls {{ gap: 8px; }}
    }}
  </style>
</head>
<body>

<header>
  <h1>Birodalmi Ciklusok: Geopolitikai Trendek 2000–2024</h1>
  <p>76 ország &nbsp;·&nbsp; World Bank (WDI) adatok &nbsp;·&nbsp; <a href="index.html">← Vissza a Dashboardhoz</a></p>
</header>

<div class="top-controls">
  <span class="ctrl-label">Mutató:</span>
  <select id="metric-sel">
{metric_opts}
  </select>
  <div class="preset-row">
    <span class="ctrl-label">Csoportok:</span>
{preset_btns}    <button class="preset-btn" style="color:#f85149;border-color:#f85149" onclick="clearAll()">✕ Töröl</button>
  </div>
</div>

<div class="main-layout">
  <div class="sidebar">
    <div class="sidebar-title">Ország kiválasztó</div>
    <input type="text" class="sidebar-search" id="country-search" placeholder="Keresés (pl. HUN, India)...">
    <div class="sb-actions">
      <div class="sb-btn" onclick="selectAll()">Mind</div>
      <div class="sb-btn" onclick="clearAll()">Töröl</div>
    </div>
    <div id="country-list">
{sidebar_items}    </div>
  </div>

  <div class="chart-card">
    <div style="display:flex;align-items:center;margin-bottom:6px;">
      <div class="card-title" id="chart-title">Végső Geopolitikai Pontszám – Trendje (2000–2024)</div>
      <span class="selected-count" id="sel-count"></span>
    </div>
    <div id="hist-fig"></div>
  </div>
</div>

<footer>Adatforrás: World Bank WDI &nbsp;·&nbsp; Generálva: historical_dashboard.py &nbsp;·&nbsp; <a href="index.html">← Dashboard</a></footer>

<script>
var YEARS          = {year_labels_json};
var METRIC_KEYS    = {metric_keys_json};
var METRIC_LABELS  = {metric_labels_json};
var HIST           = {hist_json};
var COUNTRY_LIST   = {country_list_json};
var COUNTRY_NAMES  = {country_names_json};
var COUNTRY_COLORS = {country_colors_json};
var PRESET_GROUPS  = {preset_groups_json};
var DEFAULT_VIS    = {top10_json};

// ── Build initial traces ────────────────────────────────────────────────────
var metric0 = METRIC_KEYS[0];
var traces = COUNTRY_LIST.map(function(iso) {{
  return {{
    x: YEARS,
    y: HIST[iso][metric0],
    mode: 'lines+markers',
    name: COUNTRY_NAMES[iso] || iso,
    visible: DEFAULT_VIS.indexOf(iso) >= 0,
    line: {{ color: COUNTRY_COLORS[iso], width: 2 }},
    marker: {{ size: 4 }},
    hovertemplate: '<b>' + (COUNTRY_NAMES[iso] || iso) + ' (' + iso + ')</b><br>%{{x}}: <b>%{{y:.2f}}</b><extra></extra>',
  }};
}});

var layout = {{
  paper_bgcolor: '#161b22', plot_bgcolor: '#0d1117',
  font: {{ color: '#e6edf3', family: 'Segoe UI, Arial' }},
  height: 560,
  margin: {{ t: 10, b: 50, l: 55, r: 20 }},
  xaxis: {{
    tickvals: YEARS, ticktext: YEARS.map(String),
    gridcolor: '#21262d', zerolinecolor: '#21262d',
    tickfont: {{ color: '#8b949e', size: 10 }},
  }},
  yaxis: {{
    title: {{ text: METRIC_LABELS[0], font: {{ color: '#8b949e', size: 11 }} }},
    autorange: true, gridcolor: '#21262d', zerolinecolor: '#21262d',
    tickfont: {{ color: '#8b949e', size: 10 }},
  }},
  legend: {{
    bgcolor: '#0d1117', bordercolor: '#30363d', borderwidth: 1,
    font: {{ size: 10 }},
  }},
  hovermode: 'closest',
}};

var cfg = {{ responsive: true, displayModeBar: true, displaylogo: false,
  modeBarButtonsToRemove: ['select2d','lasso2d'] }};

Plotly.newPlot('hist-fig', traces, layout, cfg);
updateCount();

// ── Helpers ──────────────────────────────────────────────────────────────────
function updateCount() {{
  var n = COUNTRY_LIST.filter(function(iso, i) {{
    var el = document.getElementById('hist-fig');
    return el && el.data && el.data[i] && el.data[i].visible;
  }}).length;
  document.getElementById('sel-count').textContent = n + ' ország látható';
}}

// ── Metric change ────────────────────────────────────────────────────────────
document.getElementById('metric-sel').addEventListener('change', function() {{
  var idx = parseInt(this.value, 10);
  var metric = METRIC_KEYS[idx];
  var newY = COUNTRY_LIST.map(function(iso) {{ return HIST[iso][metric]; }});
  Plotly.restyle('hist-fig', {{ y: newY }});
  Plotly.relayout('hist-fig', {{ 'yaxis.title.text': METRIC_LABELS[idx], 'yaxis.autorange': true }});
  document.getElementById('chart-title').textContent = METRIC_LABELS[idx] + ' – Trendje (2000–2024)';
}});

// ── Country checkboxes ────────────────────────────────────────────────────────
document.getElementById('country-list').addEventListener('change', function(e) {{
  if (!e.target.classList.contains('country-cb')) return;
  var iso = e.target.getAttribute('data-iso');
  var idx = COUNTRY_LIST.indexOf(iso);
  if (idx >= 0) {{
    Plotly.restyle('hist-fig', {{ visible: e.target.checked }}, [idx]);
    setTimeout(updateCount, 50);
  }}
}});

// ── Presets ───────────────────────────────────────────────────────────────────
function applyPreset(name) {{
  var group = PRESET_GROUPS[name] || [];
  var visArr = COUNTRY_LIST.map(function(iso) {{ return group.indexOf(iso) >= 0; }});
  Plotly.restyle('hist-fig', {{ visible: visArr }});
  COUNTRY_LIST.forEach(function(iso) {{
    var cb = document.getElementById('cb-' + iso);
    if (cb) cb.checked = group.indexOf(iso) >= 0;
  }});
  setTimeout(updateCount, 50);
}}

function selectAll() {{
  Plotly.restyle('hist-fig', {{ visible: true }});
  document.querySelectorAll('.country-cb').forEach(function(cb) {{ cb.checked = true; }});
  setTimeout(updateCount, 50);
}}

function clearAll() {{
  Plotly.restyle('hist-fig', {{ visible: false }});
  document.querySelectorAll('.country-cb').forEach(function(cb) {{ cb.checked = false; }});
  setTimeout(updateCount, 50);
}}

// ── Search ────────────────────────────────────────────────────────────────────
document.getElementById('country-search').addEventListener('input', function() {{
  var q = this.value.toLowerCase();
  var regionHdrs = {{}};
  document.querySelectorAll('#country-list .cb-label').forEach(function(el) {{
    var match = !q || el.getAttribute('data-name').includes(q) || el.getAttribute('data-iso').includes(q);
    el.style.display = match ? '' : 'none';
  }});
  document.querySelectorAll('#country-list .region-hdr').forEach(function(hdr) {{
    var next = hdr.nextElementSibling;
    var anyVisible = false;
    while (next && !next.classList.contains('region-hdr')) {{
      if (next.style.display !== 'none') anyVisible = true;
      next = next.nextElementSibling;
    }}
    hdr.style.display = anyVisible ? '' : 'none';
  }});
}});

// ── Mobile resize ─────────────────────────────────────────────────────────────
window.addEventListener('resize', function() {{
  clearTimeout(window._rt);
  window._rt = setTimeout(function() {{
    Plotly.relayout('hist-fig', {{ height: window.innerWidth < 768 ? 380 : 560 }});
  }}, 150);
}});
</script>
</body>
</html>"""

with open(OUTPUT_HTML, 'w', encoding='utf-8') as fh:
    fh.write(html)

print(f"Historical dashboard mentve: {OUTPUT_HTML}")
print("Elérési út: " + os.path.abspath(OUTPUT_HTML))
