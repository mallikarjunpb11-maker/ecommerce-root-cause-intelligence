import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from itertools import combinations

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Executive Root Cause Intelligence Console",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- CUSTOM THEME ---
st.markdown("""
<style>
.stApp {
    background: radial-gradient(circle at 10% 20%, rgb(15, 23, 42) 0%, rgb(10, 15, 29) 90.2%);
    color: #f8fafc;
}
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0b0f19 0%, #111827 100%) !important;
    border-right: 1px solid #1e293b;
}
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
div[data-testid="stMetric"] label { color: #94a3b8 !important; font-weight: 600; letter-spacing: 0.5px; }
div[data-testid="stMetric"] div[data-testid="stMetricValue"] { color: #f1f5f9 !important; font-weight: 700; }
h1 {
    background: linear-gradient(90deg, #38bdf8 0%, #818cf8 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 800 !important;
}
h2, h3 { color: #e2e8f0 !important; }
button[data-baseweb="tab"] { font-weight: 600; }
.stDownloadButton button {
    background: linear-gradient(90deg, #0284c7 0%, #2563eb 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 10px 24px !important;
    font-weight: 600 !important;
    box-shadow: 0 4px 12px rgba(2, 132, 199, 0.35) !important;
}
.stDownloadButton button:hover { opacity: 0.95; transform: scale(1.02); }
</style>
""", unsafe_allow_html=True)

# ==== LOGIC START (pure functions, no Streamlit calls) ====
DIMENSIONS = ["browser", "device", "gateway"]
NUMERIC_COLUMNS = ["sessions", "orders", "revenue"]
REQUIRED_COLUMNS = set(["period"] + DIMENSIONS + NUMERIC_COLUMNS)
PERIODS = ["Baseline", "Incident"]


def usd(x):
    """Dollar string that is safe inside Streamlit markdown (escapes the $ sign)."""
    sign = "-" if x < 0 else ""
    return f"{sign}\\${abs(x):,.0f}"


def plain_usd(x):
    sign = "-" if x < 0 else ""
    return f"{sign}${abs(x):,.0f}"


def pct_change(new, old):
    return (new - old) / old * 100 if old else 0.0


def clean_data(raw):
    d = raw.copy()
    for c in NUMERIC_COLUMNS:
        d[c] = pd.to_numeric(d[c], errors="coerce").fillna(0)
    for c in ["period"] + DIMENSIONS:
        d[c] = d[c].astype(str).str.strip()
    return d


def compute_slices(data, min_share=0.02):
    """Score every 1-way, 2-way and 3-way slice of the dimensions.

    Loss score = change in conversion rate (points) x slice share of incident sessions.
    Slices with identical numbers are collapsed into the most specific one.
    """
    base = data[data["period"] == "Baseline"]
    inci = data[data["period"] == "Incident"]
    i_sessions = inci["sessions"].sum()
    b_orders, b_rev = base["orders"].sum(), base["revenue"].sum()
    aov = b_rev / b_orders if b_orders > 0 else 0.0
    if base.empty or inci.empty or i_sessions <= 0:
        return pd.DataFrame()

    agg = dict(
        sessions=("sessions", "sum"),
        orders=("orders", "sum"),
        revenue=("revenue", "sum"),
    )
    parts = []
    for r in range(1, len(DIMENSIONS) + 1):
        for dims in combinations(DIMENSIONS, r):
            dims = list(dims)
            b = base.groupby(dims).agg(**agg).reset_index()
            i = inci.groupby(dims).agg(**agg).reset_index()
            m = b.merge(i, on=dims, suffixes=("_base", "_inci"))
            m = m[(m["sessions_base"] > 0) & (m["sessions_inci"] > 0)]
            if m.empty:
                continue
            share = m["sessions_inci"] / i_sessions
            m = m[share >= min_share]
            share = share[m.index]
            if m.empty:
                continue

            cr_base = m["orders_base"] / m["sessions_base"] * 100
            cr_inci = m["orders_inci"] / m["sessions_inci"] * 100
            delta = cr_inci - cr_base
            expected_orders = cr_base / 100 * m["sessions_inci"]
            lost = ((expected_orders - m["orders_inci"]) * aov).clip(lower=0)

            seg = m[dims[0]].astype(str)
            for d in dims[1:]:
                seg = seg + " + " + m[d].astype(str)

            sig = (
                m["sessions_base"].round(0).astype(int).astype(str) + "|"
                + m["orders_base"].round(0).astype(int).astype(str) + "|"
                + m["sessions_inci"].round(0).astype(int).astype(str) + "|"
                + m["orders_inci"].round(0).astype(int).astype(str)
            )

            part = pd.DataFrame({
                "Depth": f"{r}-way",
                "Dimension": " + ".join(d.title() for d in dims),
                "Segment": seg,
                "Baseline CR (%)": cr_base.round(2),
                "Incident CR (%)": cr_inci.round(2),
                "CR Delta (%)": delta.round(2),
                "Loss Contribution Score": (delta * share).round(4),
                "Estimated Lost Revenue ($)": lost.round(0).astype(int),
                "Share of Incident Traffic (%)": (share * 100).round(1),
                "_n": r,
                "_sig": sig,
            }, index=m.index)
            parts.append(part)

    if not parts:
        return pd.DataFrame()

    res = pd.concat(parts, ignore_index=True)

    # Collapse slices whose numbers are identical (the dimensions always occur together)
    groups = res.groupby("_sig")["Segment"].apply(list)
    res["Identical Slices"] = res["_sig"].map(lambda s: len(groups[s]))
    res["Identical To"] = res["_sig"].map(lambda s: ", ".join(groups[s]))
    res = res.sort_values("_n", ascending=False, kind="stable").drop_duplicates("_sig", keep="first")
    res = res.sort_values(
        ["Loss Contribution Score", "Estimated Lost Revenue ($)"],
        ascending=[True, False],
        kind="stable",
    ).reset_index(drop=True)
    return res


def segment_mask(data, dimension, segment):
    """Boolean mask of the rows that belong to a slice, e.g. 'Browser + Device', 'Safari + iOS'."""
    dims = [d.lower() for d in dimension.split(" + ")]
    vals = segment.split(" + ")
    mask = pd.Series(True, index=data.index)
    for d, v in zip(dims, vals):
        mask = mask & (data[d].astype(str) == v)
    return mask


def period_stats(d):
    g = d.groupby("period")[NUMERIC_COLUMNS].sum().reindex(PERIODS).fillna(0)
    g["CR (%)"] = np.where(g["sessions"] > 0, g["orders"] / g["sessions"] * 100, 0.0)
    return g


def build_waterfall(res, b_rev, i_rev, k=5):
    """Baseline revenue -> losses of the most-affected 3-way cohorts -> other effects -> incident revenue.

    3-way cohorts do not overlap, so their losses can be added safely.
    """
    cohorts = res[res["_n"] == len(DIMENSIONS)]
    cohorts = cohorts[cohorts["Estimated Lost Revenue ($)"] > 0]
    cohorts = cohorts.sort_values("Estimated Lost Revenue ($)", ascending=False).head(k)
    if cohorts.empty:
        return None
    losses = cohorts["Estimated Lost Revenue ($)"].astype(float).tolist()
    residual = i_rev - b_rev + sum(losses)
    names = ["Baseline revenue"] + cohorts["Segment"].tolist() + ["Other effects", "Incident revenue"]
    values = [b_rev] + [-v for v in losses] + [residual, i_rev]
    measures = ["absolute"] + ["relative"] * (len(losses) + 1) + ["total"]
    return names, values, measures


def build_insights(b_rev, i_rev, b_sessions, i_sessions, top):
    """Plain-English findings. `top` is the top row of the slice table (or None)."""
    out = []
    rev_chg = pct_change(i_rev, b_rev)
    sess_chg = pct_change(i_sessions, b_sessions)
    if rev_chg <= -5 and abs(sess_chg) < 5:
        out.append(
            f"Revenue changed **{rev_chg:.1f}%** while traffic moved only **{sess_chg:.1f}%**, "
            "so this is a **conversion problem, not a traffic problem**."
        )
    elif rev_chg <= -5:
        out.append(
            f"Revenue changed **{rev_chg:.1f}%** and sessions changed **{sess_chg:.1f}%**, "
            "so both traffic and conversion contribute to the drop."
        )
    else:
        out.append(
            f"Revenue changed **{rev_chg:.1f}%** and sessions changed **{sess_chg:.1f}%**: "
            "no major revenue drop in the current selection."
        )

    if top is not None and top["CR Delta (%)"] < 0:
        gap = b_rev - i_rev
        share_txt = ""
        if gap > 0:
            share = min(top["Estimated Lost Revenue ($)"] / gap, 1.0) * 100
            share_txt = f" That is about **{share:.0f}%** of the total revenue drop."
        out.append(
            f"**{top['Segment']}** is the main driver: conversion fell from "
            f"**{top['Baseline CR (%)']}%** to **{top['Incident CR (%)']}%** "
            f"({top['CR Delta (%)']:.2f} points), costing an estimated "
            f"**{usd(top['Estimated Lost Revenue ($)'])}**.{share_txt}"
        )
        others = int(top["Identical Slices"]) - 1
        if others > 0:
            out.append(
                f"{others} other slices show identical numbers, so these dimensions always "
                "occur together in this data and the cause cannot be narrowed further."
            )
    return out
# ==== LOGIC END ====


@st.cache_data(show_spinner=False)
def load_default():
    return pd.read_csv("store_data.csv")


cached_slices = st.cache_data(show_spinner=False)(compute_slices)

# --- 1. DATA INGESTION ---
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/3094/3094837.png", width=60)
st.sidebar.title("Telemetry Controls")
st.sidebar.markdown("Filter sessions across funnel parameters:")

df = load_default()
using_demo = True
uploaded_file = st.sidebar.file_uploader("📥 Ingest Custom CSV", type=["csv"])
if uploaded_file is not None:
    try:
        uploaded_df = pd.read_csv(uploaded_file)
        missing = REQUIRED_COLUMNS - set(uploaded_df.columns)
        if missing:
            st.sidebar.error("Missing columns: " + ", ".join(sorted(missing)))
        else:
            df = uploaded_df
            using_demo = False
            st.sidebar.success("Custom telemetry ingested!")
    except Exception:
        st.sidebar.error("Could not read that CSV file.")

df = clean_data(df)
if not set(PERIODS).issubset(set(df["period"])):
    st.error("The data needs a 'period' column with both 'Baseline' and 'Incident' values.")
    st.stop()

# --- 2. SIDEBAR CONTROLS ---
selected_browsers = st.sidebar.multiselect(
    "Browser Environment", options=sorted(df["browser"].unique()), default=sorted(df["browser"].unique())
)
selected_devices = st.sidebar.multiselect(
    "Client Device Tier", options=sorted(df["device"].unique()), default=sorted(df["device"].unique())
)
selected_gateways = st.sidebar.multiselect(
    "Payment Gateway Channel", options=sorted(df["gateway"].unique()), default=sorted(df["gateway"].unique())
)

with st.sidebar.expander("⚙️ Analysis settings"):
    min_share_pct = st.slider("Ignore slices below this share of traffic (%)", 0.0, 10.0, 2.0, 0.5)
    alert_threshold = st.slider("Raise alert when conversion drops by (points)", 0.1, 3.0, 0.5, 0.1)
    top_n = st.slider("Segments shown in the chart", 3, 15, 8)

filtered_df = df[
    df["browser"].isin(selected_browsers)
    & df["device"].isin(selected_devices)
    & df["gateway"].isin(selected_gateways)
]

if filtered_df.empty:
    st.warning("⚠️ No data matches the selected filters. Please widen your selection.")
    st.stop()

base = filtered_df[filtered_df["period"] == "Baseline"]
inci = filtered_df[filtered_df["period"] == "Incident"]
if base.empty or inci.empty:
    st.warning("⚠️ The current filters leave no Baseline or Incident data. Please widen your selection.")
    st.stop()

# --- 3. CORE NUMBERS ---
b_sessions, i_sessions = base["sessions"].sum(), inci["sessions"].sum()
b_orders, i_orders = base["orders"].sum(), inci["orders"].sum()
b_rev, i_rev = base["revenue"].sum(), inci["revenue"].sum()
b_cr = (b_orders / b_sessions * 100) if b_sessions > 0 else 0.0
i_cr = (i_orders / i_sessions * 100) if i_sessions > 0 else 0.0
b_aov = (b_rev / b_orders) if b_orders > 0 else 0.0

results = cached_slices(filtered_df, min_share_pct / 100)
has_results = not results.empty
top = results.iloc[0] if has_results else None

# --- HEADER ---
st.title("🛒 E-Commerce Root Cause Intelligence Engine")
st.markdown("Automated diagnostic system isolating conversion rate degradation across high-dimensional traffic slices.")
if using_demo:
    st.caption("ℹ️ The demo data is synthetic and contains an injected incident. Upload your own CSV in the sidebar.")

tab_overview, tab_root, tab_sim, tab_data = st.tabs(
    ["📊 Overview", "🔎 Root Cause", "💡 Simulator", "📂 Data"]
)

# ======================= TAB 1: OVERVIEW =======================
with tab_overview:
    st.subheader("Executive Funnel Telemetry")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Gross Incident Revenue", f"${i_rev:,.0f}", f"{pct_change(i_rev, b_rev):+.1f}% vs Baseline")
    c2.metric("Total Funnel Sessions", f"{i_sessions:,.0f}", f"{pct_change(i_sessions, b_sessions):+.1f}% vs Baseline")
    c3.metric("Observed Conversion Rate", f"{i_cr:.2f}%", f"{i_cr - b_cr:+.2f} pts vs Baseline")
    c4.metric("Orders Processed", f"{i_orders:,.0f}", f"{pct_change(i_orders, b_orders):+.1f}% vs Baseline")

    st.markdown("---")
    st.subheader("What happened?")
    if not has_results:
        st.info("Not enough data in the current selection to decompose the drop. Try lowering the traffic-share setting.")
    else:
        if top["CR Delta (%)"] <= -alert_threshold:
            st.error(
                f"🚨 **Top driver:** `{top['Segment']}` ({top['Dimension']}) — conversion fell "
                f"**{abs(top['CR Delta (%)']):.2f} points** "
                f"({top['Baseline CR (%)']}% → {top['Incident CR (%)']}%), "
                f"an estimated **{usd(top['Estimated Lost Revenue ($)'])}** in lost revenue."
            )
        else:
            st.success("✅ No segment shows a material conversion drop in the current selection.")

        st.info("\n".join(
            f"- {line}" for line in build_insights(b_rev, i_rev, b_sessions, i_sessions, top)
        ))

        wf = build_waterfall(results, b_rev, i_rev, k=5)
        if wf is not None:
            names, values, measures = wf
            fig_wf = go.Figure(go.Waterfall(
                x=names,
                y=values,
                measure=measures,
                text=[plain_usd(v) for v in values],
                textposition="outside",
                connector={"line": {"color": "#475569"}},
                increasing={"marker": {"color": "#22c55e"}},
                decreasing={"marker": {"color": "#f43f5e"}},
                totals={"marker": {"color": "#38bdf8"}},
            ))
            fig_wf.update_layout(
                title="Revenue bridge: baseline to incident (by non-overlapping cohort)",
                template="plotly_dark",
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#e2e8f0"),
                showlegend=False,
                yaxis_title="Revenue ($)",
                margin=dict(t=60, b=40),
            )
            st.plotly_chart(fig_wf, use_container_width=True)

# ======================= TAB 2: ROOT CAUSE =======================
with tab_root:
    st.subheader("Automated Root Cause Decomposition")
    if not has_results:
        st.info("Not enough data in the current selection to decompose the drop.")
    else:
        plot_df = results[results["Loss Contribution Score"] < 0].head(top_n).copy()
        if plot_df.empty:
            st.success("✅ No segment shows a conversion decline in the current selection.")
        else:
            plot_df["Loss Magnitude"] = -plot_df["Loss Contribution Score"]
            fig_bar = px.bar(
                plot_df,
                x="Loss Magnitude",
                y="Segment",
                color="Depth",
                orientation="h",
                text="CR Delta (%)",
                hover_data=["Dimension", "Baseline CR (%)", "Incident CR (%)", "Estimated Lost Revenue ($)"],
                title="Segments ranked by traffic-weighted conversion loss (longer bar = worse)",
                template="plotly_dark",
            )
            fig_bar.update_traces(texttemplate="%{text:.2f} pts", textposition="outside")
            fig_bar.update_yaxes(categoryorder="array", categoryarray=list(plot_df["Segment"])[::-1])
            fig_bar.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#e2e8f0"),
                xaxis_title="Loss score (change in conversion points x share of traffic)",
            )

            selected_segment = None
            select_supported = True
            try:
                event = st.plotly_chart(
                    fig_bar,
                    use_container_width=True,
                    on_select="rerun",
                    selection_mode="points",
                    key="rc_chart",
                )
                try:
                    points = event["selection"]["points"]
                except Exception:
                    points = []
                if points:
                    clicked = points[0].get("y")
                    if clicked in set(plot_df["Segment"]):
                        selected_segment = clicked
            except TypeError:
                # Older Streamlit versions have no click selection: fall back to a dropdown
                select_supported = False
                st.plotly_chart(fig_bar, use_container_width=True)

            if select_supported:
                st.caption("👆 Click a bar to drill down. The top driver is shown by default.")
            else:
                selected_segment = st.selectbox("Inspect a segment", list(plot_df["Segment"]))
            if selected_segment is None:
                selected_segment = plot_df.iloc[0]["Segment"]

            # ---- Drill-down panel ----
            sel = results[results["Segment"] == selected_segment].iloc[0]
            st.markdown(f"### 🔬 Drill-down: `{sel['Segment']}`")
            mask = segment_mask(filtered_df, sel["Dimension"], sel["Segment"])
            seg_stats = period_stats(filtered_df[mask])
            rest_stats = period_stats(filtered_df[~mask])

            d1, d2, d3, d4 = st.columns(4)
            d1.metric("Baseline CR", f"{sel['Baseline CR (%)']}%")
            d2.metric("Incident CR", f"{sel['Incident CR (%)']}%", f"{sel['CR Delta (%)']:+.2f} pts")
            d3.metric("Estimated lost revenue", f"${sel['Estimated Lost Revenue ($)']:,.0f}")
            d4.metric("Share of incident traffic", f"{sel['Share of Incident Traffic (%)']}%")

            others = [s for s in str(sel["Identical To"]).split(", ") if s != sel["Segment"]]
            if others:
                st.info("Slices with identical numbers (they always occur together here): " + ", ".join(others))

            cmp_df = pd.concat([
                seg_stats.reset_index().assign(Group=sel["Segment"]),
                rest_stats.reset_index().assign(Group="All other traffic"),
            ])
            fig_cmp = px.bar(
                cmp_df,
                x="period",
                y="CR (%)",
                color="Group",
                barmode="group",
                text_auto=".2f",
                title="Conversion rate: this segment vs everything else",
                color_discrete_map={sel["Segment"]: "#f43f5e", "All other traffic": "#38bdf8"},
                template="plotly_dark",
            )
            fig_cmp.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#e2e8f0"),
                xaxis_title="",
            )
            st.plotly_chart(fig_cmp, use_container_width=True)

            st.dataframe(
                seg_stats.reset_index().rename(columns={"period": "Period"}).round(2),
                use_container_width=True,
                hide_index=True,
            )

# ======================= TAB 3: SIMULATOR =======================
with tab_sim:
    st.subheader("What-If Recovery Simulator")

    st.markdown("#### A. Fix only the top driver")
    if has_results and top["CR Delta (%)"] < 0 and top["Estimated Lost Revenue ($)"] > 0:
        recover_pct = st.slider(
            f"How much of the lost conversion in `{top['Segment']}` do you recover? (%)", 0, 100, 100, 5
        )
        recovered_a = top["Estimated Lost Revenue ($)"] * recover_pct / 100
        st.success(
            f"Recovering **{recover_pct}%** of the lost conversion in `{top['Segment']}` "
            f"adds an estimated **{usd(recovered_a)}** in revenue."
        )
    else:
        st.info("No material top driver to simulate in the current selection.")

    st.markdown("#### B. Site-wide target")
    lo, hi = 0.1, float(max(5.0, round(max(b_cr, i_cr) + 1.0, 1)))
    default_target = float(min(max(round(b_cr, 1), lo), hi))
    sim1, sim2 = st.columns([1, 2])
    with sim1:
        target_cr = st.slider("Target conversion rate (%)", lo, hi, default_target, 0.1)
        aov_default = int(min(max(round(b_aov), 1), 1000)) if b_aov > 0 else 75
        avg_order_value = st.number_input(
            "Average Order Value ($)", min_value=1, max_value=1000, value=aov_default, step=5
        )

    simulated_orders = int(i_sessions * (target_cr / 100))
    simulated_revenue = simulated_orders * avg_order_value
    recovered_b = simulated_revenue - i_rev

    with sim2:
        fig_sim = go.Figure(go.Bar(
            x=["Incident revenue", "Projected revenue", "Baseline revenue"],
            y=[i_rev, simulated_revenue, b_rev],
            text=[plain_usd(i_rev), plain_usd(simulated_revenue), plain_usd(b_rev)],
            textposition="outside",
            marker_color=["#f43f5e", "#38bdf8", "#64748b"],
        ))
        fig_sim.update_layout(
            template="plotly_dark",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e2e8f0"),
            height=320,
            margin=dict(t=30, b=30),
            yaxis_title="Revenue ($)",
        )
        st.plotly_chart(fig_sim, use_container_width=True)

    st.success(
        f"Targeting a **{target_cr:.1f}%** conversion rate at **{usd(avg_order_value)}** AOV gives "
        f"**{simulated_orders:,}** orders and **{usd(simulated_revenue)}** revenue, "
        f"a change of **{usd(recovered_b)}** vs the incident period."
    )
    if b_rev > 0 and simulated_revenue > b_rev * 1.001:
        st.warning("This target is above your pre-incident baseline, so the extra revenue is growth, not recovery.")

# ======================= TAB 4: DATA =======================
with tab_data:
    st.subheader("Diagnostic Matrix")
    if has_results:
        display_cols = [
            "Depth", "Dimension", "Segment", "Baseline CR (%)", "Incident CR (%)", "CR Delta (%)",
            "Loss Contribution Score", "Estimated Lost Revenue ($)", "Share of Incident Traffic (%)",
            "Identical Slices",
        ]
        table_df = results[display_cols]
        st.dataframe(table_df, use_container_width=True, hide_index=True)
        st.download_button(
            label="📥 Download Diagnostic Matrix (CSV)",
            data=table_df.to_csv(index=False).encode("utf-8"),
            file_name="root_cause_analysis_report.csv",
            mime="text/csv",
        )
    else:
        st.info("No diagnostic matrix for the current selection.")

    with st.expander("📘 How the analysis works"):
        st.markdown(
            "1. Sessions are split into **Baseline** and **Incident** periods.\n"
            "2. Every 1-way, 2-way and 3-way combination of browser, device and gateway is scored.\n"
            "3. **Loss score** = change in conversion rate (points) x the slice's share of incident sessions.\n"
            "4. **Estimated lost revenue** = (orders expected at baseline conversion minus actual orders) x baseline AOV.\n"
            "5. Slices below the traffic-share setting are ignored, and slices with identical numbers are merged into the most specific one.\n"
            "6. Slices overlap, so scores are not additive. The waterfall uses non-overlapping 3-way cohorts instead.\n"
            "7. The tool shows **where** conversion broke, not **why**."
        )

    with st.expander("🗃️ Filtered raw data (first 500 rows)"):
        st.dataframe(filtered_df.head(500), use_container_width=True, hide_index=True)