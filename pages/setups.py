import yfinance as yf
import warnings
warnings.filterwarnings("ignore")
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Strat Setups", layout="wide")

DEFAULT = "NVDA, AMZN, AAPL, TSLA, NKE, AMD, NFLX, SNDK, MU, LLY, AMAT, GOOG, AVGO, ACHR, FOUR, BURL, MSFT, CHPT, PLTR, COIN, META, SPY, QQQ, IWM"
GREEN, RED, AMBER, PURPLE, GRAY = "#22c55e", "#ef4444", "#f59e0b", "#a78bfa", "#6b7280"
NAMES = {"1": "Inside (1)", "2u": "2 Up", "2d": "2 Down", "3": "Outside (3)"}
COLORS = {"1": AMBER, "2u": GREEN, "2d": RED, "3": PURPLE}
PERIOD_WORD = {"Weekly": "This week", "Monthly": "This month", "Quarterly": "This quarter", "Yearly": "This year"}
AVATAR = ["#2563eb", "#db2777", "#16a34a", "#ea580c", "#7c3aed", "#0891b2", "#dc2626", "#4b5563"]


def label_bar(cur, prev):
    broke_high = cur["High"] > prev["High"]
    broke_low = cur["Low"] < prev["Low"]
    if broke_high and broke_low:
        return "3"
    if broke_high:
        return "2u"
    if broke_low:
        return "2d"
    return "1"


@st.cache_data(ttl=600)
def get_all(tickers, interval, period):
    data = yf.download(list(tickers), interval=interval, period=period, group_by="ticker", progress=False, threads=True)
    out = {}
    for t in tickers:
        try:
            if isinstance(data.columns, pd.MultiIndex):
                df = data[t]
            else:
                df = data
            df = df.dropna(subset=["High", "Low"])
            if len(df) >= 2:
                out[t] = df
        except Exception:
            pass
    return out


def resample(df, rule):
    agg = {"Open": "first", "High": "max", "Low": "min", "Close": "last"}
    return df.resample(rule).agg(agg).dropna()


def get_frames(tickers, tf):
    if tf == "Weekly":
        return get_all(tickers, "1wk", "1y")
    monthly = get_all(tickers, "1mo", "10y")
    if tf == "Monthly":
        return monthly
    rule = "QE" if tf == "Quarterly" else "YE"
    out = {}
    for t, df in monthly.items():
        r = resample(df, rule)
        if len(r) >= 2:
            out[t] = r
    return out


def analyze(ticker, df):
    cur = df.iloc[-1]
    prev = df.iloc[-2]
    lab = label_bar(cur, prev)
    green = bool(cur["Close"] >= cur["Open"])
    failed = ""
    if lab == "2d" and green:
        failed = "Failed 2D"
    if lab == "2u" and not green:
        failed = "Failed 2U"
    return {
        "ticker": ticker,
        "label": lab,
        "failed": failed,
        "price": float(cur["Close"]),
        "cur_low": float(cur["Low"]),
        "cur_high": float(cur["High"]),
        "prev_low": float(prev["Low"]),
        "prev_high": float(prev["High"]),
    }


def badge(text, c):
    return f'<span style="padding:3px 9px;border-radius:6px;font-size:11px;color:{c};background:{c}26;margin-left:4px;white-space:nowrap">{text}</span>'


def card(r, word):
    c = COLORS[r["label"]]
    av = AVATAR[sum(ord(ch) for ch in r["ticker"]) % len(AVATAR)]
    badges = badge(NAMES[r["label"]], c)
    if r["failed"]:
        fc = GREEN if r["failed"] == "Failed 2D" else RED
        badges = badge(r["failed"], fc) + badges
    html = '<div style="background:#16181d;border:1px solid #262a33;border-radius:12px;padding:16px">'
    html += '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px">'
    html += '<div style="display:flex;align-items:center;gap:10px">'
    html += f'<div style="width:36px;height:36px;border-radius:50%;background:{av};color:white;display:flex;align-items:center;justify-content:center;font-weight:600">{r["ticker"][0]}</div>'
    html += f'<div><div style="font-weight:600;color:#f3f4f6">{r["ticker"]}</div><div style="font-size:12px;color:#9ca3af">${r["price"]:.2f}</div></div>'
    html += f'</div><div>{badges}</div></div>'
    html += f'<div style="font-size:13px;color:#9ca3af;line-height:1.8">{word}: <span style="color:#d1d5db">{r["cur_low"]:.2f} - {r["cur_high"]:.2f}</span><br>'
    html += f'Prior: <span style="color:#d1d5db">{r["prev_low"]:.2f} - {r["prev_high"]:.2f}</span></div>'
    html += '</div>'
    return html


st.title("Strat Setups")

c1, c2, c3, c4 = st.columns([2, 3, 2, 1])
search = c1.text_input("Search ticker", placeholder="Search ticker").strip().upper()
tf = c2.segmented_control("Timeframe", ["Weekly", "Monthly", "Quarterly", "Yearly"], default="Weekly")
if not tf:
    tf = "Weekly"
pattern = c3.selectbox("Pattern type", ["All", "Inside (1)", "2 Up", "2 Down", "Outside (3)", "Failed 2s"])
c4.write("")
if c4.button("Refresh"):
    st.cache_data.clear()

with st.expander("Edit tickers"):
    tickers_text = st.text_area("Tickers (comma separated)", DEFAULT)

tickers = tuple(t.strip().upper() for t in tickers_text.split(",") if t.strip())

with st.spinner("Scanning..."):
    frames = get_frames(tickers, tf)
    rows = [analyze(t, frames[t]) for t in tickers if t in frames]

if not rows:
    st.warning("No data came back. Check the tickers and try Refresh.")
    st.stop()

counts = {k: sum(1 for r in rows if r["label"] == k) for k in NAMES}
strip = " &nbsp;·&nbsp; ".join(f'<span style="color:#9ca3af">{NAMES[k]}:</span> <b style="color:{COLORS[k]}">{counts[k]}</b>' for k in NAMES)
st.markdown(f'<div style="font-size:14px;margin:4px 0 16px">{strip}</div>', unsafe_allow_html=True)

shown = rows
if search:
    shown = [r for r in shown if search in r["ticker"]]
if pattern == "Failed 2s":
    shown = [r for r in shown if r["failed"]]
elif pattern != "All":
    shown = [r for r in shown if NAMES[r["label"]] == pattern]

if not shown:
    st.info("No tickers match right now.")
    st.stop()

word = PERIOD_WORD[tf]
cards = "".join(card(r, word) for r in shown)
st.markdown(f'<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px">{cards}</div>', unsafe_allow_html=True)