# 🛒 E-Commerce Performance & Root Cause Intelligence Engine

An automated diagnostic analytics system that tracks e-commerce funnel health and pinpoints why conversion and revenue metrics drop.

## 🚀 Features
- **Executive Health Dashboard:** Tracks Gross Revenue, Total Sessions, and Conversion Rate against baseline periods.
- **Automated Root Cause Slicing:** Scans browser, device, and payment gateway interactions to identify failure points.
- **Contribution Loss Scoring:** Weighs drop severity by traffic volume to prevent false alarms on small segments.

## 🛠️ Tech Stack
- **Python**
- **Pandas** (Data processing)
- **Streamlit** (Interactive web app)
- **Plotly** (Dynamic data visualizations)

## ⚡ Getting Started Locally

```bash
# Clone the repository
git clone https://github.com/mallikarjunpb11-maker/ecommerce-root-cause-intelligence.git
cd ecommerce-root-cause-intelligence

# Install dependencies
pip install -r requirements.txt

# Generate synthetic telemetry
python make_data.py

# Launch dashboard
streamlit run app.py
```
