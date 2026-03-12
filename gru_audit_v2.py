"""
Energy Audit Analyzer v2.1
Professional energy consumption analysis tool for auditors.

Based on the GRU Energy Audit Colab notebook - properly cleaned data,
move-in lines, meter change bands, rolling averages, temperature correlation.

Author: Energy Audit Tools
"""

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.backends.backend_pdf import PdfPages
from scipy import stats
from sklearn.ensemble import IsolationForest
from sklearn.linear_model import HuberRegressor
import requests
import io
import warnings
from datetime import datetime, timedelta

warnings.filterwarnings('ignore')

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ═══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Energy Audit Analyzer",
    page_icon="E",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Professional color palette
COLORS = {
    "primary": "#1e3a5f",
    "secondary": "#3498db",
    "accent": "#e67e22",
    "success": "#27ae60",
    "warning": "#f39c12",
    "danger": "#c0392b",
    "neutral": "#7f8c8d",
    "steelblue": "steelblue",
    "crimson": "crimson",
    "goldenrod": "goldenrod",
    "dodgerblue": "dodgerblue",
    "darkorange": "darkorange",
}

# Chart style
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.size': 10,
    'axes.titlesize': 12,
    'axes.titleweight': 'bold',
    'axes.labelsize': 10,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'figure.facecolor': 'white',
    'axes.facecolor': 'white',
    'axes.edgecolor': '#cccccc',
    'grid.color': '#e0e0e0',
    'grid.alpha': 0.5,
})

# Custom CSS
st.markdown("""
<style>
    .stApp { background-color: #f8f9fa; }
    [data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #e0e0e0; }
    h1, h2, h3 { color: #1e3a5f; }
    .info-box { background-color: #e8f4fd; border-left: 4px solid #3498db; padding: 15px; margin: 15px 0; border-radius: 0 8px 8px 0; }
    .warning-box { background-color: #fef9e7; border-left: 4px solid #f39c12; padding: 15px; margin: 15px 0; border-radius: 0 8px 8px 0; }
    .success-box { background-color: #eafaf1; border-left: 4px solid #27ae60; padding: 15px; margin: 15px 0; border-radius: 0 8px 8px 0; }
    .danger-box { background-color: #fdedec; border-left: 4px solid #c0392b; padding: 15px; margin: 15px 0; border-radius: 0 8px 8px 0; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


def info_box(text, box_type="info"):
    st.markdown(f'<div class="{box_type}-box">{text}</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# MASTER SHEET INFO
# ═══════════════════════════════════════════════════════════════════════════════

def get_master_sheet_info(file_obj):
    """Extract customer information from Master Sheet."""
    try:
        ms = pd.read_excel(file_obj, sheet_name="Master Sheet", header=None)
        
        def safe_get(row, col):
            try:
                val = ms.iloc[row, col]
                return str(val).strip() if pd.notna(val) else None
            except:
                return None
        
        # Auto-detect row offset (if cell 0,6 has no digits, it's a title row)
        row_offset = 0
        cell_0_6 = safe_get(0, 6)
        if cell_0_6 and not any(c.isdigit() for c in str(cell_0_6)):
            row_offset = 1
        
        def get(row, col):
            return safe_get(row + row_offset, col)
        
        info = {
            "account": get(0, 6),
            "customer_name": get(1, 6),
            "own_rent": get(2, 6),
            "community": get(3, 6),
            "address": get(4, 6),
            "city_town": get(5, 6),
            "gru_rep": get(6, 2),
            "survey_date": get(7, 2),
        }
        
        if info["survey_date"] and "00:00:00" in str(info["survey_date"]):
            try:
                info["survey_date"] = pd.to_datetime(info["survey_date"]).strftime("%m/%d/%Y")
            except:
                pass
        
        return info
    except Exception as e:
        return {"error": str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# METER LOADER - Exact copy from Colab with proper data cleaning
# ═══════════════════════════════════════════════════════════════════════════════

class MeterLoader:
    """Load and clean meter consumption data - matches Colab logic exactly."""
    
    COLUMN_MAP = {
        "Division": "division", "Device": "device", "MR Reason": "mr_reason",
        "MR Type": "mr_type", "MR Date": "mr_date", "Days": "days",
        "MR Result": "mr_result", "MR Unit": "mr_unit", "Consumption": "consumption",
        "Avg.": "avg_daily", "Avg": "avg_daily",
    }
    
    NON_READ_REASONS = {3}
    VLINE_REASONS = {6, 21, 22}  # Move-In, Meter Removal, Meter Install
    NON_READ_TYPES = {"automatic estimation"}
    
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
                df["consumption"] = df["consumption"].astype(str).str.replace(",", "", regex=False)
            df["consumption"] = pd.to_numeric(df["consumption"], errors="coerce")
        
        for col in ["mr_result", "days", "avg_daily"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        
        df = df.dropna(subset=["mr_date"])
        
        # KEY CLEANING LOGIC FROM COLAB:
        if self.has_mr_reason:
            df["mr_reason"] = pd.to_numeric(df["mr_reason"], errors="coerce")
            # Remove non-reads (reason 3)
            df = df[~df["mr_reason"].isin(self.NON_READ_REASONS)]
            # Keep consumption > 0 OR vline reasons (Move-In, Meter Changes)
            df = df[(df["consumption"] > 0) | (df["mr_reason"].isin(self.VLINE_REASONS))]
        else:
            if "mr_type" in df.columns:
                df = df[~df["mr_type"].str.strip().str.lower().isin(self.NON_READ_TYPES)]
            df = df[df["consumption"] > 0]
        
        # CRITICAL: Filter out zero-day periods
        df = df[df["days"] > 0]
        
        df = df.sort_values(["division", "device", "mr_date"]).reset_index(drop=True)
        self.df = df
        return df
    
    def get_division(self, name):
        """Get division data, SKIPPING THE FIRST READ (cumulative before metering)."""
        if self.df is None:
            return pd.DataFrame()
        
        sub = self.df[self.df["division"] == name].copy()
        
        if not sub.empty:
            # CRITICAL: Skip first reading - it's the cumulative before metering started
            sub = sub[sub["mr_date"] > sub["mr_date"].min()].reset_index(drop=True)
        
        return sub


# ═══════════════════════════════════════════════════════════════════════════════
# METER FEATURES
# ═══════════════════════════════════════════════════════════════════════════════

class MeterFeatures:
    """Compute features from meter data - matches Colab logic."""
    
    def __init__(self, df):
        self.df = df.copy().sort_values("mr_date").reset_index(drop=True)
    
    def compute_features(self):
        df = self.df
        
        avg_read_interval = df["days"].mean()
        total_consumption = df["consumption"].sum()
        total_days = df["days"].sum()
        overall_daily_avg = total_consumption / total_days if total_days > 0 else None
        peak_consumption = df["consumption"].max()
        base_consumption = df["consumption"].quantile(0.05)
        
        period_series = df.set_index("mr_date")["consumption"]
        rolling_avg = period_series.rolling(window=3, min_periods=1).mean()
        daily_avg_series = df.set_index("mr_date")["avg_daily"] if "avg_daily" in df.columns else None
        
        # Isolation Forest anomaly detection
        iso_cols = [c for c in ["consumption", "days", "avg_daily"] if c in df.columns]
        iso_data = df[iso_cols].dropna()
        df["anomaly"] = False
        
        if len(iso_data) >= 5:
            preds = IsolationForest(contamination=0.05, random_state=42).fit_predict(iso_data)
            df.loc[iso_data.index, "anomaly"] = (preds == -1)
        
        n_anomalies = int(df["anomaly"].sum())
        unit = df["mr_unit"].iloc[0] if "mr_unit" in df.columns else ""
        
        # Data quality score
        score = 100
        if df["consumption"].isna().any():
            score -= 10
        if "days" in df.columns and df["days"].std() > 10:
            score -= 5
        if len(df) < 12:
            score -= (12 - len(df)) * 2
        quality_score = max(0, min(100, score))
        
        return {
            "avg_read_interval": avg_read_interval,
            "total_consumption": total_consumption,
            "overall_daily_avg": overall_daily_avg,
            "peak_consumption": peak_consumption,
            "base_consumption": base_consumption,
            "period_series": period_series,
            "rolling_avg": rolling_avg,
            "daily_avg_series": daily_avg_series,
            "df_with_anomalies": df,
            "n_anomalies": n_anomalies,
            "unit": unit,
            "quality_score": quality_score,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# METER GRAPHS - With Move-In lines and Meter Change bands
# ═══════════════════════════════════════════════════════════════════════════════

class MeterGraphs:
    """Generate meter charts with event markers - matches Colab."""
    
    def __init__(self, feats, title_prefix="", has_mr_reason=True):
        self.feats = feats
        self.prefix = title_prefix
        self.df = feats["df_with_anomalies"]
        self.has_mr_reason = has_mr_reason
    
    def _get_meter_changes(self):
        """Find consecutive 21+22 pairs for meter change bands."""
        if "mr_reason" not in self.df.columns:
            return []
        
        df = self.df.sort_values("mr_date")
        changes = []
        reasons = df["mr_reason"].tolist()
        dates = df["mr_date"].tolist()
        
        i = 0
        while i < len(reasons):
            if reasons[i] == 22:
                for j in range(i + 1, min(i + 4, len(reasons))):
                    if reasons[j] == 21:
                        changes.append((dates[i], dates[j]))
                        i = j + 1
                        break
                else:
                    changes.append((dates[i], dates[i]))
                    i += 1
            elif reasons[i] == 21:
                found = False
                for j in range(i - 1, max(i - 4, -1), -1):
                    if reasons[j] == 22:
                        found = True
                        break
                if not found:
                    changes.append((dates[i], dates[i]))
                i += 1
            else:
                i += 1
        return changes
    
    def _add_markers(self, ax):
        """Draw move-in vlines and meter change bands."""
        if "mr_reason" not in self.df.columns:
            return
        
        df = self.df
        
        # Move-in lines (reason 6)
        move_ins = df[df["mr_reason"] == 6]
        first_movein = True
        for _, row in move_ins.iterrows():
            lbl = "Move-In" if first_movein else "_nolegend_"
            ax.axvline(x=row["mr_date"], color="dodgerblue",
                      linewidth=1.8, linestyle="--", alpha=0.9, label=lbl)
            first_movein = False
        
        # Meter change bands (21 + 22 pairs)
        changes = self._get_meter_changes()
        first_change = True
        for date_start, date_end in changes:
            lbl = "Meter Change" if first_change else "_nolegend_"
            if date_start == date_end:
                ax.axvline(x=date_start, color="darkorange",
                          linewidth=1.8, linestyle="--", alpha=0.9, label=lbl)
            else:
                ax.axvspan(date_start, date_end,
                          color="darkorange", alpha=0.18, label=lbl)
                ax.axvline(x=date_start, color="darkorange",
                          linewidth=1.2, linestyle="--", alpha=0.6)
                ax.axvline(x=date_end, color="darkorange",
                          linewidth=1.2, linestyle="--", alpha=0.6)
            first_change = False
    
    def plot_consumption(self):
        """Consumption bar chart with event markers."""
        df_plot = self.df[self.df["consumption"] > 0]
        s = df_plot.set_index("mr_date")["consumption"]
        
        fig, ax = plt.subplots(figsize=(13, 4))
        ax.bar(s.index, s.values, width=20, color="steelblue", alpha=0.85, label="Consumption")
        self._add_markers(ax)
        ax.set_title(f"{self.prefix} - Consumption per Read Period")
        ax.set_ylabel(self.feats["unit"])
        ax.legend()
        fig.autofmt_xdate()
        plt.tight_layout()
        return fig
    
    def plot_daily_average(self):
        """Daily average line chart with event markers."""
        s = self.feats["daily_avg_series"]
        if s is None:
            return None
        
        s = s[s > 0]
        
        fig, ax = plt.subplots(figsize=(13, 4))
        ax.plot(s.index, s.values, color="goldenrod", linewidth=2,
               marker="o", markersize=4, label="Daily Avg")
        self._add_markers(ax)
        ax.set_title(f"{self.prefix} - Average Daily Usage per Period")
        ax.set_ylabel(f"{self.feats['unit']}/day")
        ax.legend()
        fig.autofmt_xdate()
        plt.tight_layout()
        return fig
    
    def plot_rolling_average(self):
        """Consumption with 3-period rolling average."""
        df_plot = self.df[self.df["consumption"] > 0]
        s = df_plot.set_index("mr_date")["consumption"]
        r = s.rolling(window=3, min_periods=1).mean()
        
        fig, ax = plt.subplots(figsize=(13, 4))
        ax.plot(s.index, s.values, color="steelblue", alpha=0.4,
               linewidth=1.5, label="Consumption")
        ax.plot(r.index, r.values, color="crimson",
               linewidth=2.5, label="3-Read Rolling Avg")
        self._add_markers(ax)
        ax.set_title(f"{self.prefix} - Consumption Trend")
        ax.set_ylabel(self.feats["unit"])
        ax.legend()
        fig.autofmt_xdate()
        plt.tight_layout()
        return fig
    
    def plot_anomalies(self):
        """Anomaly detection chart with event markers."""
        df = self.df[self.df["consumption"] > 0]
        normal = df[~df["anomaly"]]
        anomaly = df[df["anomaly"]]
        
        fig, ax = plt.subplots(figsize=(13, 4))
        ax.bar(normal["mr_date"], normal["consumption"],
              width=20, color="steelblue", alpha=0.85, label="Normal")
        ax.bar(anomaly["mr_date"], anomaly["consumption"],
              width=20, color="crimson", alpha=0.9, label="Anomaly")
        self._add_markers(ax)
        ax.set_title(f"{self.prefix} - Anomaly Detection")
        ax.set_ylabel(self.feats["unit"])
        ax.legend()
        fig.autofmt_xdate()
        plt.tight_layout()
        return fig


# ═══════════════════════════════════════════════════════════════════════════════
# AMI LOADER - Robust multi-format support
# ═══════════════════════════════════════════════════════════════════════════════

class AMILoader:
    """Load AMI interval data with auto-format detection."""
    
    UNITS = {"Electric": "kWh", "Water": "Gal", "Gas": "CCF"}
    
    def __init__(self, file_obj):
        self.file_obj = file_obj
        self.df = None
        self.util_type = None
        self.unit = None
        self.format_detected = None
    
    def _detect_utility_type(self, xl, filename=""):
        filename_lower = str(filename).lower()
        if "water" in filename_lower:
            return "Water"
        elif "gas" in filename_lower:
            return "Gas"
        elif "electric" in filename_lower:
            return "Electric"
        
        for name in xl.sheet_names:
            if "WATER" in name.upper():
                return "Water"
            elif "GAS" in name.upper():
                return "Gas"
            elif "ELECTRIC" in name.upper():
                return "Electric"
        
        return "Electric"
    
    def load(self):
        filename = getattr(self.file_obj, 'name', '')
        xl = pd.ExcelFile(self.file_obj)
        sheet = xl.sheet_names[0]
        
        self.util_type = self._detect_utility_type(xl, filename)
        self.unit = self.UNITS.get(self.util_type, "kWh")
        
        # Read preview to find header
        preview = pd.read_excel(xl, sheet_name=sheet, header=None, nrows=15)
        
        header_row = 0
        for i in range(min(10, len(preview))):
            row_values = [str(x).lower().strip() for x in preview.iloc[i].values if pd.notna(x)]
            row_str = " ".join(row_values)
            if any(kw in row_str for kw in ["date", "time", "timestamp"]):
                header_row = i
                break
        
        df = pd.read_excel(xl, sheet_name=sheet, header=header_row)
        df.columns = [str(c).strip() for c in df.columns]
        
        # Identify columns
        date_col, time_col, value_col = None, None, None
        
        for col in df.columns:
            col_lower = col.lower()
            if col_lower in ["date", "datetime", "date/time"]:
                date_col = col
            elif col_lower in ["time"]:
                time_col = col
            elif col_lower in ["kwh", "value", "reading", "consumption", "usage", "gal", "ccf"]:
                value_col = col
        
        # Find value column if not found
        if value_col is None:
            for col in df.columns:
                if col not in [date_col, time_col]:
                    try:
                        numeric_vals = pd.to_numeric(df[col], errors='coerce')
                        if numeric_vals.notna().sum() > len(df) * 0.5:
                            value_col = col
                            break
                    except:
                        continue
        
        if date_col is None or value_col is None:
            raise ValueError(f"Could not identify columns. Found: {df.columns.tolist()}")
        
        # Parse timestamps
        if time_col:
            # Format C: Separate Date and Time columns
            self.format_detected = "C"
            timestamps = []
            for _, row in df.iterrows():
                try:
                    date_val = row[date_col]
                    time_val = str(row[time_col]).strip()
                    
                    if isinstance(date_val, pd.Timestamp):
                        date_str = date_val.strftime("%Y-%m-%d")
                    else:
                        date_str = pd.to_datetime(date_val).strftime("%Y-%m-%d")
                    
                    try:
                        time_obj = pd.to_datetime(time_val, format="%I:%M %p")
                        time_str = time_obj.strftime("%H:%M")
                    except:
                        try:
                            time_obj = pd.to_datetime(time_val, format="%H:%M")
                            time_str = time_obj.strftime("%H:%M")
                        except:
                            time_str = "00:00"
                    
                    timestamps.append(pd.to_datetime(f"{date_str} {time_str}"))
                except:
                    timestamps.append(pd.NaT)
            
            df["timestamp"] = timestamps
            multiplier = 1.0
        else:
            # Combined datetime column
            first_val = str(df[date_col].iloc[0]).strip()
            
            def clean_tz(x):
                s = str(x).strip()
                for tz in [" EST", " EDT", " CST", " CDT", " PST", " PDT"]:
                    s = s.replace(tz, "")
                return s.strip()
            
            if " - " in first_val:
                # Format A
                self.format_detected = "A"
                df["timestamp"] = df[date_col].apply(
                    lambda x: pd.to_datetime(clean_tz(x).replace(" - ", " "), errors="coerce"))
                multiplier = 0.001
            elif "/" in first_val:
                # Format B
                self.format_detected = "B"
                df["timestamp"] = df[date_col].apply(
                    lambda x: pd.to_datetime(clean_tz(x), format="%m/%d/%Y %H:%M", errors="coerce"))
                multiplier = 1.0
            else:
                # Format D
                self.format_detected = "D"
                df["timestamp"] = pd.to_datetime(df[date_col], errors="coerce")
                multiplier = 1.0
        
        df["kwh"] = pd.to_numeric(df[value_col], errors="coerce") * multiplier
        df = df[["timestamp", "kwh"]].dropna()
        df = df.sort_values("timestamp").reset_index(drop=True)
        
        self.df = df
        return df


# ═══════════════════════════════════════════════════════════════════════════════
# AMI FEATURES
# ═══════════════════════════════════════════════════════════════════════════════

class AMIFeatures:
    def __init__(self, df, unit="kWh"):
        self.df = df.copy()
        self.unit = unit
    
    def compute(self):
        df = self.df.sort_values("timestamp")
        
        deltas = df["timestamp"].diff().dropna()
        interval = deltas.mode()[0]
        interval_minutes = int(interval.total_seconds() / 60)
        
        base_load = df["kwh"].quantile(0.05)
        base_load_rate = base_load / (interval_minutes / 60)
        peak_val = df["kwh"].max()
        peak_rate = peak_val / (interval_minutes / 60)
        
        df["date"] = df["timestamp"].dt.date
        daily_series = df.groupby("date")["kwh"].sum()
        daily_avg = daily_series.mean()
        peak_day = pd.Timestamp(daily_series.idxmax())
        
        df["hour"] = df["timestamp"].dt.hour
        avg_by_hour = df.groupby("hour")["kwh"].mean()
        
        total_val = df["kwh"].sum()
        hours = len(df) * interval_minutes / 60
        avg_demand = total_val / hours if hours > 0 else 0
        load_factor = avg_demand / peak_rate if peak_rate > 0 else 0
        
        return {
            "interval_minutes": interval_minutes,
            "base_load": base_load,
            "base_load_rate": base_load_rate,
            "peak_val": peak_val,
            "peak_rate": peak_rate,
            "daily_avg": daily_avg,
            "daily_series": daily_series,
            "peak_day": peak_day,
            "avg_by_hour": avg_by_hour,
            "load_factor": load_factor,
            "df": df,
            "unit": self.unit,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# TEMPERATURE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

GAINESVILLE_LAT = 29.6516
GAINESVILLE_LON = -82.3248

@st.cache_data(ttl=3600)
def get_gainesville_temps(start_date, end_date):
    """Fetch daily temperature data from Open-Meteo API."""
    start = pd.to_datetime(start_date).strftime("%Y-%m-%d")
    end = pd.to_datetime(end_date).strftime("%Y-%m-%d")
    
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
    except Exception as e:
        st.warning(f"Could not fetch temperature data: {e}")
        return None


def merge_consumption_temp(df_div, df_temp):
    """Merge meter consumption with temperature - exact Colab logic."""
    df = df_div.copy().sort_values("mr_date").reset_index(drop=True)
    df = df[df["consumption"] > 0]
    
    temp_avgs, temp_maxs, temp_mins = [], [], []
    
    for _, row in df.iterrows():
        end_date = row["mr_date"]
        start_date = end_date - pd.Timedelta(days=int(row["days"]))
        
        mask = (df_temp.index >= start_date) & (df_temp.index <= end_date)
        period_temps = df_temp[mask]
        
        if not period_temps.empty:
            temp_avgs.append(period_temps["temp_avg"].mean())
            temp_maxs.append(period_temps["temp_max"].mean())
            temp_mins.append(period_temps["temp_min"].mean())
        else:
            temp_avgs.append(None)
            temp_maxs.append(None)
            temp_mins.append(None)
    
    df["temp_avg"] = temp_avgs
    df["temp_max"] = temp_maxs
    df["temp_min"] = temp_mins
    
    return df.dropna(subset=["temp_avg"])


# ═══════════════════════════════════════════════════════════════════════════════
# TEMPERATURE CHARTS - Exact Colab style
# ═══════════════════════════════════════════════════════════════════════════════

def plot_temp_overlay(df_merged, title_prefix=""):
    """Consumption bars with temperature line overlaid."""
    fig, ax1 = plt.subplots(figsize=(13, 4))
    
    unit = df_merged["mr_unit"].iloc[0] if "mr_unit" in df_merged.columns else "Usage"
    
    ax1.bar(df_merged["mr_date"], df_merged["consumption"],
           width=20, color="steelblue", alpha=0.6, label="Consumption")
    ax1.set_ylabel(unit, color="steelblue")
    ax1.tick_params(axis="y", labelcolor="steelblue")
    
    ax2 = ax1.twinx()
    ax2.plot(df_merged["mr_date"], df_merged["temp_avg"],
            color="crimson", linewidth=2.2, marker="o", markersize=4, label="Avg Temp")
    ax2.fill_between(df_merged["mr_date"],
                    df_merged["temp_min"], df_merged["temp_max"],
                    color="crimson", alpha=0.08, label="Temp Range")
    ax2.set_ylabel("Temperature (F)", color="crimson")
    ax2.tick_params(axis="y", labelcolor="crimson")
    
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left", fontsize=8)
    ax1.set_title(f"{title_prefix} - Consumption vs Temperature")
    fig.autofmt_xdate()
    plt.tight_layout()
    return fig


def plot_temp_side_by_side(df_merged, title_prefix=""):
    """Consumption and temperature as stacked panels."""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 6), sharex=True)
    
    unit = df_merged["mr_unit"].iloc[0] if "mr_unit" in df_merged.columns else "Usage"
    
    ax1.bar(df_merged["mr_date"], df_merged["consumption"],
           width=20, color="steelblue", alpha=0.85)
    ax1.set_ylabel(unit)
    ax1.set_title(f"{title_prefix} - Consumption")
    
    ax2.plot(df_merged["mr_date"], df_merged["temp_avg"],
            color="crimson", linewidth=2, marker="o", markersize=4, label="Avg Temp")
    ax2.fill_between(df_merged["mr_date"],
                    df_merged["temp_min"], df_merged["temp_max"],
                    color="crimson", alpha=0.1, label="Temp Range")
    ax2.axhline(65, color="gray", linewidth=1, linestyle="--", label="65F baseline")
    ax2.set_ylabel("Temperature (F)")
    ax2.set_title("Daily Avg Temperature per Billing Period")
    ax2.legend(fontsize=8)
    
    fig.autofmt_xdate()
    plt.tight_layout()
    return fig


def plot_temp_scatter(df_merged, title_prefix="", division="Electricity"):
    """Temperature correlation scatter plot."""
    unit = df_merged["mr_unit"].iloc[0] if "mr_unit" in df_merged.columns else ""
    
    COMFORT_BASELINE = 65
    df = df_merged.copy()
    df["temp_delta"] = (df["temp_avg"] - COMFORT_BASELINE).abs()
    
    if "days" in df.columns:
        df["daily_cons"] = df["consumption"] / df["days"]
    else:
        df["daily_cons"] = df["consumption"]
    
    # Different logic for Gas vs Electric
    if division == "Gas":
        r_primary = df["daily_cons"].corr(df["temp_avg"])
        x_col = "temp_avg"
        xlabel = "Avg Temperature (F) - expect negative correlation for heating"
        title_r = f"Linear r = {r_primary:.2f}"
    else:
        r_primary = df["daily_cons"].corr(df["temp_delta"])
        r_linear = df["daily_cons"].corr(df["temp_avg"])
        x_col = "temp_delta"
        xlabel = "|Temperature - 65F| (deviation from comfort baseline)"
        title_r = f"V-shape r = {r_primary:.2f} (Linear r = {r_linear:.2f})"
    
    # Color by season
    def season_color(temp):
        if temp >= 80:
            return "#f76f6f"
        elif temp <= 55:
            return "#4f8ef7"
        else:
            return "#3ecf8e"
    
    colors = df["temp_avg"].apply(season_color)
    
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.scatter(df[x_col], df["daily_cons"], c=colors, s=60, alpha=0.8, edgecolors="white")
    
    # Trend line
    z = np.polyfit(df[x_col], df["daily_cons"], 1)
    p = np.poly1d(z)
    x_line = np.linspace(df[x_col].min(), df[x_col].max(), 100)
    ax.plot(x_line, p(x_line), color="crimson", linewidth=2, linestyle="--", label="Trend")
    
    ax.set_xlabel(xlabel)
    ax.set_ylabel(f"Daily {unit}")
    ax.set_title(f"{title_prefix} - Temperature Correlation ({title_r})")
    
    # Legend
    legend_elements = [
        mpatches.Patch(color="#f76f6f", label="Hot (>80F)"),
        mpatches.Patch(color="#3ecf8e", label="Mild (55-80F)"),
        mpatches.Patch(color="#4f8ef7", label="Cold (<55F)"),
    ]
    ax.legend(handles=legend_elements, loc="upper right")
    
    plt.tight_layout()
    return fig, r_primary


# ═══════════════════════════════════════════════════════════════════════════════
# FRACTAL ANALYZER
# ═══════════════════════════════════════════════════════════════════════════════

class FractalAnalyzer:
    """Fractal analysis for energy consumption - Hurst exponent via DFA."""
    
    def __init__(self, df_ami, value_col="kwh", time_col="timestamp"):
        self.df = df_ami.copy().sort_values(time_col).reset_index(drop=True)
        self.values = self.df[value_col].values
        self.differenced = np.diff(self.values)
    
    def detrended_fluctuation_analysis(self, min_window=4, max_window=None, num_windows=20):
        data = self.differenced
        N = len(data)
        
        if N < 20:
            return {"error": "Insufficient data for DFA"}
        
        if max_window is None:
            max_window = N // 4
        
        window_sizes = np.unique(np.logspace(
            np.log10(min_window),
            np.log10(max_window),
            num_windows
        ).astype(int))
        
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
            return {"error": "Insufficient valid fluctuations"}
        
        windows = np.array([f[0] for f in fluctuations])
        F_n = np.array([f[1] for f in fluctuations])
        
        valid = F_n > 0
        if valid.sum() < 3:
            return {"error": "Insufficient valid fluctuations"}
        
        log_n = np.log(windows[valid])
        log_F = np.log(F_n[valid])
        
        slope, intercept, r_value, p_value, _ = stats.linregress(log_n, log_F)
        
        return {
            "hurst_exponent": slope,
            "r_squared": r_value ** 2,
            "window_sizes": windows[valid],
            "fluctuations": F_n[valid],
            "log_n": log_n,
            "log_F": log_F,
            "slope": slope,
            "intercept": intercept,
        }
    
    def get_interpretation(self, dfa_result):
        if "error" in dfa_result:
            return [{"type": "warning", "title": "Analysis Error", "text": dfa_result["error"]}]
        
        H = dfa_result["hurst_exponent"]
        interpretations = []
        
        if H < 0.4:
            interpretations.append({
                "type": "info",
                "title": f"Anti-Persistent Pattern (H = {H:.3f})",
                "text": "Highly variable occupant behavior. High consumption periods quickly followed by low periods. Focus on behavior-based interventions: programmable thermostat, scheduling."
            })
        elif H < 0.55:
            interpretations.append({
                "type": "info",
                "title": f"Mixed Pattern (H = {H:.3f})",
                "text": "Usage shows no strong persistence. Mix of predictable and unpredictable factors."
            })
        else:
            interpretations.append({
                "type": "success",
                "title": f"Persistent Pattern (H = {H:.3f})",
                "text": "Consistent, predictable consumption patterns. Focus on equipment upgrades. Pre/post comparisons will be reliable."
            })
        
        return interpretations


# ═══════════════════════════════════════════════════════════════════════════════
# PDF REPORT
# ═══════════════════════════════════════════════════════════════════════════════

def generate_pdf_report(customer_info, charts, report_type="standard"):
    """Generate PDF report with all charts."""
    buffer = io.BytesIO()
    
    with PdfPages(buffer) as pdf:
        # Title page
        fig, ax = plt.subplots(figsize=(11, 8.5))
        ax.axis("off")
        
        ax.text(0.5, 0.8, "Energy Audit Report", fontsize=28, fontweight="bold",
               ha="center", va="center", color=COLORS["primary"])
        
        if customer_info:
            ax.text(0.5, 0.5, f"Customer: {customer_info.get('customer_name', 'N/A')}", 
                   fontsize=14, ha="center", va="center")
            ax.text(0.5, 0.45, f"Account: {customer_info.get('account', 'N/A')}", 
                   fontsize=12, ha="center", va="center")
            ax.text(0.5, 0.4, f"Address: {customer_info.get('address', 'N/A')}", 
                   fontsize=12, ha="center", va="center")
        
        label = "Standard Report" if report_type == "standard" else "Advanced Report"
        ax.text(0.5, 0.25, label, fontsize=12, ha="center", style="italic")
        ax.text(0.5, 0.15, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", 
               fontsize=10, ha="center", color="gray")
        
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)
        
        # Add all charts
        for chart in charts:
            if chart is not None:
                pdf.savefig(chart, bbox_inches="tight")
                plt.close(chart)
    
    buffer.seek(0)
    return buffer


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN APPLICATION
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    st.title("Energy Audit Analyzer")
    st.markdown("*Professional energy consumption analysis for auditors*")
    st.markdown("---")
    
    # Sidebar
    with st.sidebar:
        st.header("Data Upload")
        
        meter_file = st.file_uploader(
            "Meter Reading File (Excel)",
            type=["xlsx", "xls"],
            key="meter"
        )
        
        ami_file = st.file_uploader(
            "AMI Interval File (Excel)",
            type=["xlsx", "xls"],
            key="ami"
        )
        
        st.markdown("---")
        st.subheader("Settings")
        comfort_base = st.slider("Comfort Baseline (F)", 60, 72, 65, 1)
    
    if meter_file is None and ami_file is None:
        st.info("Upload meter data and/or AMI data to begin analysis.")
        
        with st.expander("How to Use"):
            st.markdown("""
            **1. Upload Data**
            - **Meter File**: Billing/consumption history with 'Consumption' sheet
            - **AMI File**: 15-minute or hourly interval data
            
            **2. Review Analysis**
            - Meter Analysis: Consumption, daily average, rolling trend, anomalies
            - Temperature: Overlay, side-by-side, correlation scatter
            - Advanced: Fractal complexity analysis (AMI only)
            
            **3. Export Reports**
            - Standard: Consumption + temperature analysis
            - Advanced: Adds fractal analysis
            """)
        return
    
    # Initialize
    customer_info = None
    meter_data = {}
    ami_data = None
    df_temp = None
    all_charts = []
    
    # Process meter file
    if meter_file is not None:
        try:
            meter_file.seek(0)
            customer_info = get_master_sheet_info(meter_file)
            
            meter_file.seek(0)
            loader = MeterLoader(meter_file)
            loader.load_and_clean()
            
            for div in ["Electricity", "Water", "Gas"]:
                df_div = loader.get_division(div)
                if not df_div.empty:
                    meter_data[div] = {
                        "df": df_div,
                        "has_mr_reason": loader.has_mr_reason
                    }
        except Exception as e:
            st.error(f"**Meter File Error**: {e}")
    
    # Process AMI file
    if ami_file is not None:
        try:
            ami_file.seek(0)
            ami_loader = AMILoader(ami_file)
            df_ami = ami_loader.load()
            ami_feats = AMIFeatures(df_ami, unit=ami_loader.unit).compute()
            ami_data = {
                "df": df_ami,
                "features": ami_feats,
                "util_type": ami_loader.util_type,
                "unit": ami_loader.unit,
            }
            st.sidebar.success(f"AMI: {ami_loader.util_type} (Format {ami_loader.format_detected})")
        except Exception as e:
            st.error(f"**AMI File Error**: {e}")
    
    # Customer info header
    if customer_info and "customer_name" in customer_info:
        st.markdown(f"### {customer_info.get('customer_name', 'Customer')}")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"**Account:** {customer_info.get('account', 'N/A')}")
        with col2:
            st.markdown(f"**Address:** {customer_info.get('address', 'N/A')}")
        with col3:
            st.markdown(f"**Survey Date:** {customer_info.get('survey_date', 'N/A')}")
        st.markdown("---")
    
    # Build tabs
    tab_names = []
    if meter_data:
        tab_names.append("Meter Analysis")
    if ami_data:
        tab_names.append("AMI Analysis")
    if meter_data or ami_data:
        tab_names.append("Temperature Analysis")
    if ami_data:
        tab_names.append("Advanced Analysis")
    tab_names.append("Export Report")
    
    if not tab_names:
        return
    
    tabs = st.tabs(tab_names)
    tab_idx = 0
    
    # ─── METER ANALYSIS TAB ─────────────────────────────────────────────────────
    if meter_data:
        with tabs[tab_idx]:
            tab_idx += 1
            
            st.header("Meter Data Analysis")
            
            for div, data in meter_data.items():
                st.subheader(div)
                
                df = data["df"]
                feats = MeterFeatures(df).compute_features()
                graphs = MeterGraphs(feats, title_prefix=div, has_mr_reason=data["has_mr_reason"])
                
                # Metrics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total", f"{feats['total_consumption']:,.0f} {feats['unit']}")
                with col2:
                    if feats['overall_daily_avg']:
                        st.metric("Daily Avg", f"{feats['overall_daily_avg']:.2f} {feats['unit']}/day")
                with col3:
                    st.metric("Peak", f"{feats['peak_consumption']:,.0f} {feats['unit']}")
                with col4:
                    st.metric("Anomalies", feats['n_anomalies'])
                
                # Charts
                fig = graphs.plot_consumption()
                st.pyplot(fig)
                all_charts.append(fig)
                
                col1, col2 = st.columns(2)
                with col1:
                    fig = graphs.plot_daily_average()
                    if fig:
                        st.pyplot(fig)
                        all_charts.append(fig)
                
                with col2:
                    fig = graphs.plot_rolling_average()
                    st.pyplot(fig)
                    all_charts.append(fig)
                
                fig = graphs.plot_anomalies()
                st.pyplot(fig)
                all_charts.append(fig)
                
                # Show anomalies
                if feats["n_anomalies"] > 0:
                    with st.expander("View Anomalous Periods"):
                        anomalies = feats["df_with_anomalies"][feats["df_with_anomalies"]["anomaly"]]
                        cols = [c for c in ["mr_date", "days", "consumption", "avg_daily"] if c in anomalies.columns]
                        st.dataframe(anomalies[cols].reset_index(drop=True))
                
                st.markdown("---")
    
    # ─── AMI ANALYSIS TAB ───────────────────────────────────────────────────────
    if ami_data:
        with tabs[tab_idx]:
            tab_idx += 1
            
            st.header(f"AMI Analysis ({ami_data['util_type']})")
            
            df_ami = ami_data["df"]
            feats = ami_data["features"]
            unit = ami_data["unit"]
            
            # Metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Daily Avg", f"{feats['daily_avg']:.1f} {unit}")
            with col2:
                st.metric("Peak Interval", f"{feats['peak_val']:.1f} {unit}")
            with col3:
                st.metric("Base Load", f"{feats['base_load']:.2f} {unit}")
            with col4:
                st.metric("Load Factor", f"{feats['load_factor']:.1%}")
            
            # Load shape
            st.subheader("Load Shape")
            fig, ax = plt.subplots(figsize=(14, 5))
            ax.plot(df_ami["timestamp"], df_ami["kwh"], color="steelblue", linewidth=0.5, alpha=0.8)
            ax.fill_between(df_ami["timestamp"], df_ami["kwh"], alpha=0.3, color="steelblue")
            ax.set_xlabel("Date/Time")
            ax.set_ylabel(f"{unit} per Interval")
            ax.set_title(f"{ami_data['util_type']} Load Shape")
            fig.autofmt_xdate()
            plt.tight_layout()
            st.pyplot(fig)
            all_charts.append(fig)
            
            # Daily and Hourly
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Daily Totals")
                fig, ax = plt.subplots(figsize=(10, 5))
                daily = feats["daily_series"]
                ax.bar(daily.index, daily.values, color="steelblue", alpha=0.8)
                ax.axhline(feats["daily_avg"], color="crimson", linestyle="--", linewidth=2, 
                          label=f"Avg: {feats['daily_avg']:.1f}")
                ax.set_ylabel(f"Daily {unit}")
                ax.legend()
                fig.autofmt_xdate()
                plt.tight_layout()
                st.pyplot(fig)
                all_charts.append(fig)
            
            with col2:
                st.subheader("Hourly Profile")
                fig, ax = plt.subplots(figsize=(10, 5))
                hours = feats["avg_by_hour"].index
                values = feats["avg_by_hour"].values
                colors = ["#e67e22" if 6 <= h < 9 or 17 <= h < 21 else 
                         "#3498db" if 9 <= h < 17 else "#1e3a5f" for h in hours]
                ax.bar(hours, values, color=colors, alpha=0.8)
                ax.set_xlabel("Hour of Day")
                ax.set_ylabel(f"Average {unit}")
                ax.set_xticks(range(0, 24, 2))
                plt.tight_layout()
                st.pyplot(fig)
                all_charts.append(fig)
    
    # ─── TEMPERATURE ANALYSIS TAB ───────────────────────────────────────────────
    if meter_data or ami_data:
        with tabs[tab_idx]:
            tab_idx += 1
            
            st.header("Temperature Analysis")
            
            # Get date range
            date_ranges = []
            if meter_data:
                for div, data in meter_data.items():
                    dates = data["df"]["mr_date"]
                    date_ranges.extend([dates.min(), dates.max()])
            if ami_data:
                dates = ami_data["df"]["timestamp"]
                date_ranges.extend([dates.min(), dates.max()])
            
            date_min = min(date_ranges) - pd.Timedelta(days=35)
            date_max = max(date_ranges)
            
            # Fetch temperature
            with st.spinner("Fetching temperature data..."):
                df_temp = get_gainesville_temps(date_min, date_max)
            
            if df_temp is None:
                st.error("Could not fetch temperature data.")
            else:
                st.success(f"Temperature data: {len(df_temp)} days")
                
                # Process each division
                if meter_data:
                    for div, data in meter_data.items():
                        st.subheader(f"{div} vs Temperature")
                        
                        df_merged = merge_consumption_temp(data["df"], df_temp)
                        
                        if df_merged.empty:
                            st.warning(f"No temperature overlap for {div}")
                            continue
                        
                        # Overlay
                        fig = plot_temp_overlay(df_merged, title_prefix=div)
                        st.pyplot(fig)
                        all_charts.append(fig)
                        
                        # Side by side
                        fig = plot_temp_side_by_side(df_merged, title_prefix=div)
                        st.pyplot(fig)
                        all_charts.append(fig)
                        
                        # Scatter with correlation
                        fig, r = plot_temp_scatter(df_merged, title_prefix=div, division=div)
                        st.pyplot(fig)
                        all_charts.append(fig)
                        
                        # Interpretation
                        if div == "Gas":
                            if r < -0.5:
                                info_box(f"Strong negative correlation (r={r:.2f}): Gas usage increases significantly when temperature drops. Heating-driven.", "success")
                            elif r < -0.2:
                                info_box(f"Moderate negative correlation (r={r:.2f}): Some heating sensitivity.", "info")
                            else:
                                info_box(f"Weak correlation (r={r:.2f}): Gas usage not strongly temperature-driven.", "warning")
                        else:
                            if r > 0.6:
                                info_box(f"Strong temperature correlation (r={r:.2f}): Usage driven by HVAC. Building responds predictably to temperature.", "success")
                            elif r > 0.3:
                                info_box(f"Moderate correlation (r={r:.2f}): Some HVAC sensitivity, other factors also significant.", "info")
                            else:
                                info_box(f"Weak correlation (r={r:.2f}): Usage driven primarily by non-HVAC loads.", "warning")
                        
                        st.markdown("---")
    
    # ─── ADVANCED ANALYSIS TAB ──────────────────────────────────────────────────
    if ami_data:
        with tabs[tab_idx]:
            tab_idx += 1
            
            st.header("Advanced Analysis: Complexity Patterns")
            
            st.markdown("""
            **Fractal Analysis** uses Detrended Fluctuation Analysis (DFA) to measure the 
            complexity of energy consumption patterns via the **Hurst Exponent (H)**:
            
            - **H < 0.45**: Anti-persistent (variable, mean-reverting)
            - **H ~ 0.5**: Random (no memory)
            - **H > 0.55**: Persistent (trending, predictable)
            """)
            
            analyzer = FractalAnalyzer(ami_data["df"])
            dfa_result = analyzer.detrended_fluctuation_analysis()
            
            if "error" not in dfa_result:
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Hurst Exponent", f"{dfa_result['hurst_exponent']:.3f}")
                with col2:
                    st.metric("R-Squared", f"{dfa_result['r_squared']:.3f}")
                
                # DFA chart
                fig, ax = plt.subplots(figsize=(10, 5))
                ax.scatter(dfa_result["log_n"], dfa_result["log_F"], 
                          color="steelblue", s=60, alpha=0.8)
                x_line = np.linspace(dfa_result["log_n"].min(), dfa_result["log_n"].max(), 100)
                y_line = dfa_result["slope"] * x_line + dfa_result["intercept"]
                ax.plot(x_line, y_line, color="crimson", linewidth=2, linestyle="--",
                       label=f"H = {dfa_result['hurst_exponent']:.3f}")
                ax.set_xlabel("log(Window Size)")
                ax.set_ylabel("log(Fluctuation)")
                ax.set_title("DFA Scaling Plot")
                ax.legend()
                ax.grid(True, alpha=0.3)
                plt.tight_layout()
                st.pyplot(fig)
                all_charts.append(fig)
                
                # Interpretation
                st.subheader("Interpretation")
                for interp in analyzer.get_interpretation(dfa_result):
                    info_box(f"**{interp['title']}**<br>{interp['text']}", interp["type"])
            else:
                st.warning(dfa_result["error"])
    
    # ─── EXPORT TAB ─────────────────────────────────────────────────────────────
    with tabs[tab_idx]:
        st.header("Export Report")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Standard Report")
            st.markdown("""
            **Includes:**
            - Consumption charts with event markers
            - Daily average and rolling trends
            - Temperature correlation analysis
            - Anomaly detection
            """)
            
            if st.button("Generate Standard Report", type="primary"):
                with st.spinner("Generating..."):
                    pdf = generate_pdf_report(customer_info, all_charts, "standard")
                    name = customer_info.get("customer_name", "Customer") if customer_info else "Customer"
                    filename = f"Energy_Audit_{name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf"
                    st.download_button("Download PDF", pdf, filename, "application/pdf")
        
        with col2:
            st.subheader("Advanced Report")
            st.markdown("""
            **Includes Standard, plus:**
            - Fractal complexity analysis
            - Hurst exponent interpretation
            - Behavior classification
            """)
            
            if ami_data:
                if st.button("Generate Advanced Report", type="secondary"):
                    with st.spinner("Generating..."):
                        pdf = generate_pdf_report(customer_info, all_charts, "advanced")
                        name = customer_info.get("customer_name", "Customer") if customer_info else "Customer"
                        filename = f"Energy_Audit_Advanced_{name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf"
                        st.download_button("Download PDF", pdf, filename, "application/pdf")
            else:
                st.info("Upload AMI data for advanced report.")


if __name__ == "__main__":
    main()
