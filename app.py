import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Executive Root Cause Intelligence Console",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CUSTOM ANALYST THEME: GRADIENTS, CARDS & ACCENTS ---
st.markdown("""
    <style>
    /* 1. Main Dashboard Background Gradient */
    .stApp {
        background: radial-gradient(circle at 10% 20%, rgb(15, 23, 42) 0%, rgb(10, 15, 29) 90.2%);
        color: #f8fafc;
    }

    /* 2. Sidebar Custom Styling */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0b0f19 0%, #111827 100%) !important;
        border-right: 1px solid #1e293b;
    }

    /* 3. Executive Metric KPI Cards */
    div[data-testid="stMetric"] {
        background: rgba(30, 41, 59, 0.7);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 4px 14px 0 rgba(0, 0, 0, 0.35);
        backdrop-filter: blur(8px);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        border-color: #38bdf8;
    }

    /* Metric Label (Title) */
    div[data-testid="stMetric"] label {
        color: #94a3b8 !important;
        font-weight: 600;
        letter-spacing: 0.5px;
    }

    /* Metric Value */
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #f1f5f9 !important;
        font-weight: 700;
    }

    /* 4. Sleek Headers with Gradient Underline */
    h1 {
        background: linear-gradient(90deg, #38bdf8 0%, #818cf8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800 !important;
    }

    h2, h3 {
        color: #e2e8f0 !important;
        border-bottom: 2px solid #1e293b;
        padding-bottom: 6px;
    }

    /* 5. Custom Button Styling */
    .stDownloadButton button {
        background: linear-gradient(90deg, #0284c7 0%, #2563eb 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 10px 24px !important;
        font-weight: 600 !important;
        box-shadow: 0 4px 12px rgba(2, 132, 199, 0.35) !important;
    }
    .stDownloadButton button:hover {
        opacity: 0.95;
        transform: scale(1.02);
    }
    </style>
""", unsafe_allow_html=True)

# --- 1. DATA INGESTION ---
@st.cache_data
def load_data():
    return pd.read_csv("store_data.csv")

df = load_data()

# --- 2. DYNAMIC SIDEBAR CONTROLS ---
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/3094/3094837.png", width=60)
st.sidebar.title("Telemetry Controls")
st.sidebar.markdown("Filter sessions across funnel parameters:")

# File Uploader Option
uploaded_file = st.sidebar.file_uploader("📥 Ingest Custom CSV", type=["csv"])
if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    st.sidebar.success("Custom telemetry ingested!")

# Slicers
selected_browsers = st.sidebar.multiselect(
    "Browser Environment",
    options=df["browser"].unique(),
    default=df["browser"].unique()
)

selected_devices = st.sidebar.multiselect(
    "Client Device Tier",
    options=df["device"].unique(),
    default=df["device"].unique()
)

selected_gateways = st.sidebar.multiselect(
    "Payment Gateway Channel",
    options=df["gateway"].unique(),
    default=df["gateway"].unique()
)

# Apply dynamic filters
filtered_df = df[
    (df["browser"].isin(selected_browsers)) &
    (df["device"].isin(selected_devices)) &
    (df["gateway"].isin(selected_gateways))
]

if filtered_df.empty:
    st.warning("⚠️ No data matches the selected filter parameters. Please widen your filter selection.")
    st.stop()

# Segment Baseline vs. Incident
base = filtered_df[filtered_df["period"] == "Baseline"]
inci = filtered_df[filtered_df["period"] == "Incident"]

# --- 3. HIGH-LEVEL EXECUTIVE SUMMARY ---
st.title("🛒 E-Commerce Root Cause Intelligence Engine")
st.markdown("Automated diagnostic system isolating conversion rate degradation across high-dimensional traffic slices.")

b_sessions, i_sessions = base["sessions"].sum(), inci["sessions"].sum()
b_orders, i_orders = base["orders"].sum(), inci["orders"].sum()
b_rev, i_rev = base["revenue"].sum(), inci["revenue"].sum()

b_cr = (b_orders / b_sessions * 100) if b_sessions > 0 else 0
i_cr = (i_orders / i_sessions * 100) if i_sessions > 0 else 0
cr_delta = i_cr - b_cr
rev_pct_change = ((i_rev - b_rev) / b_rev * 100) if b_rev > 0 else 0
session_pct_change = ((i_sessions - b_sessions) / b_sessions * 100) if b_sessions > 0 else 0

st.subheader("1. Executive Funnel Telemetry")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Gross Incident Revenue", f"${i_rev:,.0f}", f"{rev_pct_change:.1f}% vs Baseline")
col2.metric("Total Funnel Sessions", f"{i_sessions:,.0f}", f"{session_pct_change:.1f}% vs Baseline")
col3.metric("Observed Conversion Rate", f"{i_cr:.2f}%", f"{cr_delta:.2f}% Delta")
col4.metric("Orders Processed", f"{i_orders:,.0f}", f"{((i_orders - b_orders)/b_orders*100):.1f}% vs Baseline")

st.markdown("---")

# --- 4. ROOT CAUSE SLICING ALGORITHM ---
st.subheader("2. Automated Root Cause Decomposition")

dimensions = ["browser", "device", "gateway"]
results = []

for dim in dimensions:
    b_group = base.groupby(dim).agg({"sessions": "sum", "orders": "sum", "revenue": "sum"}).reset_index()
    i_group = inci.groupby(dim).agg({"sessions": "sum", "orders": "sum", "revenue": "sum"}).reset_index()
    
    merged = pd.merge(b_group, i_group, on=dim, suffixes=("_base", "_inci"))
    merged["cr_base"] = (merged["orders_base"] / merged["sessions_base"]) * 100
    merged["cr_inci"] = (merged["orders_inci"] / merged["sessions_inci"]) * 100
    merged["cr_delta"] = merged["cr_inci"] - merged["cr_base"]
    
    # Weighted Loss Score: (Delta CR) * (Share of Total Incident Sessions)
    merged["loss_score"] = merged["cr_delta"] * (merged["sessions_inci"] / i_sessions)
    merged["revenue_lost"] = (merged["cr_base"]/100 * merged["sessions_inci"] * 75) - merged["revenue_inci"]

    for _, row in merged.iterrows():
        results.append({
            "Dimension": dim.title(),
            "Segment": row[dim],
            "Baseline CR (%)": round(row["cr_base"], 2),
            "Incident CR (%)": round(row["cr_inci"], 2),
            "CR Delta (%)": round(row["cr_delta"], 2),
            "Loss Contribution Score": round(row["loss_score"], 4),
            "Estimated Lost Revenue ($)": int(row["revenue_lost"]) if row["revenue_lost"] > 0 else 0
        })

results_df = pd.DataFrame(results).sort_values(by="Loss Contribution Score", ascending=True)

worst = results_df.iloc[0]
st.error(
    f"🚨 **Critical Segment Driver Identified:** `{worst['Dimension']} = {worst['Segment']}` "
    f"experienced a **{worst['CR Delta (%)']}%** conversion collapse, resulting in an estimated **${worst['Estimated Lost Revenue ($)']:,}** in lost bookings."
)

# Custom Color Palette per dimension
custom_colors = {
    "Browser": "#38bdf8",   # Sky blue
    "Device": "#a855f7",    # Purple
    "Gateway": "#f43f5e"    # Rose/Crimson
}

fig_bar = px.bar(
    results_df,
    x="Loss Contribution Score",
    y="Segment",
    color="Dimension",
    color_discrete_map=custom_colors,
    orientation="h",
    text="CR Delta (%)",
    title="Contribution Loss by Segment (Red/Purple highlights root failures)",
    template="plotly_dark"
)
fig_bar.update_layout(
    yaxis={'categoryorder': 'total ascending'},
    plot_bgcolor='rgba(15, 23, 42, 0)',
    paper_bgcolor='rgba(15, 23, 42, 0)',
    font=dict(color="#e2e8f0")
)
st.plotly_chart(fig_bar, use_container_width=True)

# --- 5. INTERACTIVE WHAT-IF REVENUE SIMULATOR ---
st.subheader("3. 💡 What-If Scenario Recovery Simulator")
st.markdown("Quantify projected revenue gains by modeling post-patch conversion restoration:")

sim_col1, sim_col2 = st.columns([1, 2])

with sim_col1:
    target_cr = st.slider(
        "Target Post-Incident Conversion Rate (%)",
        min_value=float(max(0.5, round(i_cr, 1))),
        max_value=5.0,
        value=3.5,
        step=0.1
    )
    avg_order_value = st.number_input("Average Order Value (AOV in $)", min_value=10, max_value=500, value=75, step=5)

# Calculate Projected Gain
simulated_orders = int(i_sessions * (target_cr / 100))
simulated_revenue = simulated_orders * avg_order_value
recovered_revenue = simulated_revenue - i_rev

with sim_col2:
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=simulated_revenue,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Projected Restored Revenue ($)"},
        delta={'reference': i_rev, 'increasing': {'color': "#00cc96"}},
        gauge={
            'axis': {'range': [None, b_rev * 1.3]},
            'bar': {'color': "#2684FF"},
            'steps': [
                {'range': [0, i_rev], 'color': "#333333"},
                {'range': [i_rev, b_rev], 'color': "#444444"}
            ],
            'threshold': {
                'line': {'color': "green", 'width': 4},
                'thickness': 0.75,
                'value': b_rev
            }
        }
    ))
    fig_gauge.update_layout(template="plotly_dark", height=280, margin=dict(l=20, r=20, t=50, b=20))
    st.plotly_chart(fig_gauge, use_container_width=True)

st.success(
    f"Targeting a **{target_cr:.1f}%** CR at **${avg_order_value}** AOV yields **{simulated_orders:,}** orders and **${simulated_revenue:,.0f}** revenue "
    f"— directly unlocking **+${recovered_revenue:,.0f}** in incremental recovery."
)

st.markdown("---")

# --- 6. DRILL-DOWN TELEMETRY & DATA EXPORT ---
with st.expander("📂 Deep-Dive Telemetry Table & CSV Export"):
    st.markdown("Filter and export the granular root-cause decomposition matrix:")
    st.dataframe(results_df, use_container_width=True)
    
    csv_bytes = results_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Diagnostic Matrix (CSV)",
        data=csv_bytes,
        file_name="root_cause_analysis_report.csv",
        mime="text/csv",
    )