import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="E-Commerce Root Cause Finder", layout="wide")

st.title("🛒 E-Commerce Performance & Root Cause Engine")
st.write("Automatically scans sales telemetry and isolates root causes behind conversion drops.")

# 1. Load Data
df = pd.read_csv("store_data.csv")

base = df[df["period"] == "Baseline"]
inci = df[df["period"] == "Incident"]

# 2. Key Metrics
b_sessions, i_sessions = base["sessions"].sum(), inci["sessions"].sum()
b_orders, i_orders = base["orders"].sum(), inci["orders"].sum()
b_rev, i_rev = base["revenue"].sum(), inci["revenue"].sum()

b_cr = (b_orders / b_sessions) * 100
i_cr = (i_orders / i_sessions) * 100

st.header("1. High-Level Performance")
col1, col2, col3 = st.columns(3)
col1.metric("Total Revenue ($)", f"${i_rev:,.0f}", f"{((i_rev - b_rev) / b_rev)*100:.1f}%")
col2.metric("Total Sessions", f"{i_sessions:,}", f"{((i_sessions - b_sessions) / b_sessions)*100:.1f}%")
col3.metric("Conversion Rate (%)", f"{i_cr:.2f}%", f"{i_cr - b_cr:.2f}%")

st.markdown("---")

# 3. Automated Diagnostic Slicing
st.header("2. Root Cause Slicing Analysis")

dimensions = ["browser", "device", "gateway"]
results = []

for dim in dimensions:
    b_group = base.groupby(dim).agg({"sessions": "sum", "orders": "sum"}).reset_index()
    i_group = inci.groupby(dim).agg({"sessions": "sum", "orders": "sum"}).reset_index()
    
    merged = pd.merge(b_group, i_group, on=dim, suffixes=("_base", "_inci"))
    merged["cr_base"] = merged["orders_base"] / merged["sessions_base"]
    merged["cr_inci"] = merged["orders_inci"] / merged["sessions_inci"]
    
    # Impact score: (Delta CR) * (Session Share)
    merged["loss_score"] = (merged["cr_inci"] - merged["cr_base"]) * (merged["sessions_inci"] / i_sessions)
    
    for _, row in merged.iterrows():
        results.append({
            "Dimension": dim,
            "Segment": row[dim],
            "Baseline CR": f"{row['cr_base']*100:.2f}%",
            "Incident CR": f"{row['cr_inci']*100:.2f}%",
            "CR Delta": f"{(row['cr_inci'] - row['cr_base'])*100:.2f}%",
            "Loss Score": row["loss_score"]
        })

results_df = pd.DataFrame(results).sort_values(by="Loss Score", ascending=True)

# Highlight primary issue
worst = results_df.iloc[0]
st.error(f"🚨 **Primary Root Cause Detected:** `{worst['Dimension']} = {worst['Segment']}` suffered a severe drop of **{worst['CR Delta']}**, driving the portfolio failure.")

st.dataframe(results_df, use_container_width=True)

# Chart
fig = px.bar(
    results_df,
    x="Segment",
    y="Loss Score",
    color="Dimension",
    title="Contribution Loss by Segment (Largest negative bar = main problem)"
)
st.plotly_chart(fig, use_container_width=True)