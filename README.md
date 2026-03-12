# Energy Audit Analyzer

Professional energy consumption analysis tool for energy auditors. Analyze meter billing data and AMI interval data with weather normalization and advanced complexity analysis.

---

## Features

### Data Analysis
- **Meter Data Analysis**: Load billing/consumption history, detect anomalies, compute statistics
- **AMI Interval Analysis**: 15-minute or hourly interval data with load shape, hourly profiles, and demand metrics
- **Multi-Utility Support**: Electricity, Water, and Gas divisions

### Weather Integration
- **Automatic Temperature Fetch**: Pulls historical temperature data from Open-Meteo API (no API key required)
- **Temperature Overlay Charts**: Visualize consumption alongside daily temperatures
- **Weather-Normalized Anomaly Detection**: Uses HDD/CDD regression to identify periods with unexpectedly high or low usage

### Advanced Analysis
- **Fractal Analysis (DFA)**: Detrended Fluctuation Analysis to compute Hurst exponent
- **Complexity Classification**: Categorize buildings as persistent, anti-persistent, or random patterns
- **Distribution Analysis**: Skewness, kurtosis, and normality testing

### Reporting
- **Standard Report (PDF)**: Consumption charts, weather analysis, anomaly detection
- **Advanced Report (PDF)**: Includes fractal analysis and behavior classification
- **Professional Formatting**: Clean charts suitable for client presentations

---

## Installation

### Requirements
- Python 3.8 or higher
- pip package manager

### Setup

1. Clone or download this repository:
```bash
git clone https://github.com/your-username/energy-audit-analyzer.git
cd energy-audit-analyzer
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
streamlit run streamlit_energy_audit.py
```

4. Open your browser to `http://localhost:8501`

---

## Usage

### Step 1: Upload Data

**Meter File (Excel)**
- Must contain a sheet named "Consumption" (or similar)
- Required columns: Division, MR Date, Days, Consumption
- Optional: Master Sheet with customer information

**AMI File (Excel)**
- Interval data with timestamp and value columns
- Supports 15-minute or hourly intervals
- Auto-detects format variations

### Step 2: Review Analysis

Navigate through tabs to see different analyses:

| Tab | Description |
|-----|-------------|
| Overview | Customer info, data summary, quick insights |
| Meter Analysis | Consumption history, daily averages, anomaly flags |
| AMI Analysis | Load shape, hourly profile, load factor, peak demand |
| Temperature Analysis | Weather correlation, normalized anomaly detection |
| Advanced Analysis | Fractal complexity patterns (Hurst exponent) |
| Export Report | Generate PDF reports |

### Step 3: Export Reports

**Standard Report**
- Consumption history charts
- Temperature correlation analysis
- Weather-normalized anomaly detection
- Summary statistics

**Advanced Report**
- Everything in Standard, plus:
- Fractal analysis (DFA scaling plots)
- Distribution analysis
- Behavior pattern classification
- Advanced recommendations

---

## File Format Requirements

### Meter File Structure

The application expects an Excel file with:

1. **Master Sheet** (optional but recommended):
   - Row 1, Col G: Account number
   - Row 2, Col G: Customer name
   - Row 5, Col G: Street address
   - Row 6, Col G: City, State ZIP

2. **Consumption Sheet**:

| Column | Description |
|--------|-------------|
| Division | Electricity, Water, or Gas |
| MR Date | Meter read date |
| Days | Days in billing period |
| Consumption | Usage amount |
| MR Unit | Unit of measurement (kWh, kGal, CCF) |
| Avg. | Daily average (optional) |

### AMI File Structure

Excel file with interval readings. Multiple formats are supported:

**Format A** - Combined timestamp with date separator:
| Date/Time | Value |
|-----------|-------|
| Jan 15, 2025 - 2:30 PM EST | 1250 |

*Note: Values assumed to be in Wh (divided by 1000 for kWh)*

**Format B** - Combined timestamp, numeric format:
| Date/Time | kWh |
|-----------|-----|
| 01/12/2026 00:15 EST | 1.25 |

**Format C** - Separate Date and Time columns:
| Date | Time | kwh |
|------|------|-----|
| 2026-03-11 | 12:00 am | 268.4 |
| 2026-03-10 | 11:00 pm | 415.6 |

*Note: Time can be 12-hour (am/pm) or 24-hour format*

**Format D** - Standard datetime:
| DateTime | Reading |
|----------|---------|
| 2026-03-11 00:00:00 | 1.25 |

**Auto-Detection:**
- Utility type (Electric/Water/Gas) detected from filename or sheet name
- Column names detected automatically (Date, Time, kWh, Value, Consumption, etc.)
- Header row found by scanning for date/time keywords

---

## Understanding the Analysis

### Weather-Normalized Anomaly Detection

This analysis answers: "Is this customer using more or less energy than expected given the weather?"

**How it works:**
1. Computes Heating Degree Days (HDD) and Cooling Degree Days (CDD) for each billing period
2. Trains a regression model: `Daily Usage = f(HDD, CDD)`
3. Compares actual usage to predicted usage
4. Flags periods where the difference exceeds 2.5 standard deviations

**Interpretation:**
- **High Anomaly**: Using more than expected. Investigate HVAC issues, air leaks, occupancy changes
- **Low Anomaly**: Using less than expected. May indicate vacancy or conservation efforts
- **Persistent Anomaly**: Multiple consecutive anomalies. Higher priority for investigation

### Fractal Analysis (Hurst Exponent)

This analysis answers: "How complex and predictable is this building's energy use pattern?"

**Hurst Exponent (H) Interpretation:**

| H Value | Pattern | Meaning |
|---------|---------|---------|
| H < 0.4 | Strongly Anti-Persistent | Highly variable behavior; high periods followed by low |
| 0.4 - 0.5 | Anti-Persistent | Usage tends to bounce back toward average |
| 0.5 | Random | No clear pattern; unpredictable |
| 0.5 - 0.6 | Weakly Persistent | Mild trending behavior |
| H > 0.6 | Strongly Persistent | Consistent, predictable patterns |

**Auditor Recommendations:**
- **Anti-Persistent (H < 0.45)**: Focus on behavior-based interventions; consider programmable thermostat
- **Persistent (H > 0.55)**: Focus on equipment upgrades; pre/post comparisons will be reliable

---

## Deployment

### Streamlit Cloud (Recommended)

1. Push files to GitHub:
```bash
git init
git add streamlit_energy_audit.py requirements.txt README.md
git commit -m "Initial commit"
git remote add origin https://github.com/your-username/energy-audit-analyzer.git
git push -u origin main
```

2. Go to [share.streamlit.io](https://share.streamlit.io)

3. Click "New app" and connect your GitHub repository

4. Set main file path: `streamlit_energy_audit.py`

5. Click "Deploy"

### Docker (Alternative)

Create a `Dockerfile`:
```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY streamlit_energy_audit.py .
EXPOSE 8501
CMD ["streamlit", "run", "streamlit_energy_audit.py", "--server.port=8501"]
```

Build and run:
```bash
docker build -t energy-audit-analyzer .
docker run -p 8501:8501 energy-audit-analyzer
```

---

## Configuration

### Settings (Sidebar)

| Setting | Default | Description |
|---------|---------|-------------|
| Anomaly Z-Threshold | 2.5 | Standard deviations for anomaly flagging |
| Comfort Baseline | 65 F | Base temperature for degree day calculations |

### Customization

To modify the default location for temperature data, edit these constants in the code:

```python
GAINESVILLE_LAT = 29.6516
GAINESVILLE_LON = -82.3248
```

---

## Technical Details

### Dependencies

| Package | Purpose |
|---------|---------|
| streamlit | Web application framework |
| pandas | Data manipulation |
| numpy | Numerical operations |
| matplotlib | Chart generation |
| scipy | Statistical functions |
| scikit-learn | Anomaly detection (Isolation Forest), regression (HuberRegressor) |
| requests | API calls for temperature data |
| openpyxl | Excel file reading |

### Key Classes

| Class | Purpose |
|-------|---------|
| `MeterLoader` | Load and clean meter billing data |
| `MeterFeatures` | Compute statistics and detect anomalies |
| `AMILoader` | Load AMI interval data with format detection |
| `AMIFeatures` | Compute load metrics (peak, base, load factor) |
| `WeatherAnomalyDetector` | Weather-normalized anomaly detection |
| `FractalAnalyzer` | DFA and complexity analysis |

### API Usage

The application uses the [Open-Meteo Archive API](https://open-meteo.com/) for historical temperature data. No API key is required. Rate limits are generous for typical usage.

---

## References

### Fractal Analysis

Based on research by Knowles et al. (2017):

> "Describing the dynamics, distributions, and multiscale relationships in the time evolution of residential building energy consumption"
> 
> *Energy and Buildings, Volume 158, Pages 310-325*
> 
> University of Florida

### Weather Normalization

Uses standard ASHRAE methods for Heating Degree Days (HDD) and Cooling Degree Days (CDD) calculations with a configurable comfort baseline.

---

## Troubleshooting

### Common Errors and Solutions

**"No consumption sheet found"**
- Ensure your Excel file has a sheet with "Consumption" in the name
- Check available sheets in the error message
- Rename your data sheet to include "Consumption"

**"Missing required columns: ['mr_date', 'consumption']"**
- Check that your file has columns named "MR Date" and "Consumption"
- Alternative accepted names: "Date", "Read Date", "Usage"
- The error message will suggest which columns might match

**"Could not find date/time column"**
- AMI files need a column with "Date", "Time", or "DateTime" in the name
- Accepted column names: Date, Time, DateTime, Date/Time, Reading Date

**"Could not find value column"**
- AMI files need a numeric column for consumption values
- Accepted names: kWh, Value, Consumption, Reading, Usage, Gal, CCF

**"No valid data after parsing"**
- Date format may not be recognized
- Check that dates are in a standard format (YYYY-MM-DD, MM/DD/YYYY, etc.)
- Check that values are numeric (not text)

**"Insufficient data for analysis"**
- Meter analysis requires at least 6 billing periods
- Fractal analysis requires sufficient AMI intervals (100+ recommended)
- Weather analysis requires temperature data to be available

**Charts not displaying correctly**
- Ensure matplotlib is properly installed
- Try clearing Streamlit cache: `streamlit cache clear`
- Check browser console for JavaScript errors

### Debug Information

When an error occurs, the app displays debug information including:
- Available sheets in the file
- Detected column names
- Row counts before/after filtering
- Format type detected (for AMI files)

Use this information to identify what the app found and what it expected.

---

## License

MIT License

Copyright (c) 2024

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

---

## Support

For issues or feature requests, please open an issue on GitHub.
