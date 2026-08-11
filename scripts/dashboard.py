import streamlit as st
import pandas as pd
import json
import os
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

# ─── PAGE CONFIG ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Day 13 · AI Observability - Team B2",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── GLOBAL CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Import font */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* Reset & root */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* Dark background for the whole app */
.stApp {
    background: linear-gradient(135deg, #0a0e1a 0%, #0d1b2a 50%, #0a1628 100%);
    background-attachment: fixed;
}

/* Hide default streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }

/* Glass card style */
div[data-testid="metric-container"] {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(255,255,255,0.10) !important;
    border-radius: 16px !important;
    padding: 20px !important;
    backdrop-filter: blur(12px) !important;
    transition: all 0.3s ease !important;
}
div[data-testid="metric-container"]:hover {
    border-color: rgba(99,179,237,0.4) !important;
    background: rgba(255,255,255,0.08) !important;
}

/* Metric label */
div[data-testid="metric-container"] label {
    color: #94a3b8 !important;
    font-size: 0.75rem !important;
    font-weight: 500 !important;
    letter-spacing: 0.05em !important;
    text-transform: uppercase !important;
}

/* Metric value */
div[data-testid="metric-container"] [data-testid="metric-value"] {
    color: #f1f5f9 !important;
    font-size: 2rem !important;
    font-weight: 700 !important;
}

/* Block container padding */
.block-container {
    padding: 2rem 3rem !important;
    max-width: 100% !important;
}

/* Column gap */
div[data-testid="column"] { padding: 0 0.5rem !important; }

/* Subheader overrides */
h3 { color: #e2e8f0 !important; font-weight: 600 !important; }

/* Caption text */
div[data-testid="caption"] { color: #64748b !important; }

/* Plotly charts transparent bg */
.js-plotly-plot { border-radius: 12px !important; }

/* Status badge OK */
.badge-ok {
    display:inline-block;
    background: rgba(16,185,129,0.15);
    border: 1px solid rgba(16,185,129,0.4);
    color: #10b981;
    border-radius: 20px;
    padding: 2px 12px;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}
.badge-warn {
    display:inline-block;
    background: rgba(245,158,11,0.15);
    border: 1px solid rgba(245,158,11,0.4);
    color: #f59e0b;
    border-radius: 20px;
    padding: 2px 12px;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}
.badge-err {
    display:inline-block;
    background: rgba(239,68,68,0.15);
    border: 1px solid rgba(239,68,68,0.4);
    color: #ef4444;
    border-radius: 20px;
    padding: 2px 12px;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}

/* Section divider */
.section-divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(99,179,237,0.3), transparent);
    margin: 2rem 0 1.5rem 0;
}
</style>
""", unsafe_allow_html=True)

# ─── PLOTLY THEME ──────────────────────────────────────────────────────────────
PLOT_BG   = "rgba(0,0,0,0)"
PAPER_BG  = "rgba(0,0,0,0)"
GRID_CLR  = "rgba(255,255,255,0.06)"
FONT_CLR  = "#94a3b8"

def base_layout(title="", yunit=""):
    return dict(
        plot_bgcolor=PLOT_BG,
        paper_bgcolor=PAPER_BG,
        font=dict(color=FONT_CLR, family="Inter", size=11),
        title=dict(text=title, font=dict(color="#e2e8f0", size=13), x=0),
        xaxis=dict(showgrid=False, zeroline=False, color=FONT_CLR,
                   tickfont=dict(size=10)),
        yaxis=dict(showgrid=True, gridcolor=GRID_CLR, zeroline=False,
                   color=FONT_CLR, tickfont=dict(size=10),
                   ticksuffix=" " + yunit if yunit else ""),
        margin=dict(l=10, r=10, t=30, b=10),
        height=220,
        showlegend=True,
        legend=dict(orientation="h", y=1.15, x=0,
                    font=dict(color=FONT_CLR, size=10)),
        hovermode="x unified",
    )

# ─── DATA LOADER ───────────────────────────────────────────────────────────────
@st.cache_data(ttl=15)
def load_data():
    log_path = "data/logs.jsonl"
    if not os.path.exists(log_path):
        return pd.DataFrame()
    try:
        records = [json.loads(l) for l in open(log_path, encoding="utf-8") if l.strip()]
        df = pd.DataFrame(records)
        if "ts" in df.columns:
            df["ts"] = pd.to_datetime(df["ts"], utc=True)
        return df
    except Exception as e:
        st.error(f"Lỗi đọc log: {e}")
        return pd.DataFrame()

df = load_data()

df_req  = df[df["event"] == "request_received"]  if not df.empty else pd.DataFrame()
df_resp = df[df["event"] == "response_sent"]     if not df.empty else pd.DataFrame()
df_err  = df[df["event"] == "request_failed"]    if not df.empty else pd.DataFrame()

# ─── HEADER ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="display:flex; align-items:center; gap:16px; margin-bottom:0.25rem;">
  <div style="background:linear-gradient(135deg,#3b82f6,#8b5cf6);
              width:44px; height:44px; border-radius:12px;
              display:flex; align-items:center; justify-content:center;
              font-size:22px; flex-shrink:0;">📡</div>
  <div>
    <h1 style="margin:0; font-size:1.6rem; font-weight:700;
               background:linear-gradient(90deg,#63b3ed,#a78bfa);
               -webkit-background-clip:text; -webkit-text-fill-color:transparent;">
      Day 13 · AI Observability
    </h1>
    <p style="margin:0; color:#475569; font-size:0.8rem;">
      Source: data/logs.jsonl &nbsp;|&nbsp; Time range: 60 min &nbsp;|&nbsp; Refresh: 15s
    </p>
  </div>
</div>
""", unsafe_allow_html=True)

if df.empty:
    st.markdown("""
    <div style="text-align:center; padding:80px 0; color:#475569;">
      <div style="font-size:48px; margin-bottom:16px;">🛰️</div>
      <p style="font-size:1.1rem;">Chưa có dữ liệu · Hãy bật API và chạy <code>python scripts/load_test.py</code></p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ─── TOP KPI ROW ───────────────────────────────────────────────────────────────
st.markdown('<div style="height:20px"></div>', unsafe_allow_html=True)

total_reqs  = len(df_req)
total_errs  = len(df_err)
error_rate  = (total_errs / total_reqs * 100) if total_reqs else 0
total_cost  = df_resp["cost_usd"].sum() if "cost_usd" in df_resp.columns else 0
p95         = df_resp["latency_ms"].quantile(0.95) if "latency_ms" in df_resp.columns and not df_resp.empty else 0
avg_quality = df_resp["quality_score"].mean() if "quality_score" in df_resp.columns and not df_resp.empty else 0

def slo_badge(ok: bool, ok_text="✅ SLO OK", warn_text="🚨 SLO BREACH"):
    if ok:
        return f'<span class="badge-ok">{ok_text}</span>'
    return f'<span class="badge-err">{warn_text}</span>'

k1, k2, k3, k4, k5 = st.columns(5)
with k1:
    st.metric("Total Requests", f"{total_reqs:,}")
with k2:
    st.metric("P95 Latency", f"{p95:.0f} ms")
    st.markdown(slo_badge(p95 <= 3000), unsafe_allow_html=True)
with k3:
    st.metric("Error Rate", f"{error_rate:.1f}%")
    st.markdown(slo_badge(error_rate <= 2), unsafe_allow_html=True)
with k4:
    st.metric("Total Cost", f"${total_cost:.4f}")
    st.markdown(slo_badge(total_cost <= 2.5), unsafe_allow_html=True)
with k5:
    st.metric("Avg Quality", f"{avg_quality:.2f}")
    st.markdown(slo_badge(avg_quality >= 0.75), unsafe_allow_html=True)

st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

# ─── ROW 1: LATENCY + TRAFFIC ──────────────────────────────────────────────────
c1, c2 = st.columns([1, 1])

with c1:
    st.markdown("##### 📶 Latency Percentiles (ms)")
    if not df_resp.empty and "latency_ms" in df_resp.columns:
        df_t = df_resp.set_index("ts").sort_index()
        p50_s  = df_t["latency_ms"].expanding().quantile(0.50)
        p95_s  = df_t["latency_ms"].expanding().quantile(0.95)
        p99_s  = df_t["latency_ms"].expanding().quantile(0.99)

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_t.index, y=p50_s,
            name="P50", line=dict(color="#3b82f6", width=2)))
        fig.add_trace(go.Scatter(x=df_t.index, y=p95_s,
            name="P95", line=dict(color="#f59e0b", width=2)))
        fig.add_trace(go.Scatter(x=df_t.index, y=p99_s,
            name="P99", line=dict(color="#ef4444", width=2)))
        # SLO threshold line
        fig.add_hline(y=3000, line_dash="dot",
            line_color="rgba(239,68,68,0.5)",
            annotation_text="SLO 3000ms",
            annotation_font_color="#ef4444",
            annotation_position="top right")
        fig.update_layout(**base_layout(yunit="ms"))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("Chưa có dữ liệu")

with c2:
    st.markdown("##### 🚦 Request Traffic (req/min)")
    if not df_req.empty:
        df_t = df_req.set_index("ts").sort_index()
        rpm_s = df_t.resample("1min").size().reset_index(name="count")

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=rpm_s["ts"], y=rpm_s["count"],
            name="req/min",
            marker=dict(
                color=rpm_s["count"],
                colorscale=[[0,"#1e40af"],[0.5,"#3b82f6"],[1,"#60a5fa"]],
                line_width=0,
            )
        ))
        fig.add_hline(y=1, line_dash="dot", line_color="rgba(16,185,129,0.5)",
            annotation_text="Min SLO 1 rpm",
            annotation_font_color="#10b981",
            annotation_position="top right")
        fig.update_layout(**base_layout(yunit="req"))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("Chưa có dữ liệu")

st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

# ─── ROW 2: ERRORS + COST ──────────────────────────────────────────────────────
c3, c4 = st.columns([1, 1])

with c3:
    st.markdown("##### 🔴 Error Rate & Breakdown (%)")
    # Gauge chart for error rate
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=error_rate,
        delta={"reference": 2, "increasing": {"color": "#ef4444"},
               "decreasing": {"color": "#10b981"}},
        number={"suffix": "%", "font": {"color": "#f1f5f9", "size": 36}},
        gauge={
            "axis": {"range": [0, 10], "tickcolor": "#475569",
                     "tickfont": {"color": "#475569"}},
            "bar": {"color": "#ef4444" if error_rate > 2 else "#10b981"},
            "bgcolor": "rgba(255,255,255,0.03)",
            "bordercolor": "rgba(255,255,255,0.1)",
            "steps": [
                {"range": [0, 2],  "color": "rgba(16,185,129,0.1)"},
                {"range": [2, 10], "color": "rgba(239,68,68,0.1)"},
            ],
            "threshold": {"line": {"color": "#f59e0b", "width": 3},
                          "value": 2},
        },
    ))
    fig.update_layout(
        plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
        font=dict(color=FONT_CLR), height=220,
        margin=dict(l=20, r=20, t=20, b=10),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    if not df_err.empty and "error_type" in df_err.columns:
        ec = df_err["error_type"].value_counts().reset_index()
        ec.columns = ["error_type", "count"]
        fig2 = go.Figure(go.Bar(
            x=ec["count"], y=ec["error_type"], orientation="h",
            marker=dict(color="#ef4444", opacity=0.8, line_width=0)
        ))
        fig2.update_layout(
            plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
            font=dict(color=FONT_CLR), height=120,
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis=dict(showgrid=False, zeroline=False, color=FONT_CLR),
            yaxis=dict(showgrid=False, zeroline=False, color=FONT_CLR),
        )
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
    else:
        st.markdown('<p style="color:#10b981; text-align:center; padding:8px;">🎉 Không có lỗi nào!</p>',
                    unsafe_allow_html=True)

with c4:
    st.markdown("##### 💰 Cost Over Time (USD)")
    if not df_resp.empty and "cost_usd" in df_resp.columns:
        df_t = df_resp.set_index("ts").sort_index()
        cost_min = df_t["cost_usd"].resample("1min").sum().reset_index()
        cost_min.columns = ["ts", "cost"]
        cost_min["cumulative"] = cost_min["cost"].cumsum()

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=cost_min["ts"], y=cost_min["cost"],
            name="cost/min",
            marker=dict(color="#a78bfa", opacity=0.7, line_width=0)
        ))
        fig.add_trace(go.Scatter(
            x=cost_min["ts"], y=cost_min["cumulative"],
            name="cumulative",
            line=dict(color="#f59e0b", width=2),
            yaxis="y2"
        ))
        fig.add_hline(y=2.5, line_dash="dot", line_color="rgba(239,68,68,0.5)",
            annotation_text="Budget $2.5",
            annotation_font_color="#ef4444",
            annotation_position="top right",
            yref="y2")
        layout = base_layout(yunit="$")
        layout.update(
            yaxis2=dict(overlaying="y", side="right",
                        showgrid=False, zeroline=False,
                        color=FONT_CLR, tickprefix="$",
                        tickfont=dict(size=10)),
        )
        fig.update_layout(**layout)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("Chưa có dữ liệu")

st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

# ─── ROW 3: TOKENS + QUALITY ───────────────────────────────────────────────────
c5, c6 = st.columns([1, 1])

with c5:
    st.markdown("##### 🔤 Input / Output Tokens")
    if not df_resp.empty and "tokens_in" in df_resp.columns:
        tokens_in  = int(df_resp["tokens_in"].sum())
        tokens_out = int(df_resp["tokens_out"].sum())
        total_tok  = tokens_in + tokens_out

        # Donut chart
        fig = go.Figure(go.Pie(
            labels=["Tokens In", "Tokens Out"],
            values=[tokens_in, tokens_out],
            hole=0.65,
            marker=dict(colors=["#3b82f6", "#8b5cf6"],
                        line=dict(color="rgba(0,0,0,0.4)", width=2)),
            textfont=dict(color="#e2e8f0"),
        ))
        fig.add_annotation(
            text=f"<b>{total_tok:,}</b><br><span style='font-size:9px'>total</span>",
            x=0.5, y=0.5, showarrow=False,
            font=dict(color="#f1f5f9", size=16)
        )
        fig.update_layout(
            plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
            font=dict(color=FONT_CLR), height=230,
            margin=dict(l=20, r=20, t=20, b=10),
            legend=dict(orientation="h", x=0.2, y=-0.05,
                        font=dict(color=FONT_CLR)),
            showlegend=True,
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        col_i, col_o = st.columns(2)
        col_i.metric("Tokens In",  f"{tokens_in:,}")
        col_o.metric("Tokens Out", f"{tokens_out:,}")
    else:
        st.info("Chưa có dữ liệu")

with c6:
    st.markdown("##### ⭐ Quality Proxy (0–1)")
    if not df_resp.empty and "quality_score" in df_resp.columns:
        df_t = df_resp.set_index("ts").sort_index()
        q_series = df_t["quality_score"].resample("1min").mean().dropna().reset_index()
        q_series.columns = ["ts", "quality"]
        mean_q   = df_t["quality_score"].mean()

        fig = go.Figure()
        # Shaded good zone
        fig.add_hrect(y0=0.75, y1=1.0,
            fillcolor="rgba(16,185,129,0.06)",
            line_width=0,
            annotation_text="Good ≥ 0.75",
            annotation_position="top right",
            annotation_font_color="#10b981",
            annotation_font_size=10)
        fig.add_trace(go.Scatter(
            x=q_series["ts"], y=q_series["quality"],
            name="quality/min",
            mode="lines+markers",
            line=dict(color="#10b981", width=2),
            marker=dict(color="#10b981", size=5),
            fill="tozeroy",
            fillcolor="rgba(16,185,129,0.08)",
        ))
        fig.add_hline(y=0.75, line_dash="dot", line_color="rgba(16,185,129,0.5)",
            annotation_text="SLO 0.75",
            annotation_font_color="#10b981",
            annotation_position="bottom right")
        fig.add_hline(y=mean_q, line_dash="dash", line_color="#f59e0b",
            annotation_text=f"Mean {mean_q:.2f}",
            annotation_font_color="#f59e0b",
            annotation_position="top left")
        layout = base_layout()
        layout["yaxis"]["range"] = [0, 1.05]
        fig.update_layout(**layout)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("Chưa có dữ liệu")

# ─── FOOTER ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="section-divider"></div>
<p style="text-align:center; color:#334155; font-size:0.72rem;">
  Day 13 K3 Observability Lab · Nguồn: data/logs.jsonl · Thành viên C
</p>
""", unsafe_allow_html=True)
