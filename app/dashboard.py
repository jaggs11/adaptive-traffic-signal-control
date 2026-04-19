import os
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="Neuro-Fuzzy Traffic Dashboard", layout="wide")
st.title("Neuro-Fuzzy Traffic Signal Control Dashboard")

PROCESSED_DIR = "data/processed"
CMP_PATH = os.path.join(PROCESSED_DIR, "comparison.csv")


def load_csv(path):
    if os.path.exists(path):
        return pd.read_csv(path)
    return pd.DataFrame()


# --- Single latest run (existing behavior) ---
st.header("Latest Run Summary")
latest_metrics = load_csv(os.path.join(PROCESSED_DIR, "run_metrics.csv"))
latest_steps = load_csv(os.path.join(PROCESSED_DIR, "step_log.csv"))

if not latest_metrics.empty:
    st.dataframe(latest_metrics, width="stretch")
else:
    st.info("No latest run_metrics.csv found. Run: python -m src.main")

if not latest_steps.empty:
    fig_latest = px.line(
        latest_steps,
        x="step",
        y=["total_queue", "total_wait"],
        title="Latest Run: Total Queue & Total Wait"
    )
    st.plotly_chart(fig_latest, use_container_width=True)
else:
    st.info("No latest step_log.csv found.")


# --- All 3 modes comparison ---
st.header("Controller Comparison (Fixed vs Fuzzy vs ANFIS)")

cmp_df = load_csv(CMP_PATH)
if cmp_df.empty:
    st.warning("No comparison.csv found. Run: python -m src.run_all")
else:
    st.subheader("Comparison Table")
    st.dataframe(cmp_df, width="stretch")

    c1, c2, c3 = st.columns(3)

    with c1:
        fig_wait = px.bar(cmp_df, x="mode", y="avg_total_wait", title="Avg Total Wait (lower is better)")
        st.plotly_chart(fig_wait, use_container_width=True)

    with c2:
        fig_queue = px.bar(cmp_df, x="mode", y="avg_total_queue", title="Avg Total Queue (lower is better)")
        st.plotly_chart(fig_queue, use_container_width=True)

    with c3:
        fig_thr = px.bar(cmp_df, x="mode", y="throughput", title="Throughput (higher is better)")
        st.plotly_chart(fig_thr, use_container_width=True)


# --- Per-mode step logs ---
st.header("Per-Mode Step Logs")
mode = st.selectbox("Select mode", ["fixed", "fuzzy", "anfis"])
mode_steps = load_csv(os.path.join(PROCESSED_DIR, f"step_log_{mode}.csv"))

if mode_steps.empty:
    st.info(f"No step_log_{mode}.csv found. Run: python -m src.run_all")
else:
    fig_mode = px.line(
        mode_steps,
        x="step",
        y=["total_queue", "total_wait"],
        title=f"{mode.upper()} Step Log: Total Queue & Total Wait"
    )
    st.plotly_chart(fig_mode, use_container_width=True)
    st.dataframe(mode_steps.tail(30), width="stretch")