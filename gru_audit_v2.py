'''
Energy Audit Analyzer v3.0
Professional energy consumption analysis tool for auditors.

Features:

- Multi-utility support (Electric, Water, Gas) with dynamic tabs
- Temperature correlation analysis
- Cross-utility correlation with scatter plots
- Auditor advice based on patterns
- Dark/Light mode toggle
- Enhanced responsive design
- Flexible AMI format detection
- PDF report export

Author: Energy Audit Tools
'''

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.backends.backend_pdf import PdfPages
from scipy import stats
from sklearn.ensemble import IsolationForest
import requests
import io
import re
import warnings
from datetime import datetime

warnings.filterwarnings(‘ignore’)

# ═══════════════════════════════════════════════════════════════════════════════

# PAGE CONFIG & THEME

# ═══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
page_title=“Energy Audit Analyzer”,
page_icon=“E”,
layout=“wide”,
initial_sidebar_state=“expanded”
)

# Initialize theme in session state

if “dark_mode” not in st.session_state:
st.session_state.dark_mode = False

def get_theme_colors():
“”“Get colors based on current theme.”””
if st.session_state.dark_mode:
return {
“bg”: “#1a1a2e”,
“card_bg”: “#16213e”,
“text”: “#eaeaea”,
“text_secondary”: “#a0a0a0”,
“primary”: “#4fc3f7”,
“secondary”: “#81d4fa”,
“accent”: “#ffb74d”,
“success”: “#81c784”,
“warning”: “#ffb74d”,
“danger”: “#e57373”,
“chart_bg”: “#1a1a2e”,
“grid”: “#333355”,
}
else:
return {
“bg”: “#f8f9fa”,
“card_bg”: “#ffffff”,
“text”: “#1e3a5f”,
“text_secondary”: “#6c757d”,
“primary”: “#1e3a5f”,
“secondary”: “#3498db”,
“accent”: “#e67e22”,
“success”: “#27ae60”,
“warning”: “#f39c12”,
“danger”: “#c0392b”,
“chart_bg”: “#ffffff”,
“grid”: “#e0e0e0”,
}

def apply_theme():
“”“Apply CSS based on current theme.”””
colors = get_theme_colors()

```
st.markdown(f"""
<style>
    .stApp {{
        background-color: {colors["bg"]};
    }}
    [data-testid="stSidebar"] {{
        background-color: {colors["card_bg"]};
    }}
    h1, h2, h3 {{
        color: {colors["text"]};
    }}
    p, span, label {{
        color: {colors["text"]};
    }}
    .info-box {{
        background-color: {"#1e3a5f22" if st.session_state.dark_mode else "#e8f4fd"};
        border-left: 4px solid {colors["secondary"]};
        padding: 15px;
        margin: 15px 0;
        border-radius: 0 8px 8px 0;
        color: {colors["text"]};
    }}
    .warning-box {{
        background-color: {"#f39c1222" if st.session_state.dark_mode else "#fef9e7"};
        border-left: 4px solid {colors["warning"]};
        padding: 15px;
        margin: 15px 0;
        border-radius: 0 8px 8px 0;
        color: {colors["text"]};
    }}
    .success-box {{
        background-color: {"#27ae6022" if st.session_state.dark_mode else "#eafaf1"};
        border-left: 4px solid {colors["success"]};
        padding: 15px;
        margin: 15px 0;
        border-radius: 0 8px 8px 0;
        color: {colors["text"]};
    }}
    .danger-box {{
        background-color: {"#c0392b22" if st.session_state.dark_mode else "#fdedec"};
        border-left: 4px solid {colors["danger"]};
        padding: 15px;
        margin: 15px 0;
        border-radius: 0 8px 8px 0;
        color: {colors["text"]};
    }}
    .metric-card {{
        background-color: {colors["card_bg"]};
        border: 1px solid {colors["grid"]};
        border-radius: 8px;
        padding: 15px;
        text-align: center;
    }}
    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px;
    }}
    .stTabs [data-baseweb="tab"] {{
        background-color: {colors["card_bg"]};
        border-radius: 4px;
        padding: 8px 16px;
    }}
    /* Responsive adjustments */
    @media (max-width: 768px) {{
        .row-widget.stHorizontalBlock {{
            flex-direction: column;
        }}
        .row-widget.stHorizontalBlock > div {{
            width: 100% !important;
            margin-bottom: 1rem;
        }}
    }}
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
</style>
""", unsafe_allow_html=True)
```

def info_box(text, box_type=“info”):
st.markdown(f’<div class="{box_type}-box">{text}</div>’, unsafe_allow_html=True)

def setup_chart_style():
“”“Configure matplotlib for current theme.”””
colors = get_theme_colors()

```
plt.rcParams.update({
    'figure.facecolor': colors["chart_bg"],
    'axes.facecolor': colors["chart_bg"],
    'axes.edgecolor': colors["grid"],
    'axes.labelcolor': colors["text"],
    'text.color': colors["text"],
    'xtick.color': colors["text"],
    'ytick.color': colors["text"],
    'grid.color': colors["grid"],
    'grid.alpha': 0.3,
    'font.size': 10,
    'axes.titlesize': 12,
    'axes.titleweight': 'bold',
    'axes.spines.top': False,
    'axes.spines.right': False,
})
```

# ═══════════════════════════════════════════════════════════════════════════════

# MASTER SHEET INFO

# ═══════════════════════════════════════════════════════════════════════════════

def get_master_sheet_info(file_obj):
“”“Extract customer information from Master Sheet.”””
try:
ms = pd.read_excel(file_obj, sheet_name=“Master Sheet”, header=None)

```
    def safe_get(row, col):
        try:
            val = ms.iloc[row, col]
            return str(val).strip() if pd.notna(val) else None
        except:
            return None
    
    row_offset = 0
    cell_0_6 = safe_get(0, 6)
    if cell_0_6 and not any(c.isdigit() for c in str(cell_0_6)):
        row_offset = 1
    
    def get(row, col):
        return safe_get(row + row_offset, col)
    
    info = {
        "account": get(0, 6),
        "customer_name": get(1, 6),
        "address": get(4, 6),
        "city_town": get(5, 6),
        "survey_date": get(7, 2),
    }
    
    if info["survey_date"] and "00:00:00" in str(info["survey_date"]):
        try:
            info["survey_date"] = pd.to_datetime(info["survey_date"]).strftime("%m/%d/%Y")
        except:
            pass
    
    return info
except:
    return {}
```

# ═══════════════════════════════════════════════════════════════════════════════

# METER LOADER

# ═══════════════════════════════════════════════════════════════════════════════

class MeterLoader:
“”“Load and clean meter consumption data.”””

```
COLUMN_MAP = {
    "Division": "division", "Device": "device", "MR Reason": "mr_reason",
    "MR Type": "mr_type", "MR Date": "mr_date", "Days": "days",
    "MR Result": "mr_result", "MR Unit": "mr_unit", "Consumption": "consumption",
    "Avg.": "avg_daily", "Avg": "avg_daily",
}

NON_READ_REASONS = {3}
VLINE_REASONS = {6, 21, 22}

def __init__(self, file_obj):
    self.file_obj = file_obj
    self.df = None
    self.has_mr_reason = False

def _find_sheet(self, xl):
    for name in xl.sheet_names:
        if "consumption" in name.lower():
            return name
    raise ValueError(f"No consumption sheet found. Sheets: {xl.sheet_names}")

def _find_header_row(self, xl, sheet):
    for i in range(5):
        df = pd.read_excel(xl, sheet_name=sheet, header=i, nrows=1)
        df.columns = df.columns.str.strip()
        if "Division" in df.columns:
            return i
    return 0

def load_and_clean(self):
    xl = pd.ExcelFile(self.file_obj)
    sheet = self._find_sheet(xl)
    header_row = self._find_header_row(xl, sheet)
    
    df = pd.read_excel(xl, sheet_name=sheet, header=header_row)
    df.columns = df.columns.str.strip()
    df = df.rename(columns=self.COLUMN_MAP)
    
    self.has_mr_reason = "mr_reason" in df.columns
    
    df["mr_date"] = pd.to_datetime(df["mr_date"], errors="coerce")
    
    if "consumption" in df.columns:
        if df["consumption"].dtype == object:
            df["consumption"] = df["consumption"].astype(str).str.replace(",", "")
        df["consumption"] = pd.to_numeric(df["consumption"], errors="coerce")
    
    for col in ["days", "avg_daily"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    
    df = df.dropna(subset=["mr_date"])
    
    if self.has_mr_reason:
        df["mr_reason"] = pd.to_numeric(df["mr_reason"], errors="coerce")
        df = df[~df["mr_reason"].isin(self.NON_READ_REASONS)]
        df = df[(df["consumption"] > 0) | (df["mr_reason"].isin(self.VLINE_REASONS))]
    else:
        df = df[df["consumption"] > 0]
    
    df = df[df["days"] > 0]
    df = df.sort_values(["division", "mr_date"]).reset_index(drop=True)
    self.df = df
    return df

def get_division(self, name):
    if self.df is None:
        return pd.DataFrame()
    sub = self.df[self.df["division"] == name].copy()
    if not sub.empty:
        sub = sub[sub["mr_date"] > sub["mr_date"].min()].reset_index(drop=True)
    return sub

def get_available_divisions(self):
    if self.df is None:
        return []
    return self.df["division"].unique().tolist()
```

# ═══════════════════════════════════════════════════════════════════════════════

# METER FEATURES & GRAPHS

# ═══════════════════════════════════════════════════════════════════════════════

class MeterFeatures:
def **init**(self, df):
self.df = df.copy().sort_values(“mr_date”).reset_index(drop=True)

```
def compute_features(self):
    df = self.df
    
    total_consumption = df["consumption"].sum()
    total_days = df["days"].sum()
    overall_daily_avg = total_consumption / total_days if total_days > 0 else None
    peak_consumption = df["consumption"].max()
    
    period_series = df.set_index("mr_date")["consumption"]
    rolling_avg = period_series.rolling(window=3, min_periods=1).mean()
    daily_avg_series = df.set_index("mr_date")["avg_daily"] if "avg_daily" in df.columns else None
    
    iso_cols = [c for c in ["consumption", "days", "avg_daily"] if c in df.columns]
    iso_data = df[iso_cols].dropna()
    df["anomaly"] = False
    if len(iso_data) >= 5:
        preds = IsolationForest(contamination=0.05, random_state=42).fit_predict(iso_data)
        df.loc[iso_data.index, "anomaly"] = (preds == -1)
    
    n_anomalies = int(df["anomaly"].sum())
    unit = df["mr_unit"].iloc[0] if "mr_unit" in df.columns else ""
    
    return {
        "total_consumption": total_consumption,
        "overall_daily_avg": overall_daily_avg,
        "peak_consumption": peak_consumption,
        "period_series": period_series,
        "rolling_avg": rolling_avg,
        "daily_avg_series": daily_avg_series,
        "df_with_anomalies": df,
        "n_anomalies": n_anomalies,
        "unit": unit,
    }
```

class MeterGraphs:
def **init**(self, feats, title_prefix=””):
self.feats = feats
self.prefix = title_prefix
self.df = feats[“df_with_anomalies”]

```
def _add_markers(self, ax):
    if "mr_reason" not in self.df.columns:
        return
    df = self.df
    move_ins = df[df["mr_reason"] == 6]
    first = True
    for _, row in move_ins.iterrows():
        ax.axvline(x=row["mr_date"], color="dodgerblue", linewidth=1.8, 
                  linestyle="--", alpha=0.9, label="Move-In" if first else "_")
        first = False

def plot_consumption(self):
    colors = get_theme_colors()
    setup_chart_style()
    
    df_plot = self.df[self.df["consumption"] > 0]
    s = df_plot.set_index("mr_date")["consumption"]
    
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.bar(s.index, s.values, width=20, color=colors["secondary"], alpha=0.85)
    self._add_markers(ax)
    ax.set_title(f"{self.prefix} - Consumption per Billing Period")
    ax.set_ylabel(self.feats["unit"])
    ax.legend()
    fig.autofmt_xdate()
    plt.tight_layout()
    return fig

def plot_rolling_average(self):
    colors = get_theme_colors()
    setup_chart_style()
    
    df_plot = self.df[self.df["consumption"] > 0]
    s = df_plot.set_index("mr_date")["consumption"]
    r = s.rolling(window=3, min_periods=1).mean()
    
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(s.index, s.values, color=colors["secondary"], alpha=0.4, linewidth=1.5, label="Consumption")
    ax.plot(r.index, r.values, color=colors["danger"], linewidth=2.5, label="3-Period Rolling Avg")
    self._add_markers(ax)
    ax.set_title(f"{self.prefix} - Consumption Trend")
    ax.set_ylabel(self.feats["unit"])
    ax.legend()
    fig.autofmt_xdate()
    plt.tight_layout()
    return fig

def plot_anomalies(self):
    colors = get_theme_colors()
    setup_chart_style()
    
    df = self.df[self.df["consumption"] > 0]
    normal = df[~df["anomaly"]]
    anomaly = df[df["anomaly"]]
    
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.bar(normal["mr_date"], normal["consumption"], width=20, color=colors["secondary"], alpha=0.85, label="Normal")
    ax.bar(anomaly["mr_date"], anomaly["consumption"], width=20, color=colors["danger"], alpha=0.9, label="Anomaly")
    self._add_markers(ax)
    ax.set_title(f"{self.prefix} - Anomaly Detection")
    ax.set_ylabel(self.feats["unit"])
    ax.legend()
    fig.autofmt_xdate()
    plt.tight_layout()
    return fig
```

# ═══════════════════════════════════════════════════════════════════════════════

# AMI LOADER - Flexible multi-format, multi-utility support

# ═══════════════════════════════════════════════════════════════════════════════

class AMILoader:
“”“Load AMI data with flexible format detection and multi-utility support.”””

```
UTILITY_KEYWORDS = {
    "Electric": ["electric", "elec", "kwh", "wh"],
    "Water": ["water", "gal", "gallon"],
    "Gas": ["gas", "ccf", "therm"],
}

UNITS = {"Electric": "kWh", "Water": "Gal", "Gas": "CCF"}

def __init__(self, file_obj):
    self.file_obj = file_obj
    self.utilities = {}  # {utility_name: {"df": df, "unit": unit}}
    self.customer_info = {}

def _detect_utility_from_sheet(self, sheet_name):
    sheet_lower = sheet_name.lower()
    for util, keywords in self.UTILITY_KEYWORDS.items():
        if any(kw in sheet_lower for kw in keywords):
            return util
    return None

def _parse_value(self, val_str):
    """Parse value like '1,862.000 Wh Del' or '25.400 GAL'."""
    if pd.isna(val_str):
        return None, None
    
    val_str = str(val_str).strip()
    
    # Extract numeric part
    numeric_match = re.search(r'[\d,]+\.?\d*', val_str)
    if not numeric_match:
        return None, None
    
    numeric = float(numeric_match.group().replace(',', ''))
    
    # Detect unit and convert
    val_upper = val_str.upper()
    if 'WH' in val_upper and 'KWH' not in val_upper:
        return numeric / 1000, "kWh"  # Convert Wh to kWh
    elif 'KWH' in val_upper:
        return numeric, "kWh"
    elif 'GAL' in val_upper:
        return numeric, "Gal"
    elif 'CCF' in val_upper or 'THERM' in val_upper:
        return numeric, "CCF"
    else:
        return numeric, None

def _parse_timestamp(self, ts_str):
    """Parse various timestamp formats."""
    if pd.isna(ts_str):
        return None
    
    ts_str = str(ts_str).strip()
    
    # Remove timezone
    for tz in [" EST", " EDT", " CST", " CDT", " PST", " PDT"]:
        ts_str = ts_str.replace(tz, "")
    
    # Format: "Feb 25, 2026 - 12:00 am"
    if " - " in ts_str:
        ts_str = ts_str.replace(" - ", " ")
    
    try:
        return pd.to_datetime(ts_str)
    except:
        return None

def _load_sheet(self, xl, sheet_name):
    """Load a single sheet with flexible format detection."""
    df_raw = pd.read_excel(xl, sheet_name=sheet_name, header=None)
    
    # Find where data starts (skip customer info rows)
    data_start = 0
    for i in range(min(10, len(df_raw))):
        row = df_raw.iloc[i]
        # Check if row looks like data (has a parseable timestamp)
        if self._parse_timestamp(row.iloc[0]) is not None:
            data_start = i
            break
        # Extract customer info from header rows
        row_str = str(row.iloc[0]) if pd.notna(row.iloc[0]) else ""
        if "METER #" in row_str.upper():
            self.customer_info["meter"] = row_str
        elif any(c.isdigit() for c in row_str) and len(row_str) > 10:
            if "customer_name" not in self.customer_info:
                self.customer_info["customer_name"] = row_str
    
    # Parse data rows
    timestamps = []
    values = []
    detected_unit = None
    
    for i in range(data_start, len(df_raw)):
        row = df_raw.iloc[i]
        
        ts = self._parse_timestamp(row.iloc[0])
        if ts is None:
            continue
        
        # Value might be in column 1 or combined with timestamp
        if len(row) > 1 and pd.notna(row.iloc[1]):
            val, unit = self._parse_value(row.iloc[1])
        else:
            val, unit = self._parse_value(row.iloc[0])
        
        if val is not None:
            timestamps.append(ts)
            values.append(val)
            if unit and detected_unit is None:
                detected_unit = unit
    
    if not timestamps:
        return None, None
    
    df = pd.DataFrame({"timestamp": timestamps, "value": values})
    df = df.sort_values("timestamp").reset_index(drop=True)
    
    return df, detected_unit

def load(self):
    """Load all utilities from the AMI file."""
    xl = pd.ExcelFile(self.file_obj)
    
    for sheet in xl.sheet_names:
        util_type = self._detect_utility_from_sheet(sheet)
        if util_type is None:
            # Try to detect from content
            util_type = "Electric"  # Default
        
        df, detected_unit = self._load_sheet(xl, sheet)
        
        if df is not None and len(df) > 0:
            unit = detected_unit or self.UNITS.get(util_type, "kWh")
            
            # Adjust utility type based on detected unit
            if detected_unit == "Gal":
                util_type = "Water"
            elif detected_unit == "CCF":
                util_type = "Gas"
            
            self.utilities[util_type] = {
                "df": df,
                "unit": unit,
                "sheet": sheet,
            }
    
    return self.utilities

def get_available_utilities(self):
    return list(self.utilities.keys())
```

# ═══════════════════════════════════════════════════════════════════════════════

# AMI FEATURES

# ═══════════════════════════════════════════════════════════════════════════════

class AMIFeatures:
def **init**(self, df, unit=“kWh”):
self.df = df.copy()
self.unit = unit

```
def compute(self):
    df = self.df.sort_values("timestamp")
    
    deltas = df["timestamp"].diff().dropna()
    if len(deltas) > 0:
        interval = deltas.mode()[0]
        interval_minutes = int(interval.total_seconds() / 60)
    else:
        interval_minutes = 60
    
    base_load = df["value"].quantile(0.05)
    peak_val = df["value"].max()
    
    df["date"] = df["timestamp"].dt.date
    daily_series = df.groupby("date")["value"].sum()
    daily_avg = daily_series.mean()
    
    df["hour"] = df["timestamp"].dt.hour
    avg_by_hour = df.groupby("hour")["value"].mean()
    
    # Load factor
    total_val = df["value"].sum()
    hours = len(df) * interval_minutes / 60
    avg_demand = total_val / hours if hours > 0 else 0
    peak_rate = peak_val / (interval_minutes / 60) if interval_minutes > 0 else peak_val
    load_factor = avg_demand / peak_rate if peak_rate > 0 else 0
    
    return {
        "interval_minutes": interval_minutes,
        "base_load": base_load,
        "peak_val": peak_val,
        "daily_avg": daily_avg,
        "daily_series": daily_series,
        "avg_by_hour": avg_by_hour,
        "load_factor": load_factor,
        "df": df,
        "unit": self.unit,
    }
```

# ═══════════════════════════════════════════════════════════════════════════════

# TEMPERATURE FUNCTIONS

# ═══════════════════════════════════════════════════════════════════════════════

GAINESVILLE_LAT = 29.6516
GAINESVILLE_LON = -82.3248
COMFORT_BASELINE = 65

@st.cache_data(ttl=3600)
def get_temperature_data(start_date, end_date):
“”“Fetch temperature data from Open-Meteo.”””
start = pd.to_datetime(start_date).strftime(”%Y-%m-%d”)
end = pd.to_datetime(end_date).strftime(”%Y-%m-%d”)

```
url = "https://archive-api.open-meteo.com/v1/archive"
params = {
    "latitude": GAINESVILLE_LAT,
    "longitude": GAINESVILLE_LON,
    "start_date": start,
    "end_date": end,
    "daily": ["temperature_2m_max", "temperature_2m_min"],
    "temperature_unit": "fahrenheit",
    "timezone": "America/New_York",
}

try:
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()["daily"]
    
    df_temp = pd.DataFrame({
        "date": pd.to_datetime(data["time"]),
        "temp_max": data["temperature_2m_max"],
        "temp_min": data["temperature_2m_min"],
    })
    df_temp["temp_avg"] = (df_temp["temp_max"] + df_temp["temp_min"]) / 2
    df_temp = df_temp.set_index("date")
    return df_temp
except:
    return None
```

def merge_meter_temp(df_div, df_temp):
“”“Merge meter data with temperature.”””
df = df_div.copy().sort_values(“mr_date”).reset_index(drop=True)
df = df[df[“consumption”] > 0]

```
temp_avgs = []
for _, row in df.iterrows():
    end_date = row["mr_date"]
    start_date = end_date - pd.Timedelta(days=int(row["days"]))
    mask = (df_temp.index >= start_date) & (df_temp.index <= end_date)
    period_temps = df_temp[mask]
    temp_avgs.append(period_temps["temp_avg"].mean() if not period_temps.empty else None)

df["temp_avg"] = temp_avgs
return df.dropna(subset=["temp_avg"])
```

def merge_ami_temp(daily_series, df_temp):
“”“Merge AMI daily data with temperature.”””
df = daily_series.reset_index()
df.columns = [“date”, “value”]
df[“date”] = pd.to_datetime(df[“date”])

```
df_temp_reset = df_temp.reset_index()
df_temp_reset.columns = ["date", "temp_max", "temp_min", "temp_avg"]

merged = df.merge(df_temp_reset[["date", "temp_avg"]], on="date", how="inner")
return merged.dropna()
```

# ═══════════════════════════════════════════════════════════════════════════════

# TEMPERATURE CHARTS

# ═══════════════════════════════════════════════════════════════════════════════

def plot_temp_overlay_ami(df_merged, title, unit):
“”“Temperature overlay for AMI daily data.”””
colors = get_theme_colors()
setup_chart_style()

```
fig, ax1 = plt.subplots(figsize=(12, 5))

# Color bars by temperature
bar_colors = []
for t in df_merged["temp_avg"]:
    if t >= 80:
        bar_colors.append("#e57373")
    elif t <= 55:
        bar_colors.append("#64b5f6")
    else:
        bar_colors.append("#81c784")

ax1.bar(df_merged["date"], df_merged["value"], color=bar_colors, alpha=0.7, width=0.8)
ax1.set_ylabel(f"Daily {unit}", color=colors["text"])
ax1.set_xlabel("")

ax2 = ax1.twinx()
ax2.plot(df_merged["date"], df_merged["temp_avg"], color="#ff9800", linewidth=2.5, marker="o", markersize=3)
ax2.axhline(COMFORT_BASELINE, color="#ff9800", linestyle="--", linewidth=1, alpha=0.5)
ax2.set_ylabel("Temperature (F)", color="#ff9800")

# Legend
legend_elements = [
    mpatches.Patch(color="#e57373", alpha=0.7, label="Hot (>80F)"),
    mpatches.Patch(color="#81c784", alpha=0.7, label="Mild (55-80F)"),
    mpatches.Patch(color="#64b5f6", alpha=0.7, label="Cold (<55F)"),
    plt.Line2D([0], [0], color="#ff9800", linewidth=2.5, marker="o", label="Temperature"),
]
ax1.legend(handles=legend_elements, loc="upper left", fontsize=8)

ax1.set_title(title, fontweight="bold")
fig.autofmt_xdate()
plt.tight_layout()
return fig
```

def plot_temp_overlay_meter(df_merged, title, unit):
“”“Temperature overlay for meter billing data.”””
colors = get_theme_colors()
setup_chart_style()

```
fig, ax1 = plt.subplots(figsize=(12, 4))

ax1.bar(df_merged["mr_date"], df_merged["consumption"], width=20, color=colors["secondary"], alpha=0.6)
ax1.set_ylabel(unit, color=colors["secondary"])

ax2 = ax1.twinx()
ax2.plot(df_merged["mr_date"], df_merged["temp_avg"], color="#ff9800", linewidth=2.2, marker="o", markersize=4)
ax2.set_ylabel("Temperature (F)", color="#ff9800")

ax1.set_title(title, fontweight="bold")
fig.autofmt_xdate()
plt.tight_layout()
return fig
```

def compute_temp_correlation(df, value_col, temp_col=“temp_avg”, utility_type=“Electric”):
“”“Compute temperature correlation.”””
if utility_type == “Gas”:
# Linear correlation (negative expected for heating)
r = df[value_col].corr(df[temp_col])
return r, “linear”
else:
# V-shape correlation for Electric/Water
df = df.copy()
df[“temp_delta”] = (df[temp_col] - COMFORT_BASELINE).abs()
r = df[value_col].corr(df[“temp_delta”])
return r, “v-shape”

def plot_temp_scatter(df, value_col, unit, title, utility_type=“Electric”):
“”“Temperature correlation scatter plot.”””
colors = get_theme_colors()
setup_chart_style()

```
df = df.copy()

if utility_type == "Gas":
    x_col = "temp_avg"
    xlabel = "Average Temperature (F)"
else:
    df["temp_delta"] = (df["temp_avg"] - COMFORT_BASELINE).abs()
    x_col = "temp_delta"
    xlabel = "|Temperature - 65F|"

r, _ = compute_temp_correlation(df, value_col, utility_type=utility_type)

# Color by temperature
point_colors = ["#e57373" if t >= 80 else "#64b5f6" if t <= 55 else "#81c784" for t in df["temp_avg"]]

fig, ax = plt.subplots(figsize=(8, 5))
ax.scatter(df[x_col], df[value_col], c=point_colors, s=50, alpha=0.7, edgecolors="white")

# Trend line
z = np.polyfit(df[x_col], df[value_col], 1)
p = np.poly1d(z)
x_line = np.linspace(df[x_col].min(), df[x_col].max(), 100)
ax.plot(x_line, p(x_line), color=colors["danger"], linewidth=2, linestyle="--")

ax.set_xlabel(xlabel)
ax.set_ylabel(unit)
ax.set_title(f"{title} (r = {r:.2f})", fontweight="bold")

plt.tight_layout()
return fig, r
```

# ═══════════════════════════════════════════════════════════════════════════════

# CROSS-UTILITY CORRELATION

# ═══════════════════════════════════════════════════════════════════════════════

def compute_cross_utility_correlation(utility_data):
“”“Compute correlation between utilities using daily totals.”””
# Collect daily series from all utilities
daily_dfs = {}

```
for util_name, data in utility_data.items():
    if "features" in data and "daily_series" in data["features"]:
        ds = data["features"]["daily_series"].reset_index()
        ds.columns = ["date", util_name]
        ds["date"] = pd.to_datetime(ds["date"])
        daily_dfs[util_name] = ds

if len(daily_dfs) < 2:
    return None, None

# Merge all on date
merged = None
for util_name, df in daily_dfs.items():
    if merged is None:
        merged = df
    else:
        merged = merged.merge(df, on="date", how="inner")

if merged is None or len(merged) < 5:
    return None, None

# Compute correlation matrix
util_cols = [c for c in merged.columns if c != "date"]
corr_matrix = merged[util_cols].corr()

return merged, corr_matrix
```

def plot_cross_utility_scatter(merged_df, util1, util2, unit1, unit2):
“”“Scatter plot between two utilities.”””
colors = get_theme_colors()
setup_chart_style()

```
r = merged_df[util1].corr(merged_df[util2])

fig, ax = plt.subplots(figsize=(6, 5))
ax.scatter(merged_df[util1], merged_df[util2], color=colors["secondary"], s=40, alpha=0.7, edgecolors="white")

# Trend line
z = np.polyfit(merged_df[util1], merged_df[util2], 1)
p = np.poly1d(z)
x_line = np.linspace(merged_df[util1].min(), merged_df[util1].max(), 100)
ax.plot(x_line, p(x_line), color=colors["danger"], linewidth=2, linestyle="--")

ax.set_xlabel(f"{util1} ({unit1})")
ax.set_ylabel(f"{util2} ({unit2})")
ax.set_title(f"{util1} vs {util2} (r = {r:.2f})", fontweight="bold")

plt.tight_layout()
return fig, r
```

# ═══════════════════════════════════════════════════════════════════════════════

# AUDITOR ADVICE

# ═══════════════════════════════════════════════════════════════════════════════

def generate_auditor_advice(temp_correlations, cross_correlations, utility_features):
“”“Generate auditor advice based on analysis results.”””
advice = []

```
# Temperature correlation advice
for util, (r, corr_type) in temp_correlations.items():
    if util == "Gas":
        if r < -0.5:
            advice.append({
                "type": "success",
                "text": f"<b>{util} - Strong heating correlation (r={r:.2f}):</b> Natural gas furnace is primary heating source. Consider furnace efficiency upgrades, insulation improvements, and air sealing."
            })
        elif r < -0.2:
            advice.append({
                "type": "info",
                "text": f"<b>{util} - Moderate heating correlation (r={r:.2f}):</b> Some natural gas furnace usage for heating. Evaluate thermostat settings and furnace maintenance."
            })
        else:
            advice.append({
                "type": "warning",
                "text": f"<b>{util} - Weak temperature correlation (r={r:.2f}):</b> Gas usage not strongly heating-driven. Check for gas water heater, stove, or other non-HVAC gas appliances."
            })
    else:  # Electric or Water
        if r > 0.6:
            advice.append({
                "type": "success",
                "text": f"<b>{util} - Strong HVAC correlation (r={r:.2f}):</b> Usage driven by heating/cooling. Focus on envelope improvements, AC efficiency, and programmable thermostat."
            })
        elif r > 0.3:
            advice.append({
                "type": "info",
                "text": f"<b>{util} - Moderate HVAC correlation (r={r:.2f}):</b> Some temperature sensitivity. Other factors also significant - check appliances and plug loads."
            })
        else:
            advice.append({
                "type": "warning",
                "text": f"<b>{util} - Weak temperature correlation (r={r:.2f}):</b> Usage driven primarily by non-HVAC loads. Investigate appliances, lighting, and always-on equipment."
            })

# Cross-utility correlation advice
if cross_correlations is not None:
    for (util1, util2), r in cross_correlations.items():
        if "Water" in util1 or "Water" in util2:
            other = util1 if util2 == "Water" else util2
            if r > 0.5 and other == "Electric":
                advice.append({
                    "type": "info",
                    "text": f"<b>High Water-Electric correlation (r={r:.2f}):</b> Possible electric water heater or pool pump. Consider water heater efficiency or heat pump water heater upgrade."
                })
        if "Gas" in util1 or "Gas" in util2:
            other = util1 if util2 == "Gas" else util2
            if r < -0.3 and other == "Electric":
                advice.append({
                    "type": "info",
                    "text": f"<b>Inverse Gas-Electric correlation (r={r:.2f}):</b> Likely switching between natural gas furnace (winter) and AC (summer). Normal seasonal HVAC pattern."
                })

# Feature-based advice
for util, feats in utility_features.items():
    if "load_factor" in feats:
        lf = feats["load_factor"]
        if lf < 0.3:
            advice.append({
                "type": "warning",
                "text": f"<b>{util} - Low load factor ({lf:.1%}):</b> Peaky demand pattern. Consider load shifting, TOU rate optimization, or demand response programs."
            })
    
    if "base_load" in feats and util == "Electric":
        base = feats.get("base_load", 0)
        interval = feats.get("interval_minutes", 60)
        base_kw = base / (interval / 60) if interval > 0 else base
        if base_kw > 1.0:
            advice.append({
                "type": "warning",
                "text": f"<b>{util} - High base load ({base_kw:.2f} kW):</b> Significant always-on equipment. Check for old refrigerators, phantom loads, pool pumps, or inefficient HVAC."
            })
    
    if "n_anomalies" in feats and feats["n_anomalies"] > 0:
        advice.append({
            "type": "danger",
            "text": f"<b>{util} - {feats['n_anomalies']} anomalous periods detected:</b> Review flagged billing periods for equipment issues, occupancy changes, or meter problems."
        })

return advice
```

# ═══════════════════════════════════════════════════════════════════════════════

# FRACTAL ANALYZER

# ═══════════════════════════════════════════════════════════════════════════════

class FractalAnalyzer:
def **init**(self, values):
self.values = values
self.differenced = np.diff(values)

```
def compute_hurst(self):
    data = self.differenced
    N = len(data)
    
    if N < 50:
        return None, None
    
    max_window = N // 4
    window_sizes = np.unique(np.logspace(np.log10(4), np.log10(max_window), 15).astype(int))
    
    fluctuations = []
    for n in window_sizes:
        num_segments = N // n
        if num_segments < 2:
            continue
        rms_values = []
        for i in range(num_segments):
            segment = data[i*n:(i+1)*n]
            y = np.cumsum(segment - np.mean(segment))
            x = np.arange(n)
            coeffs = np.polyfit(x, y, 1)
            trend = np.polyval(coeffs, x)
            rms = np.sqrt(np.mean((y - trend) ** 2))
            if rms > 0:
                rms_values.append(rms)
        if rms_values:
            fluctuations.append((n, np.mean(rms_values)))
    
    if len(fluctuations) < 3:
        return None, None
    
    windows = np.array([f[0] for f in fluctuations])
    F_n = np.array([f[1] for f in fluctuations])
    
    valid = F_n > 0
    if valid.sum() < 3:
        return None, None
    
    log_n = np.log(windows[valid])
    log_F = np.log(F_n[valid])
    
    slope, _, r_value, _, _ = stats.linregress(log_n, log_F)
    
    return slope, r_value ** 2
```

# ═══════════════════════════════════════════════════════════════════════════════

# PDF REPORT

# ═══════════════════════════════════════════════════════════════════════════════

def generate_pdf_report(customer_info, charts, advice_list):
“”“Generate PDF report.”””
buffer = io.BytesIO()

```
# Use light theme for PDF
plt.rcParams.update({
    'figure.facecolor': 'white',
    'axes.facecolor': 'white',
    'text.color': 'black',
    'axes.labelcolor': 'black',
    'xtick.color': 'black',
    'ytick.color': 'black',
})

with PdfPages(buffer) as pdf:
    # Title page
    fig, ax = plt.subplots(figsize=(11, 8.5))
    ax.axis("off")
    
    ax.text(0.5, 0.8, "Energy Audit Report", fontsize=28, fontweight="bold", ha="center", color="#1e3a5f")
    
    if customer_info:
        ax.text(0.5, 0.55, f"Customer: {customer_info.get('customer_name', 'N/A')}", fontsize=14, ha="center")
        ax.text(0.5, 0.50, f"Account: {customer_info.get('account', 'N/A')}", fontsize=12, ha="center")
        ax.text(0.5, 0.45, f"Address: {customer_info.get('address', 'N/A')}", fontsize=12, ha="center")
    
    ax.text(0.5, 0.25, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", fontsize=10, ha="center", color="gray")
    
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)
    
    # Advice page
    if advice_list:
        fig, ax = plt.subplots(figsize=(11, 8.5))
        ax.axis("off")
        ax.text(0.5, 0.95, "Auditor Recommendations", fontsize=18, fontweight="bold", ha="center", color="#1e3a5f")
        
        y = 0.88
        for adv in advice_list:
            text = adv["text"].replace("<b>", "").replace("</b>", "")
            wrapped = "\n".join([text[i:i+90] for i in range(0, len(text), 90)])
            ax.text(0.05, y, wrapped, fontsize=9, va="top", wrap=True)
            y -= 0.12
            if y < 0.1:
                break
        
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)
    
    # Charts
    for chart in charts:
        if chart is not None:
            pdf.savefig(chart, bbox_inches="tight")
            plt.close(chart)

buffer.seek(0)
return buffer
```

# ═══════════════════════════════════════════════════════════════════════════════

# MAIN APPLICATION

# ═══════════════════════════════════════════════════════════════════════════════

def main():
# Sidebar
with st.sidebar:
st.header(“Settings”)

```
    # Dark/Light mode toggle
    dark_mode = st.toggle("Dark Mode", value=st.session_state.dark_mode)
    if dark_mode != st.session_state.dark_mode:
        st.session_state.dark_mode = dark_mode
        st.rerun()
    
    st.markdown("---")
    st.header("Data Upload")
    
    meter_file = st.file_uploader("Meter Reading File", type=["xlsx", "xls"], key="meter")
    ami_file = st.file_uploader("AMI Interval File", type=["xlsx", "xls"], key="ami")

# Apply theme
apply_theme()

# Title
st.title("Energy Audit Analyzer")
st.markdown("*Professional energy consumption analysis for auditors*")
st.markdown("---")

if meter_file is None and ami_file is None:
    st.info("Upload meter data and/or AMI data in the sidebar to begin analysis.")
    return

# Initialize data containers
customer_info = {}
meter_data = {}
ami_data = {}
df_temp = None
all_charts = []
temp_correlations = {}
cross_corr_pairs = {}
utility_features = {}

# Process meter file
if meter_file is not None:
    try:
        meter_file.seek(0)
        customer_info = get_master_sheet_info(meter_file)
        
        meter_file.seek(0)
        loader = MeterLoader(meter_file)
        loader.load_and_clean()
        
        for div in loader.get_available_divisions():
            df_div = loader.get_division(div)
            if not df_div.empty:
                feats = MeterFeatures(df_div).compute_features()
                meter_data[div] = {"df": df_div, "features": feats, "has_mr_reason": loader.has_mr_reason}
                utility_features[div] = feats
    except Exception as e:
        st.error(f"Meter file error: {e}")

# Process AMI file
if ami_file is not None:
    try:
        ami_file.seek(0)
        loader = AMILoader(ami_file)
        utilities = loader.load()
        
        if loader.customer_info and not customer_info:
            customer_info = loader.customer_info
        
        for util_name, data in utilities.items():
            feats = AMIFeatures(data["df"], data["unit"]).compute()
            ami_data[util_name] = {"df": data["df"], "features": feats, "unit": data["unit"]}
            utility_features[util_name] = feats
        
        if ami_data:
            st.sidebar.success(f"AMI: {', '.join(ami_data.keys())}")
    except Exception as e:
        st.error(f"AMI file error: {e}")

# Get all available utilities
all_utilities = list(set(list(meter_data.keys()) + list(ami_data.keys())))

if not all_utilities:
    st.warning("No valid utility data found.")
    return

# Customer info header
if customer_info:
    name = customer_info.get("customer_name", "Customer")
    st.markdown(f"### {name}")
    
    cols = st.columns(3)
    with cols[0]:
        st.markdown(f"**Account:** {customer_info.get('account', 'N/A')}")
    with cols[1]:
        st.markdown(f"**Address:** {customer_info.get('address', 'N/A')}")
    with cols[2]:
        st.markdown(f"**Survey Date:** {customer_info.get('survey_date', 'N/A')}")
    st.markdown("---")

# Fetch temperature data
date_ranges = []
for data in meter_data.values():
    dates = data["df"]["mr_date"]
    date_ranges.extend([dates.min(), dates.max()])
for data in ami_data.values():
    dates = data["df"]["timestamp"]
    date_ranges.extend([dates.min(), dates.max()])

if date_ranges:
    with st.spinner("Fetching temperature data..."):
        df_temp = get_temperature_data(
            min(date_ranges) - pd.Timedelta(days=35),
            max(date_ranges)
        )

# Build tabs
tab_names = ["Overview"] + all_utilities
if ami_data:
    tab_names.append("Advanced Analysis")
tab_names.append("Export Report")

tabs = st.tabs(tab_names)

# ═══════════════════════════════════════════════════════════════════════════
# OVERVIEW TAB
# ═══════════════════════════════════════════════════════════════════════════
with tabs[0]:
    st.header("Overview")
    
    # Temperature Overlay for ALL utilities
    if df_temp is not None:
        st.subheader("Temperature Correlation")
        
        for util in all_utilities:
            # AMI data preferred
            if util in ami_data:
                data = ami_data[util]
                merged = merge_ami_temp(data["features"]["daily_series"], df_temp)
                if not merged.empty:
                    fig = plot_temp_overlay_ami(merged, f"{util} Daily Usage vs Temperature", data["unit"])
                    st.pyplot(fig)
                    all_charts.append(fig)
                    
                    r, corr_type = compute_temp_correlation(merged, "value", utility_type=util)
                    temp_correlations[util] = (r, corr_type)
                    
                    fig2, r2 = plot_temp_scatter(merged, "value", data["unit"], f"{util} Temperature Correlation", util)
                    st.pyplot(fig2)
                    all_charts.append(fig2)
            
            elif util in meter_data:
                data = meter_data[util]
                merged = merge_meter_temp(data["df"], df_temp)
                if not merged.empty:
                    fig = plot_temp_overlay_meter(merged, f"{util} Consumption vs Temperature", data["features"]["unit"])
                    st.pyplot(fig)
                    all_charts.append(fig)
                    
                    r, corr_type = compute_temp_correlation(merged, "consumption", utility_type=util)
                    temp_correlations[util] = (r, corr_type)
            
            st.markdown("---")
    
    # Cross-Utility Correlation
    if len(all_utilities) >= 2 and ami_data:
        st.subheader("Cross-Utility Correlation")
        
        merged_cross, corr_matrix = compute_cross_utility_correlation(ami_data)
        
        if merged_cross is not None:
            # Display correlation table
            st.markdown("**Correlation Matrix (Daily Totals)**")
            st.dataframe(corr_matrix.round(2))
            
            # Scatter plots for each pair
            util_list = list(ami_data.keys())
            for i in range(len(util_list)):
                for j in range(i + 1, len(util_list)):
                    u1, u2 = util_list[i], util_list[j]
                    if u1 in merged_cross.columns and u2 in merged_cross.columns:
                        fig, r = plot_cross_utility_scatter(
                            merged_cross, u1, u2,
                            ami_data[u1]["unit"], ami_data[u2]["unit"]
                        )
                        st.pyplot(fig)
                        all_charts.append(fig)
                        cross_corr_pairs[(u1, u2)] = r
            
            st.markdown("---")
    
    # Auditor Advice
    st.subheader("Auditor Recommendations")
    
    advice_list = generate_auditor_advice(temp_correlations, cross_corr_pairs, utility_features)
    
    if advice_list:
        for adv in advice_list:
            info_box(adv["text"], adv["type"])
    else:
        st.info("Upload data to generate recommendations.")

# ═══════════════════════════════════════════════════════════════════════════
# UTILITY TABS
# ═══════════════════════════════════════════════════════════════════════════
for i, util in enumerate(all_utilities):
    with tabs[i + 1]:
        st.header(f"{util} Analysis")
        
        # Metrics row
        if util in ami_data:
            data = ami_data[util]
            feats = data["features"]
            unit = data["unit"]
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Daily Average", f"{feats['daily_avg']:.1f} {unit}")
            with col2:
                st.metric("Peak Interval", f"{feats['peak_val']:.1f} {unit}")
            with col3:
                st.metric("Base Load", f"{feats['base_load']:.2f} {unit}")
            with col4:
                st.metric("Load Factor", f"{feats['load_factor']:.1%}")
            
            # Load shape
            st.subheader("Load Shape")
            setup_chart_style()
            colors = get_theme_colors()
            
            fig, ax = plt.subplots(figsize=(12, 4))
            df = feats["df"]
            ax.plot(df["timestamp"], df["value"], color=colors["secondary"], linewidth=0.5, alpha=0.8)
            ax.fill_between(df["timestamp"], df["value"], alpha=0.3, color=colors["secondary"])
            ax.set_ylabel(f"{unit} per Interval")
            ax.set_title(f"{util} Load Shape")
            fig.autofmt_xdate()
            plt.tight_layout()
            st.pyplot(fig)
            all_charts.append(fig)
            
            # Daily and Hourly
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Daily Totals")
                fig, ax = plt.subplots(figsize=(10, 4))
                daily = feats["daily_series"]
                ax.bar(daily.index, daily.values, color=colors["secondary"], alpha=0.8)
                ax.axhline(feats["daily_avg"], color=colors["danger"], linestyle="--", linewidth=2)
                ax.set_ylabel(f"Daily {unit}")
                fig.autofmt_xdate()
                plt.tight_layout()
                st.pyplot(fig)
                all_charts.append(fig)
            
            with col2:
                st.subheader("Hourly Profile")
                fig, ax = plt.subplots(figsize=(10, 4))
                hours = feats["avg_by_hour"].index
                values = feats["avg_by_hour"].values
                bar_colors = [colors["accent"] if 6 <= h < 9 or 17 <= h < 21 else colors["secondary"] for h in hours]
                ax.bar(hours, values, color=bar_colors, alpha=0.8)
                ax.set_xlabel("Hour of Day")
                ax.set_ylabel(f"Average {unit}")
                ax.set_xticks(range(0, 24, 2))
                plt.tight_layout()
                st.pyplot(fig)
                all_charts.append(fig)
        
        elif util in meter_data:
            data = meter_data[util]
            feats = data["features"]
            unit = feats["unit"]
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total", f"{feats['total_consumption']:,.0f} {unit}")
            with col2:
                if feats['overall_daily_avg']:
                    st.metric("Daily Avg", f"{feats['overall_daily_avg']:.2f} {unit}/day")
            with col3:
                st.metric("Peak", f"{feats['peak_consumption']:,.0f} {unit}")
            with col4:
                st.metric("Anomalies", feats['n_anomalies'])
            
            graphs = MeterGraphs(feats, title_prefix=util)
            
            fig = graphs.plot_consumption()
            st.pyplot(fig)
            all_charts.append(fig)
            
            col1, col2 = st.columns(2)
            with col1:
                fig = graphs.plot_rolling_average()
                st.pyplot(fig)
                all_charts.append(fig)
            
            with col2:
                fig = graphs.plot_anomalies()
                st.pyplot(fig)
                all_charts.append(fig)

# ═══════════════════════════════════════════════════════════════════════════
# ADVANCED ANALYSIS TAB
# ═══════════════════════════════════════════════════════════════════════════
if ami_data:
    adv_tab_idx = len(all_utilities) + 1
    with tabs[adv_tab_idx]:
        st.header("Advanced Analysis")
        
        st.markdown("""
        **Fractal Analysis** measures consumption pattern complexity using the Hurst Exponent (H):
        - **H < 0.45**: Anti-persistent (variable behavior, mean-reverting)
        - **H ~ 0.5**: Random (no pattern memory)
        - **H > 0.55**: Persistent (consistent, predictable patterns)
        """)
        
        for util, data in ami_data.items():
            st.subheader(f"{util} Complexity Analysis")
            
            analyzer = FractalAnalyzer(data["features"]["df"]["value"].values)
            H, r2 = analyzer.compute_hurst()
            
            if H is not None:
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Hurst Exponent", f"{H:.3f}")
                with col2:
                    st.metric("R-Squared", f"{r2:.3f}")
                
                if H < 0.45:
                    info_box(f"<b>Anti-Persistent Pattern (H={H:.3f}):</b> Variable occupant behavior. Recommend programmable thermostat and behavior-based interventions.", "info")
                elif H > 0.55:
                    info_box(f"<b>Persistent Pattern (H={H:.3f}):</b> Consistent patterns. Equipment upgrades will show measurable results.", "success")
                else:
                    info_box(f"<b>Mixed Pattern (H={H:.3f}):</b> No strong persistence. Mix of predictable and variable factors.", "warning")
            else:
                st.warning(f"Insufficient data for {util} complexity analysis.")
            
            st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════
# EXPORT TAB
# ═══════════════════════════════════════════════════════════════════════════
export_tab_idx = len(tab_names) - 1
with tabs[export_tab_idx]:
    st.header("Export Report")
    
    st.markdown("""
    Generate a PDF report including:
    - Temperature correlation analysis
    - Cross-utility correlations
    - Auditor recommendations
    - All utility charts
    """)
    
    if st.button("Generate PDF Report", type="primary"):
        with st.spinner("Generating report..."):
            pdf = generate_pdf_report(customer_info, all_charts, advice_list if 'advice_list' in dir() else [])
            name = customer_info.get("customer_name", "Customer") if customer_info else "Customer"
            filename = f"Energy_Audit_{name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf"
            
            st.download_button(
                label="Download PDF",
                data=pdf,
                file_name=filename,
                mime="application/pdf"
            )
```

if **name** == “**main**”:
main()