import yfinance as yf
import warnings
warnings.filterwarnings("ignore")
import streamlit as st
import plotly.express as px
import pandas as pd

st.set_page_config(page_title="Heatmap", layout="wide")
st.title("Market Heatmap")
st.caption("Daily % change by sector. For education, not financial advice.")

SECTORS = {
    "Tech": ["AAPL", "MSFT", "NVDA", "AMD", "MU", "AVGO", "INTC"],
    "Communication": ["GOOGL", "META", "NFLX"],
    "Consumer": ["AMZN", "TSLA", "NKE", "HD"],
    "Finance": ["JPM", "BAC", "V", "MA"],
    "Health": ["LLY", "UNH", "JNJ"],
    "Energy": ["XOM", "CVX"],
    "ETFs": ["SPY", "QQQ", "IWM"],
}

@st.cache_data(ttl=300)
def load():
    rows = []
    for sector, tickers in SECTORS.items():
        for t in tickers:
            df = yf.download(t, period="5d", interval="1d", progress=False, multi_level_index=False)
            if df is None or len(df) < 2:
                continue
            close = float(df["Close"].iloc[-1])
            prev = float(df["Close"].iloc[-2])
            rows.append({
                "Sector": sector,
                "Ticker": t,
                "Price": round(close, 2),
                "Change": round((close / prev - 1) * 100, 2),
                "Size": 1,
            })
    return pd.DataFrame(rows)

if st.button("Refresh"):
    st.cache_data.clear()

with st.spinner("Loading heatmap..."):
    data = load()

if data.empty:
    st.warning("No data came back. Try Refresh.")
    st.stop()

fig = px.treemap(
    data,
    path=[px.Constant("Market"), "Sector", "Ticker"],
    values="Size",
    color="Change",
    color_continuous_scale=["#ef4444", "#1f2430", "#22c55e"],
    color_continuous_midpoint=0,
    range_color=[-3, 3],
    custom_data=["Change", "Price"],
)
fig.update_traces(
    texttemplate="%{label} %{customdata[0]:+.2f}%",
    textfont_size=16,
)
fig.update_layout(height=650, margin=dict(t=30, l=0, r=0, b=0))
st.plotly_chart(fig, use_container_width=True)