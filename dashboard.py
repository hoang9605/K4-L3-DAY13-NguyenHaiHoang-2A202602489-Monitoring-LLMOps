"""Live six-panel dashboard for the lab's structured JSONL logs."""

from __future__ import annotations

import json
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st
import yaml

ROOT = Path(__file__).resolve().parent
CONFIG = yaml.safe_load((ROOT / "config" / "dashboard.yaml").read_text(encoding="utf-8"))["dashboard"]
PANELS = {panel["id"]: panel for panel in CONFIG["panels"]}
LOG_FILE = ROOT / PANELS["latency"]["source"]

st.set_page_config(page_title=CONFIG["title"], layout="wide")


def load_window() -> pd.DataFrame:
    """Read the current UTC window on every refresh; skip incomplete JSONL lines."""
    if not LOG_FILE.exists():
        return pd.DataFrame()
    rows = []
    with LOG_FILE.open(encoding="utf-8") as handle:
        for line in handle:
            try:
                if line.strip():
                    rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    if not rows:
        return pd.DataFrame()
    frame = pd.DataFrame(rows)
    frame["ts"] = pd.to_datetime(frame["ts"], utc=True, errors="coerce")
    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(minutes=CONFIG["time_range_minutes"])
    frame = frame.loc[frame["ts"].notna() & (frame["ts"] >= cutoff)].copy()
    frame["minute"] = frame["ts"].dt.floor("min")
    return frame


def event_rows(frame: pd.DataFrame, event: str) -> pd.DataFrame:
    return frame.loc[frame["event"] == event].copy()


def numeric(frame: pd.DataFrame, field: str) -> pd.Series:
    if field not in frame:
        return pd.Series(dtype="float64", index=frame.index)
    return pd.to_numeric(frame[field], errors="coerce")


def line_chart(data: pd.DataFrame, fields: list[str], threshold: float, unit: str, height: int = 225):
    long = data.reset_index().melt(id_vars="minute", value_vars=fields, var_name="Series", value_name="Value")
    long["utc"] = long["minute"].dt.strftime("%Y-%m-%d %H:%M UTC")
    series = (
        alt.Chart(long)
        .mark_line(point=True)
        .encode(
            x=alt.X("minute:T", title="Time (UTC)", scale=alt.Scale(type="utc")),
            y=alt.Y("Value:Q", title=unit),
            color=alt.Color("Series:N"),
            tooltip=[alt.Tooltip("utc:N", title="UTC"), "Series:N", alt.Tooltip("Value:Q", format=".3f")],
        )
    )
    rule = alt.Chart(pd.DataFrame({"threshold": [threshold]})).mark_rule(color="#e45756", strokeDash=[6, 4]).encode(y="threshold:Q")
    return (series + rule).properties(height=height)


def panel_heading(panel_id: str) -> dict:
    panel = PANELS[panel_id]
    st.subheader(panel["title"])
    st.caption(f"Unit: {panel['unit']} · Window: {CONFIG['time_range_minutes']} min UTC · Threshold: {panel['threshold']['aggregation']} {panel['threshold']['operator']} {panel['threshold']['value']}")
    return panel


def latency_panel(frame: pd.DataFrame) -> None:
    panel = panel_heading("latency")
    responses = event_rows(frame, "response_sent")
    responses["latency_ms"] = numeric(responses, "latency_ms")
    responses["ttft_ms"] = numeric(responses, "ttft_ms")
    responses = responses.dropna(subset=["latency_ms"])
    if responses.empty:
        st.info("No responses in the current window.")
        return
    a, b, c, d = st.columns(4)
    a.metric("P50", f"{responses['latency_ms'].quantile(.50):,.0f} ms")
    b.metric("P95", f"{responses['latency_ms'].quantile(.95):,.0f} ms")
    c.metric("P99", f"{responses['latency_ms'].quantile(.99):,.0f} ms")
    d.metric("TTFT P95", f"{responses['ttft_ms'].quantile(.95):,.0f} ms")
    by_minute = responses.groupby("minute").agg(
        P50=("latency_ms", lambda s: s.quantile(.50)),
        P95=("latency_ms", lambda s: s.quantile(.95)),
        P99=("latency_ms", lambda s: s.quantile(.99)),
        TTFT_P95=("ttft_ms", lambda s: s.quantile(.95)),
    )
    st.altair_chart(line_chart(by_minute, ["P50", "P95", "P99", "TTFT_P95"], panel["threshold"]["value"], "ms"), use_container_width=True)


def traffic_panel(frame: pd.DataFrame) -> None:
    panel = panel_heading("traffic")
    requests = event_rows(frame, "request_received")
    st.metric("Requests in window", len(requests))
    if requests.empty:
        st.info("No requests in the current window.")
        return
    per_minute = requests.groupby("minute").size().to_frame("Requests/min")
    st.altair_chart(line_chart(per_minute, ["Requests/min"], panel["threshold"]["value"], "requests/min"), use_container_width=True)


def errors_panel(frame: pd.DataFrame) -> None:
    panel = panel_heading("errors")
    received = event_rows(frame, "request_received")
    failed = event_rows(frame, "request_failed")
    error_rate = len(failed) / len(received) * 100 if len(received) else 0.0
    # tool_success is emitted by both response_sent and request_failed.
    attempts = frame.loc[frame.get("tool_success", pd.Series(index=frame.index, dtype=object)).notna()].copy()
    success = attempts["tool_success"].eq(True).sum() / len(attempts) * 100 if len(attempts) else None
    a, b = st.columns(2)
    a.metric("Error rate", f"{error_rate:.1f}%")
    b.metric("Retrieval success", f"{success:.1f}%" if success is not None else "N/A")
    if len(received):
        counts = received.groupby("minute").size().rename("received")
        failures = failed.groupby("minute").size().rename("failed")
        rate = pd.concat([counts, failures], axis=1).fillna(0)
        rate["Error rate %"] = rate["failed"].div(rate["received"].where(rate["received"] > 0)).mul(100)
        st.altair_chart(line_chart(rate, ["Error rate %"], panel["threshold"]["value"], "%", 175), use_container_width=True)
    if len(attempts):
        retrieval = attempts.groupby("minute")["tool_success"].apply(lambda s: s.eq(True).mean() * 100).to_frame("Retrieval success %")
        st.altair_chart(line_chart(retrieval, ["Retrieval success %"], 90, "%", 140), use_container_width=True)
        st.caption("Retrieval success threshold: ≥ 90% (config/slo.yaml)")
    breakdown = failed.get("error_type", pd.Series(dtype=str)).value_counts()
    st.caption("Error types: " + (", ".join(f"{name}: {count}" for name, count in breakdown.items()) if len(breakdown) else "none"))


def cost_panel(frame: pd.DataFrame) -> None:
    panel = panel_heading("cost")
    responses = event_rows(frame, "response_sent")
    responses["cost_usd"] = numeric(responses, "cost_usd")
    st.metric("Total cost", f"${responses['cost_usd'].sum():.4f}")
    if responses.empty:
        st.info("No responses in the current window.")
        return
    per_minute = responses.groupby("minute")["cost_usd"].sum().to_frame("Cost/min USD")
    per_minute["Cumulative USD"] = per_minute["Cost/min USD"].cumsum()
    st.altair_chart(line_chart(per_minute, ["Cumulative USD"], panel["threshold"]["value"], "USD"), use_container_width=True)
    st.caption("Cost/min: " + ", ".join(f"{minute:%H:%M} ${value:.4f}" for minute, value in per_minute["Cost/min USD"].tail(5).items()))


def tokens_panel(frame: pd.DataFrame) -> None:
    panel = panel_heading("tokens")
    responses = event_rows(frame, "response_sent")
    for field in ("tokens_in", "tokens_out"):
        responses[field] = numeric(responses, field)
    input_total = responses["tokens_in"].sum()
    output_total = responses["tokens_out"].sum()
    a, b, c = st.columns(3)
    a.metric("Input", f"{input_total:,.0f}")
    b.metric("Output", f"{output_total:,.0f}")
    c.metric("Combined", f"{input_total + output_total:,.0f}")
    if responses.empty:
        st.info("No responses in the current window.")
        return
    by_minute = responses.groupby("minute")[["tokens_in", "tokens_out"]].sum()
    cumulative = by_minute.cumsum().rename(columns={"tokens_in": "Input cumulative", "tokens_out": "Output cumulative"})
    cumulative["Combined cumulative"] = cumulative.sum(axis=1)
    st.altair_chart(line_chart(cumulative, ["Input cumulative", "Output cumulative", "Combined cumulative"], panel["threshold"]["value"], "tokens"), use_container_width=True)
    st.caption("Input/output per minute: " + ", ".join(f"{minute:%H:%M} {int(row.tokens_in)}/{int(row.tokens_out)}" for minute, row in by_minute.tail(5).iterrows()))


def quality_panel(frame: pd.DataFrame) -> None:
    panel = panel_heading("quality")
    responses = event_rows(frame, "response_sent")
    responses["quality_score"] = numeric(responses, "quality_score")
    mean = responses["quality_score"].mean()
    st.metric("Mean quality proxy", f"{mean:.3f}" if pd.notna(mean) else "N/A")
    if responses.empty:
        st.info("No responses in the current window.")
        return
    by_minute = responses.groupby("minute")["quality_score"].mean().to_frame("Mean quality")
    st.altair_chart(line_chart(by_minute, ["Mean quality"], panel["threshold"]["value"], "score 0–1"), use_container_width=True)


@st.fragment(run_every=f"{CONFIG['refresh_seconds']}s")
def dashboard() -> None:
    frame = load_window()
    st.title(CONFIG["title"])
    st.caption(f"Source: {LOG_FILE.relative_to(ROOT)} · Last {CONFIG['time_range_minutes']} minutes (UTC) · Auto refresh: {CONFIG['refresh_seconds']} seconds · Updated: {pd.Timestamp.now(tz='UTC'):%Y-%m-%d %H:%M:%S} UTC")
    if frame.empty:
        st.warning("No log events in the last 60 minutes. Start the API and run python scripts/load_test.py.")
        return
    left, right = st.columns(2)
    with left:
        latency_panel(frame)
        errors_panel(frame)
        tokens_panel(frame)
    with right:
        traffic_panel(frame)
        cost_panel(frame)
        quality_panel(frame)


dashboard()
