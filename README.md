# Energy Audit Analyzer v3.0

An energy consumption analysis tool for energy auditors. Analyzes meter billing data and AMI interval data to identify patterns, correlations, and actionable recommendations.

## Features

### Multi-Utility Support
- **Electric** (kWh)
- **Water** (Gal, kGal)
- **Gas** (CCF, Therms)
- Dynamic tabs - only shows utilities present in your data
- Handles any combination: single utility, two utilities, or all three

### Temperature Analysis
- Automatic temperature data fetch (Gainesville, FL - Open-Meteo API)
- Temperature overlay charts with color-coded bars (Hot/Mild/Cold)
- Correlation scatter plots with trend lines
- V-shape correlation for Electric/Water (deviation from 65F baseline)
- Linear correlation for Gas (negative = heating-driven)

### Cross-Utility Correlation
Works with both AMI and meter data:

| Correlation | What It Detects |
|-------------|-----------------|
| Water-Electric > 0.7 | Possible electric water heater issue or hot water leak |
| Water-Electric > 0.5 | Electric water heater or pool pump present |
| Water-Gas > 0.7 | Possible natural gas water heater issue or hot water leak |
| Water-Gas > 0.5 | Natural gas water heater detected |
| Electric-Gas < -0.5 | Seasonal HVAC switching (furnace/AC) - normal pattern |
| Electric-Gas > 0.5 | Unusual - both increasing together, check equipment |

### Auditor Recommendations
Automatic advice generation based on:
- Temperature correlations (HVAC dependency)
- Cross-utility correlations (water heater issues, leaks)
- Load factor analysis (peaky demand)
- Base load detection (always-on equipment)
- Anomaly detection (unusual billing periods)

### Additional Features
- **Dark/Light Mode** - Toggle in sidebar
- **Responsive Design** - Works on desktop and mobile
- **PDF Export** - Generate reports with all charts and recommendations
- **Flexible AMI Formats** - Auto-detects multiple file formats

## Installation

### Local Installation

```bash
# Clone or download the repository
git clone https://github.com/yourusername/energy-audit-analyzer.git
cd energy-audit-analyzer

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run streamlit_energy_audit.py
```

Opens at `http://localhost:8501`

### Streamlit Cloud Deployment

1. Push code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repo
4. Deploy

## File Formats

### Meter Files (Excel)

Expected structure:
- **Master Sheet** tab with customer info (optional)
- **Consumption** tab with billing data

Required columns:
| Column | Description |
|--------|-------------|
| Division | Electricity, Water, or Gas |
| MR Date | Meter read date |
| Days | Days in billing period |
| Consumption | Usage for period |
| Avg. | Daily average (optional) |
| MR Reason | Read reason code (optional) |
| MR Unit | Unit of measure |

MR Reason codes handled:
- 3 = Non-read (filtered out)
- 6 = Move-In (shown as vertical line)
- 21/22 = Meter Change (shown as shaded band)

### AMI Files (Excel)

Supports multiple formats:

**Format A** - Combined datetime with " - " separator
```
Feb 25, 2026 - 12:00 am | 1,862.000 Wh Del
```

**Format B** - Combined datetime MM/DD/YYYY
```
01/12/2026 00:15 EST | 2.5
```

**Format C** - Separate Date and Time columns
```
Date       | Time     | Gal
2/15/2026  | 1:00 am  | 25.4
```

**Format D** - Standard datetime
```
timestamp           | kwh
2026-01-15 00:00:00 | 1.5
```

**Multi-Utility AMI Files:**
- Multiple sheets supported (ELECTRIC, WATER, GAS)
- Utility type detected from sheet name
- Units auto-detected from values (Wh, kWh, Gal, CCF)

## Usage

### 1. Upload Data

In the sidebar:
- **Meter Reading File** - Excel file with billing history
- **AMI Interval File** - Excel file with 15-min or hourly data

You can upload one or both file types.

### 2. Review Overview Tab

The Overview tab shows:
- Temperature overlay charts for all utilities
- Temperature correlation scatter plots
- Cross-utility correlation matrix and scatter plots
- Auditor recommendations

### 3. Explore Utility Tabs

Each utility gets its own tab with:
- Key metrics (total, daily avg, peak, anomalies)
- Consumption charts with Move-In and Meter Change markers
- Rolling average trend lines
- Anomaly detection

**AMI data additionally shows:**
- Load shape (full interval data)
- Daily totals bar chart
- Hourly profile by time of day
- Load factor

### 4. Advanced Analysis (AMI only)

Fractal/complexity analysis using Hurst Exponent:
- H < 0.45: Anti-persistent (variable behavior)
- H ~ 0.5: Random (no pattern)
- H > 0.55: Persistent (consistent patterns)

### 5. Export Report

Generate PDF report including:
- Cover page with customer info
- Auditor recommendations
- All charts from analysis

## Auditor Advice Reference

### Temperature Correlations

| Pattern | Utility | Advice |
|---------|---------|--------|
| r > 0.6 | Electric/Water | Strong HVAC dependency - focus on envelope, AC efficiency |
| r > 0.3 | Electric/Water | Moderate HVAC sensitivity - check appliances too |
| r < 0.3 | Electric/Water | Non-HVAC loads dominate - investigate appliances, lighting |
| r < -0.5 | Gas | Natural gas furnace is primary heat source |
| r < -0.2 | Gas | Some natural gas furnace usage |
| r > -0.2 | Gas | Gas not heating-driven - check water heater, stove |

### Cross-Utility Correlations

| Pattern | Advice |
|---------|--------|
| Water-Electric > 0.7 | Check for electric water heater issues or hot water leaks |
| Water-Gas > 0.7 | Check for natural gas water heater issues or hot water leaks |
| Electric-Gas < -0.5 | Normal seasonal switching between furnace and AC |
| Electric-Gas > 0.5 | Unusual - investigate equipment issues |

### Load Characteristics

| Pattern | Advice |
|---------|--------|
| Load factor < 30% | Peaky demand - consider load shifting, TOU rates |
| Base load > 1 kW | High always-on usage - check phantom loads, old equipment |
| Anomalies detected | Review flagged periods for equipment issues |

## Requirements

```
numpy>=1.21.0
pandas>=1.3.0
matplotlib>=3.4.0
scikit-learn>=0.24.0
scipy>=1.7.0
requests>=2.25.0
openpyxl>=3.0.0
streamlit>=1.28.0
```

## Troubleshooting

### "No consumption sheet found"
- Ensure your meter file has a sheet with "Consumption" in the name

### "Could not identify columns"
- Check that your AMI file has recognizable date/time and value columns
- Supported column names: Date, Time, DateTime, kWh, Value, Gal, CCF

### Temperature data not loading
- Requires internet connection
- Open-Meteo API may be temporarily unavailable
- Data cached for 1 hour

### Cross-utility correlation not showing
- Need at least 2 utilities with overlapping date ranges
- Need at least 5 overlapping data points


