import pandas as pd
import plotly.graph_objects as go
import os, sys, json as _json, urllib.request

OUTPUT_HTML = "index.html"

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
for c in ['NGA','ZAF','KEN','ETH','GHA','AGO','CIV']:
    REGIONS[c] = 'Africa'

REGION_COLORS = {
    'Europe': '#4e79a7', 'Asia': '#f28e2b', 'Americas': '#59a14f',
    'Middle East': '#edc948', 'Africa': '#b07aa1',
}

METRICS = {
    'FINAL_SCORE_1_10': 'Végső Geopolitikai Pontszám',
    'Score_OSCI':       'OSCI (Soft Power)',
    'Score_HardPower':  'Hard Power',
    'Dim_Energy':       'Energia & Vitalitás',
    'Dim_Openness':     'Nyitottság',
    'Dim_Cohesion':     'Kohézió',
    'Dim_Demography':   'Demográfia',
}

RADAR_DIMS   = ['Dim_Energy','Dim_Openness','Dim_Cohesion','Dim_Demography','Score_HardPower']
RADAR_LABELS = ['Energia','Nyitottság','Kohézió','Demográfia','Hard Power']
TRACE_COLORS = ['#58a6ff','#f85149','#3fb950','#d29922','#bc8cff','#e3b341','#79c0ff']

# ── LOAD DATA ────────────────────────────────────────────────────────────────
def _find_excel():
    import glob
    files = glob.glob("Geopolitical*.xlsx")
    return max(files, key=os.path.getmtime) if files else None

EXCEL_FILE = _find_excel()
if EXCEL_FILE is None:
    print("Nincs Geopolitical*.xlsx. Futtatom geo76.py-t...")
    import subprocess
    subprocess.run([sys.executable, 'geo76.py'], check=True)
    EXCEL_FILE = _find_excel()
    if EXCEL_FILE is None:
        sys.exit('HIBA: xlsx nem jött létre.')

print(f"Adatforrás: {EXCEL_FILE}")
df = pd.read_excel(EXCEL_FILE, index_col=0)
df['Name']   = [COUNTRY_NAMES.get(iso, iso) for iso in df.index]
df['Region'] = [REGIONS.get(iso, 'Egyéb') for iso in df.index]
df['rank']   = df['FINAL_SCORE_1_10'].rank(ascending=False).astype(int)

n_countries = len(df)
metric_list = list(METRICS.items())
n = len(metric_list)

top5 = df.sort_values('FINAL_SCORE_1_10', ascending=False).head(5).index.tolist()
RADAR_GROUPS = {
    'Top 5':       top5,
    'G7':          [c for c in ['USA','CAN','GBR','FRA','DEU','ITA','JPN'] if c in df.index],
    'BRICS':       [c for c in ['BRA','RUS','IND','CHN','ZAF'] if c in df.index],
    'NATO Nagyok': [c for c in ['USA','GBR','FRA','DEU','TUR'] if c in df.index],
    'Kelet-Ázsia': [c for c in ['CHN','JPN','KOR','IND','SGP'] if c in df.index],
    'Öböl-menti':  [c for c in ['SAU','ARE','QAT','KWT','OMN'] if c in df.index],
}

# ── GEOJSON LETÖLTÉS ─────────────────────────────────────────────────────────
USE_TILE = False
GEOJSON  = None
print("GeoJSON letöltése...", end=" ", flush=True)
try:
    _url = ("https://raw.githubusercontent.com/nvkelso/natural-earth-vector"
            "/master/geojson/ne_110m_admin_0_countries.geojson")
    with urllib.request.urlopen(_url, timeout=20) as _r:
        GEOJSON = _json.load(_r)
    for _f in GEOJSON['features']:
        _p = _f['properties']
        if _p.get('ISO_A3') in ('-99', -99, None):
            _p['ISO_A3'] = _p.get('ADM0_A3', '-99')
    USE_TILE = True
    print(f"OK ({len(GEOJSON['features'])} feature)")
except Exception as _e:
    print(f"HIBA ({_e}) – geo choropleth fallback")

# ── HOVER SZÖVEG (minden mutatóhoz azonos) ───────────────────────────────────
hover_texts = [
    f"<b>{row['Name']} ({iso})</b><br>"
    f"Rang: #{row['rank']}<br>"
    f"Végső: {row['FINAL_SCORE_1_10']:.2f}<br>"
    f"OSCI: {row['Score_OSCI']:.2f} · Hard Power: {row['Score_HardPower']:.2f}<br>"
    f"Energia: {row['Dim_Energy']:.2f} · Nyitottság: {row['Dim_Openness']:.2f}<br>"
    f"Kohézió: {row['Dim_Cohesion']:.2f} · Demográfia: {row['Dim_Demography']:.2f}"
    for iso, row in df.iterrows()
]

# ── JS ADATOK (mutatónként z értékek) ────────────────────────────────────────
all_z_dict = {col: df[col].round(4).tolist() for col, _ in metric_list}
all_z_json      = _json.dumps(all_z_dict)
metric_keys_json = _json.dumps([col for col, _ in metric_list])
metric_labels_json = _json.dumps([lbl for _, lbl in metric_list])

# ── FIGURE: TÉRKÉP ───────────────────────────────────────────────────────────
col0, lbl0 = metric_list[0]
colorbar_cfg = dict(
    title=dict(text='Pont', font=dict(color='#e6edf3', size=11)),
    tickfont=dict(color='#e6edf3', size=10),
    bgcolor='rgba(13,17,23,0.85)',
    bordercolor='#444c56', borderwidth=1,
    thickness=14, len=0.78, x=1.0, xanchor='left',
)

if USE_TILE:
    fig_map = go.Figure(go.Choroplethmap(
        geojson=GEOJSON,
        locations=df.index.tolist(),
        z=df[col0].tolist(),
        featureidkey='properties.ISO_A3',
        text=hover_texts,
        hovertemplate='%{text}<extra></extra>',
        colorscale='RdYlGn',
        zmin=1, zmax=10,
        marker=dict(opacity=0.85, line=dict(width=0.5, color='rgba(255,255,255,0.15)')),
        showscale=True,
        colorbar=colorbar_cfg,
        name=lbl0,
    ))
    fig_map.update_layout(
        map=dict(style='carto-darkmatter', center=dict(lat=20, lon=10), zoom=0.85),
        margin=dict(t=0, b=0, l=0, r=0),
        paper_bgcolor='#0d1117',
        font=dict(color='#e6edf3', family='Segoe UI, Arial'),
        height=520,
    )
else:
    fig_map = go.Figure(go.Choropleth(
        locations=df.index.tolist(),
        z=df[col0].tolist(),
        text=hover_texts,
        hovertemplate='%{text}<extra></extra>',
        colorscale='RdYlGn',
        zmin=1, zmax=10,
        showscale=True,
        colorbar=colorbar_cfg,
        name=lbl0,
    ))
    fig_map.update_layout(
        geo=dict(
            showframe=False, projection=dict(type='mercator'),
            showcoastlines=True, coastlinecolor='#444c56',
            showland=True, landcolor='#21262d',
            showocean=True, oceancolor='#0d1117',
            showcountries=True, countrycolor='#30363d',
            bgcolor='#0d1117',
        ),
        margin=dict(t=0, b=0, l=0, r=0),
        paper_bgcolor='#0d1117',
        font=dict(color='#e6edf3', family='Segoe UI, Arial'),
        height=520,
    )

# ── FIGURE: RANGSOR (BAR) ─────────────────────────────────────────────────────
fig_bar = go.Figure()
for i, (col, label) in enumerate(metric_list):
    df_b = df.sort_values(col, ascending=True).tail(25)
    bar_colors = [REGION_COLORS.get(REGIONS.get(iso, ''), '#555') for iso in df_b.index]
    fig_bar.add_trace(go.Bar(
        x=df_b[col].tolist(),
        y=[COUNTRY_NAMES.get(iso, iso) for iso in df_b.index],
        orientation='h',
        text=[f"{v:.2f}" for v in df_b[col]],
        textposition='outside',
        hovertemplate='<b>%{y}</b>: %{x:.2f}<extra></extra>',
        marker=dict(color=bar_colors, line=dict(width=0)),
        visible=(i == 0),
        showlegend=False,
        name=label,
    ))

fig_bar.update_layout(
    height=520,
    paper_bgcolor='#161b22',
    plot_bgcolor='#161b22',
    font=dict(color='#e6edf3', family='Segoe UI, Arial'),
    margin=dict(t=10, b=45, l=10, r=70),
    xaxis=dict(
        range=[0, 12], gridcolor='#30363d', zerolinecolor='#30363d',
        tickfont=dict(color='#8b949e', size=10),
        title=dict(text=metric_list[0][1], font=dict(color='#8b949e', size=11)),
    ),
    yaxis=dict(
        automargin=True,
        tickfont=dict(color='#e6edf3', size=10),
        gridcolor='#21262d',
    ),
)

# ── FIGURE: PÓKHÁLÓ (RADAR) ──────────────────────────────────────────────────
fig_radar = go.Figure()
group_counts = []
for g_name, g_countries in RADAR_GROUPS.items():
    cnt = 0
    for j, iso in enumerate(g_countries):
        if iso not in df.index:
            continue
        row = df.loc[iso]
        vals  = [row[d] for d in RADAR_DIMS] + [row[RADAR_DIMS[0]]]
        theta = RADAR_LABELS + [RADAR_LABELS[0]]
        fig_radar.add_trace(go.Scatterpolar(
            r=vals, theta=theta, fill='toself', opacity=0.75,
            name=COUNTRY_NAMES.get(iso, iso),
            visible=(g_name == 'Top 5'),
            line=dict(color=TRACE_COLORS[j % len(TRACE_COLORS)], width=2),
            hovertemplate=f'<b>{COUNTRY_NAMES.get(iso, iso)}</b><br>%{{theta}}: %{{r:.2f}}<extra></extra>',
        ))
        cnt += 1
    group_counts.append(cnt)

total_r = sum(group_counts)
cum = [0]
for c in group_counts:
    cum.append(cum[-1] + c)

radar_btns = []
for g_idx, g_name in enumerate(RADAR_GROUPS.keys()):
    vis = [False] * total_r
    for t in range(cum[g_idx], cum[g_idx + 1]):
        vis[t] = True
    radar_btns.append(dict(label=g_name, method='update', args=[{'visible': vis}]))

fig_radar.update_layout(
    polar=dict(
        radialaxis=dict(visible=True, range=[1,10], gridcolor='#30363d',
                        linecolor='#30363d', tickfont=dict(color='#8b949e', size=9)),
        angularaxis=dict(gridcolor='#30363d', linecolor='#444c56',
                         tickfont=dict(color='#e6edf3', size=12)),
        bgcolor='#161b22',
    ),
    paper_bgcolor='#161b22',
    font=dict(color='#e6edf3', family='Segoe UI, Arial'),
    legend=dict(bgcolor='#0d1117', bordercolor='#30363d', borderwidth=1, font=dict(size=11)),
    updatemenus=[dict(
        active=0, buttons=radar_btns, direction='down', x=0.0, y=1.2,
        showactive=True, bgcolor='#21262d', bordercolor='#58a6ff',
        font=dict(color='#e6edf3', size=12),
    )],
    height=460,
    margin=dict(t=80, b=20, l=60, r=60),
)

# ── FIGURE: SCATTER BUBBLE ───────────────────────────────────────────────────
fig_scatter = go.Figure()
for region in sorted(df['Region'].unique()):
    sub = df[df['Region'] == region].copy()
    sizes = ((sub['HP_GDP'] - 1) / 9 * 44 + 9).tolist()
    fig_scatter.add_trace(go.Scatter(
        x=sub['Score_HardPower'], y=sub['Score_OSCI'],
        mode='markers+text', name=region,
        text=sub.index,
        textposition='top center',
        textfont=dict(size=8, color='rgba(180,180,180,0.65)'),
        hovertemplate=(
            '<b>%{customdata[0]}</b><br>'
            'Végső: %{customdata[1]:.2f} (#%{customdata[2]})<br>'
            'Hard Power: %{x:.2f} · OSCI: %{y:.2f}<br>'
            'Energia: %{customdata[3]:.2f} · Nyitottság: %{customdata[4]:.2f}<br>'
            'Kohézió: %{customdata[5]:.2f} · Demográfia: %{customdata[6]:.2f}'
            '<extra></extra>'
        ),
        customdata=sub[['Name','FINAL_SCORE_1_10','rank',
                        'Dim_Energy','Dim_Openness','Dim_Cohesion','Dim_Demography']].values,
        marker=dict(size=sizes, color=REGION_COLORS.get(region,'#888'),
                    opacity=0.85, line=dict(color='rgba(255,255,255,0.25)', width=1)),
    ))

fig_scatter.add_shape(type='line', x0=1, y0=1, x1=10, y1=10,
    line=dict(color='#30363d', dash='dot', width=1.5))
for x, y, txt in [(2.2,9.2,'Soft Power dominál'),(7.5,1.8,'Hard Power dominál'),
                   (7.8,9.2,'Globális Hatalom'),(1.8,1.8,'Fejlődő')]:
    fig_scatter.add_annotation(x=x, y=y, text=txt, showarrow=False,
        font=dict(color='#444c56', size=10))

fig_scatter.update_layout(
    paper_bgcolor='#161b22', plot_bgcolor='#0d1117',
    font=dict(color='#e6edf3', family='Segoe UI, Arial'),
    xaxis=dict(title='Hard Power (1–10)', range=[0.5,10.8],
               gridcolor='#21262d', zerolinecolor='#21262d', tickfont=dict(color='#8b949e')),
    yaxis=dict(title='OSCI (1–10)', range=[0.5,10.8],
               gridcolor='#21262d', zerolinecolor='#21262d', tickfont=dict(color='#8b949e')),
    legend=dict(bgcolor='#0d1117', bordercolor='#30363d', borderwidth=1, font=dict(size=11)),
    height=490, margin=dict(t=20, b=50, l=60, r=20),
)

# ── HTML ÖSSZEÁLLÍTÁS ─────────────────────────────────────────────────────────
cfg = {'responsive': True, 'displayModeBar': True, 'displaylogo': False,
       'modeBarButtonsToRemove': ['select2d', 'lasso2d']}

f_map     = fig_map.to_html(full_html=False, include_plotlyjs=False, div_id='map-fig', config=cfg)
f_bar     = fig_bar.to_html(full_html=False, include_plotlyjs=False, div_id='bar-fig', config=cfg)
f_radar   = fig_radar.to_html(full_html=False, include_plotlyjs=False, div_id='radar-fig', config=cfg)
f_scatter = fig_scatter.to_html(full_html=False, include_plotlyjs=False, div_id='scatter-fig', config=cfg)

select_options = "\n".join(
    f'      <option value="{i}">{lbl}</option>'
    for i, (_, lbl) in enumerate(metric_list)
)

# JS adatok külön (json { } karaktereket tartalmaz, placeholder-rel adjuk hozzá)
js_data_block = (
    "var METRIC_KEYS = " + metric_keys_json + ";\n"
    "var METRIC_LABELS = " + metric_labels_json + ";\n"
    "var ALL_Z = " + all_z_json + ";\n"
    "var N_METRICS = " + str(n) + ";\n"
)

html = f"""<!DOCTYPE html>
<html lang="hu">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Geopolitikai Erő Dashboard</title>
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: #0d1117;
      color: #e6edf3;
      font-family: 'Segoe UI', Arial, sans-serif;
      padding: 20px 24px;
    }}
    header {{ text-align: center; margin-bottom: 20px; }}
    header h1 {{
      font-size: 27px; font-weight: 700;
      background: linear-gradient(90deg, #58a6ff 0%, #3fb950 100%);
      -webkit-background-clip: text; -webkit-text-fill-color: transparent;
      background-clip: text; letter-spacing: 0.4px;
    }}
    header p {{ color: #8b949e; font-size: 13px; margin-top: 6px; }}

    .selector-bar {{
      display: flex; align-items: center; gap: 14px;
      background: #161b22; border: 1px solid #30363d; border-radius: 10px;
      padding: 10px 18px; margin-bottom: 16px;
    }}
    .selector-bar span {{ color: #8b949e; font-size: 12px; font-weight: 600;
      text-transform: uppercase; letter-spacing: 0.8px; white-space: nowrap; }}
    select#metric-sel {{
      background: #21262d; color: #e6edf3;
      border: 1px solid #58a6ff; border-radius: 6px;
      padding: 7px 14px; font-size: 14px; cursor: pointer;
      outline: none; flex: 1; max-width: 340px;
    }}
    select#metric-sel:hover {{ border-color: #79c0ff; }}
    .zoom-hint {{
      margin-left: auto; color: #6e7681; font-size: 11px;
      background: #21262d; border-radius: 5px; padding: 4px 10px;
      border: 1px solid #30363d; white-space: nowrap;
    }}

    .map-bar-row {{
      display: grid; grid-template-columns: 3fr 2fr;
      gap: 16px; margin-bottom: 16px;
    }}
    .card {{
      background: #161b22; border: 1px solid #30363d;
      border-radius: 12px; padding: 14px 14px 6px; overflow: hidden;
    }}
    .card-title {{
      font-size: 10px; color: #58a6ff; font-weight: 600;
      text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;
    }}
    .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
    footer {{ text-align: center; color: #30363d; font-size: 11px; margin-top: 12px; }}
    @media (max-width: 960px) {{
      .map-bar-row, .grid-2 {{ grid-template-columns: 1fr; }}
      .meth-grid {{ grid-template-columns: 1fr; }}
      .pillars {{ grid-template-columns: 1fr 1fr; }}
    }}

    /* ── Módszertan szekció ── */
    .meth-section {{ cursor: default; }}
    .meth-toggle {{
      display: flex; align-items: center; justify-content: space-between;
      cursor: pointer; padding: 4px 0; user-select: none;
    }}
    .meth-toggle:hover .card-title {{ color: #79c0ff; }}
    .meth-arrow {{
      color: #58a6ff; font-size: 14px; transition: transform 0.3s;
    }}
    .meth-section.open .meth-arrow {{ transform: rotate(180deg); }}
    .meth-content {{
      display: none; margin-top: 18px;
    }}
    .meth-section.open .meth-content {{ display: block; }}
    .meth-grid {{
      display: grid; grid-template-columns: 1fr 1fr;
      gap: 20px; margin-bottom: 16px;
    }}
    .meth-block h3 {{
      color: #58a6ff; font-size: 13px; font-weight: 600;
      margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.5px;
    }}
    .meth-block p, .meth-block li {{
      color: #c9d1d9; font-size: 13px; line-height: 1.65;
    }}
    .meth-block ul {{
      padding-left: 18px; margin: 6px 0;
    }}
    .meth-block li {{ margin-bottom: 4px; }}
    .score-formula {{
      display: flex; align-items: stretch; gap: 10px;
      margin: 12px 0;
    }}
    .formula-item {{
      flex: 1; border-radius: 8px; padding: 12px;
      display: flex; flex-direction: column; gap: 4px;
    }}
    .formula-item.osci {{ background: rgba(88,166,255,0.1); border: 1px solid rgba(88,166,255,0.3); }}
    .formula-item.hard {{ background: rgba(63,185,80,0.1); border: 1px solid rgba(63,185,80,0.3); }}
    .formula-pct {{ font-size: 26px; font-weight: 700; }}
    .formula-item.osci .formula-pct {{ color: #58a6ff; }}
    .formula-item.hard .formula-pct {{ color: #3fb950; }}
    .formula-name {{ font-size: 12px; font-weight: 600; color: #e6edf3; }}
    .formula-desc {{ font-size: 11.5px; color: #8b949e; line-height: 1.5; }}
    .formula-plus {{ color: #444c56; font-size: 24px; align-self: center; }}
    .pillars {{
      display: grid; grid-template-columns: 1fr 1fr;
      gap: 10px; margin-top: 10px;
    }}
    .pillar {{
      background: #0d1117; border: 1px solid #30363d;
      border-radius: 8px; padding: 10px; font-size: 12px;
    }}
    .pillar-icon {{ font-size: 18px; display: block; margin-bottom: 4px; }}
    .pillar strong {{ color: #e6edf3; display: block; margin-bottom: 4px; font-size: 12px; }}
    .pillar p {{ color: #8b949e; font-size: 11.5px; line-height: 1.5; }}
    .formula-box {{
      background: #0d1117; border: 1px solid #58a6ff;
      border-radius: 8px; padding: 12px 16px; text-align: center;
      font-size: 15px; font-weight: 600; color: #79c0ff;
      margin: 10px 0; letter-spacing: 0.3px;
    }}
    .meth-footer {{
      border-top: 1px solid #30363d; padding-top: 14px; margin-top: 4px;
    }}
    .meth-footer p {{ color: #8b949e; font-size: 13px; line-height: 1.7; }}
    .meth-footer strong {{ color: #e6edf3; }}
    .meth-footer em {{ color: #58a6ff; font-style: normal; }}
  </style>
</head>
<body>

<header>
  <h1>Geopolitikai Erő Dashboard</h1>
  <p>{n_countries} ország &nbsp;·&nbsp; World Bank (WDI) adatok &nbsp;·&nbsp; OSCI Geopolitikai Index</p>
</header>

<div class="selector-bar">
  <span>Mutató:</span>
  <select id="metric-sel">
{select_options}
  </select>
  <div class="zoom-hint">Térkép: görgetés = zoom &nbsp;·&nbsp; húzás = mozgás</div>
</div>

<div class="map-bar-row">
  <div class="card">
    <div class="card-title">Interaktív Térkép</div>
    {f_map}
  </div>
  <div class="card">
    <div class="card-title">TOP 25 Rangsor</div>
    {f_bar}
  </div>
</div>

<div class="grid-2">
  <div class="card">
    <div class="card-title">Dimenzió összehasonlítás – Pókháló</div>
    {f_radar}
  </div>
  <div class="card">
    <div class="card-title">OSCI vs Hard Power &nbsp;(buborék ≈ GDP)</div>
    {f_scatter}
  </div>
</div>

<!-- Módszertan szekció -->
<div class="card meth-section" style="margin-top: 16px;" id="meth-card">
  <div class="meth-toggle" onclick="document.getElementById('meth-card').classList.toggle('open')">
    <div class="card-title" style="margin-bottom:0;">Módszertan &amp; Magyarázat az Indexhez</div>
    <span class="meth-arrow">▼</span>
  </div>
  <div class="meth-content">
    <div class="meth-grid">
      <div class="meth-block">
        <h3>1. Az Alapelv: Birodalmak Anatómiája</h3>
        <p>Prof. Jiang Xueqin strukturális történelemelemzése szerint a nagy birodalmak szinte soha nem külső katonai vereség miatt omlanak össze. A vesztüket mindig a <strong style="color:#e6edf3;">belső elkorhadás</strong> okozza:</p>
        <ul style="margin-top:8px;">
          <li><strong style="color:#e6edf3;">A Gőg (Hubris):</strong> Túlterjeszkednek, mert öröknek hiszik a hatalmukat.</li>
          <li><strong style="color:#e6edf3;">Az Elit Kisajátítása:</strong> A gazdaságot "pilótajátékká" változtatják, lezárva a felemelkedés útját.</li>
          <li><strong style="color:#e6edf3;">A Cél Elvesztése:</strong> A társadalom megosztottá válik, a fenntartás költségei fenntarthatatlanná válnak.</li>
        </ul>
        <p style="margin-top:10px;">A modell nem dől be annak, hogy <em>"annál erősebb vagy, minél több pénzed és tankod van"</em> – egy belülről egészséges ellenfél egyszerűen <strong style="color:#58a6ff;">túléli</strong> az izmos óriást.</p>
      </div>
      <div class="meth-block">
        <h3>2. A 65/35-ös Súlyozás</h3>
        <p>A végső pontszámot két nagy tömbből számítjuk, az arány mindennél fontosabb:</p>
        <div class="score-formula">
          <div class="formula-item osci">
            <span class="formula-pct">65%</span>
            <span class="formula-name">OSCI – Belső Vitalitás</span>
            <span class="formula-desc">A társadalom "lelke" és immunrendszere. Megmutatja, hogy felszálló, érett vagy hanyatló fázisban van-e a birodalom.</span>
          </div>
          <div class="formula-plus">+</div>
          <div class="formula-item hard">
            <span class="formula-pct">35%</span>
            <span class="formula-name">Hard Power – Nyers Erő</span>
            <span class="formula-desc">A fizikai izomzat: GDP méret, katonai elrettentés, földrajzi adottságok. Belső életerő nélkül önmagában mit sem ér.</span>
          </div>
        </div>
      </div>
      <div class="meth-block">
        <h3>3. Az OSCI 4 Pillére (Világbank adatok)</h3>
        <div class="pillars">
          <div class="pillar">
            <span class="pillar-icon">⚡</span>
            <strong>Energia &amp; Innováció</strong>
            <p>Szabadalmak, K+F kiadás, ifjúsági aktivitás – a társadalom "agyát" méri. Találja meg a "Spártai Tech-államokat" (pl. Izrael, Dél-Korea).</p>
          </div>
          <div class="pillar">
            <span class="pillar-icon">🔓</span>
            <strong>Nyitottság (Társadalmi Lift)</strong>
            <p>Vállalkozásindítás nehézsége, a Top 10% vagyonkisajátítása, diplomások elhelyezkedési esélye.</p>
          </div>
          <div class="pillar">
            <span class="pillar-icon">🤝</span>
            <strong>Kohézió (Összetartás)</strong>
            <p>Gini-index (vagyonegyenlőség) és gyilkossági ráták – bízhatsz-e a honfitársadban?</p>
          </div>
          <div class="pillar">
            <span class="pillar-icon">👶</span>
            <strong>Demográfia (Biológiai Jövő)</strong>
            <p>Születési ráták. Prof. Jiang szerint egy kihaló társadalom automatikusan kiesik a történelem formálói közül.</p>
          </div>
        </div>
      </div>
      <div class="meth-block">
        <h3>4. A "Gyenge Láncszem" Elve</h3>
        <p>Az OSCI-t <strong style="color:#e6edf3;">geometriai átlaggal</strong> számítjuk, nem szimpla átlaggal:</p>
        <div class="formula-box">OSCI = ∜(Energia × Nyitottság × Kohézió × Demográfia)</div>
        <p>Ha a 4 pillérből akár csak <em>egyetlen egy</em> is közelít a nullához, az egész pontszám összeomlik – nem lehet zseniális tech-iparral eltakarni egy kihaló demográfiát.</p>
        <h3 style="margin-top:16px;">5. A Hard Power Összetevői</h3>
        <ul>
          <li><strong style="color:#e6edf3;">GDP (25%) + Népesség (20%):</strong> A puszta méret.</li>
          <li><strong style="color:#e6edf3;">Aszimmetrikus Katonai Erő (25%):</strong> Katonai kiadás × K+F – nem a tankok száma, hanem a csúcstechnológia.</li>
          <li><strong style="color:#e6edf3;">Földrajz (20%):</strong> Ivóvíz + termőföld – az önellátás képessége. (Jutalmazza Oroszországot és Kazahsztánt, bünteti Európát.)</li>
          <li><strong style="color:#e6edf3;">Energiafüggetlenség (10%):</strong> Túlélöd-e, ha elzárják az olajcsapokat?</li>
        </ul>
      </div>
    </div>
    <div class="meth-footer">
      <p><strong>Hogyan értelmezd a listát?</strong> Ne a mai nap gazdasági rangsorát keresd benne – ez egy <em>jövőkutatói jelentés</em> a következő évtizedekre. Ha egy ma domináns hatalom lejjebb csúszik (pl. USA, Nyugat-Európa), az nem holnapi összeomlást jelent, hanem azt, hogy hanyatlásuk strukturálisan megkezdődött. <strong>Ez a mátrix a türelmesek és az egészségesek játéka</strong> – pontosan úgy, ahogy azt a történelem nagy birodalmai már oly sokszor bebizonyították.</p>
    </div>
  </div>
</div>

<footer>Adatforrás: World Bank WDI &nbsp;·&nbsp; Generálva: geo76.py + dashboard.py</footer>

<script>
__JS_DATA__

document.getElementById('metric-sel').addEventListener('change', function() {{
  var idx = parseInt(this.value, 10);
  var key = METRIC_KEYS[idx];

  // Térkép: csak z értékek frissítése (GeoJSON és hover szöveg marad)
  Plotly.restyle('map-fig', {{ z: [ALL_Z[key]] }});

  // Rangsor: trace váltás (minden mutatónak saját rendezett trace-e van)
  var barVis = Array(N_METRICS).fill(false);
  barVis[idx] = true;
  Plotly.restyle('bar-fig', {{ visible: barVis }});

  // Bar x tengely cím frissítése
  Plotly.relayout('bar-fig', {{ 'xaxis.title.text': METRIC_LABELS[idx] }});
}});
</script>

</body>
</html>"""

html = html.replace("__JS_DATA__", js_data_block)

with open(OUTPUT_HTML, 'w', encoding='utf-8') as fh:
    fh.write(html)

print(f"Dashboard mentve: {OUTPUT_HTML}")
print("Elérési út: " + os.path.abspath(OUTPUT_HTML))
