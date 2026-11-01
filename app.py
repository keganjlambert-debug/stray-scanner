import yfinance as yf
import warnings
warnings.filterwarnings("ignore")
import streamlit as st

st.set_page_config(page_title="Strat Scanner", layout="wide")

DEFAULT = "SPY, QQQ, IWM, TSLA, NVDA, AMD, MU, AAPL"
TIMEFRAMES = [("1h", "1H"), ("1d", "D"), ("1wk", "W")]
PERIODS = {"1h": "5d", "1d": "3mo", "1wk": "1y"}
GREEN, RED, GRAY, AMBER = "#22c55e", "#ef4444", "#6b7280", "#f59e0b"

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

@st.cache_data(ttl=300)
def get_bars(ticker, interval):
    return yf.download(ticker, interval=interval, period=PERIODS[interval], progress=False, multi_level_index=False)

def analyze(df):
    if df is None or len(df) < 4:
        return None
    bars = [df.iloc[i] for i in range(len(df))]
    labels = [label_bar(bars[i], bars[i - 1]) for i in range(1, len(bars))]
    last = bars[-1]
    setups = []
    if labels[-1] == "2d" and last["Close"] > last["Open"]:
        setups.append("Failed 2-down (bullish)")
    if labels[-1] == "2u" and last["Close"] < last["Open"]:
        setups.append("Failed 2-up (bearish)")
    if labels[-3] == "3" and labels[-2] == labels[-1] and labels[-1] in ("2u", "2d"):
        direction = "bullish" if labels[-1] == "2u" else "bearish"
        setups.append(f"3-2-2 continuation ({direction})")
    if labels[-1] == "1":
        setups.append(f"Inside bar: trigger {last['High']:.2f} / {last['Low']:.2f}")
    result = {}
    result["label"] = labels[-1]
    result["green"] = bool(last["Close"] >= last["Open"])
    result["close"] = float(last["Close"])
    result["prev_close"] = float(bars[-2]["Close"])
    result["setups"] = setups
    return result

def scan(ticker):
    tfs = {}
    for iv, name in TIMEFRAMES:
        tfs[name] = analyze(get_bars(ticker, iv))
    daily = tfs.get("D")
    if not daily:
        return None
    setups = []
    for name in ("1H", "D"):
        if tfs.get(name):
            for s in tfs[name]["setups"]:
                setups.append(f"{name}: {s}")
    text = " ".join(setups)
    bull = text.count("bullish")
    bear = text.count("bearish")
    if bull > bear:
        bias = "Bullish"
    elif bear > bull:
        bias = "Bearish"
    elif setups:
        bias = "Watch"
    else:
        bias = "None"
    greens = [tfs[n]["green"] for n in ("1H", "D", "W") if tfs.get(n)]
    if greens and all(greens):
        continuity = "Full green"
    elif greens and not any(greens):
        continuity = "Full red"
    else:
        continuity = "Mixed"
    r = {}
    r["ticker"] = ticker
    r["price"] = daily["close"]
    r["change"] = (daily["close"] / daily["prev_close"] - 1) * 100
    r["tfs"] = tfs
    r["setups"] = setups
    r["bias"] = bias
    r["continuity"] = continuity
    return r

def badge(name, res):
    base = "display:inline-block;min-width:46px;text-align:center;padding:3px 6px;margin-right:6px;border:1px solid;border-radius:6px;font-size:11px;line-height:1.3;"
    if not res:
        return f'<span style="{base}color:{GRAY};border-color:{GRAY}">{name}<br>-</span>'
    c = GREEN if res["green"] else RED
    arrow = "▲" if res["green"] else "▼"
    return f'<span style="{base}color:{c};border-color:{c};background:{c}22">{arrow} {name}<br><b>{res["label"]}</b></span>'

st.title("Strat Scanner")
st.caption("Strat setups across 1H, D and W. For education, not financial advice.")

c1, c2, c3 = st.columns([4, 1, 1])
tickers_text = c1.text_input("Tickers (comma separated)", DEFAULT)
c2.write("")
only_setups = c2.toggle("Only setups")
c3.write("")
if c3.button("Refresh"):
    st.cache_data.clear()

tickers = [t.strip().upper() for t in tickers_text.split(",") if t.strip()]
rows = []
with st.spinner("Scanning..."):
    for t in tickers:
        r = scan(t)
        if r:
            rows.append(r)

if not rows:
    st.warning("No data came back. Check the tickers and try Refresh.")
    st.stop()

rows.sort(key=lambda r: (not r["setups"], r["ticker"]))

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Tickers scanned", len(rows))
m2.metric("Active setups", sum(1 for r in rows if r["setups"]))
m3.metric("Bullish", sum(1 for r in rows if r["bias"] == "Bullish"))
m4.metric("Bearish", sum(1 for r in rows if r["bias"] == "Bearish"))
m5.metric("Full continuity", sum(1 for r in rows if r["continuity"] != "Mixed"))

if only_setups:
    shown = [r for r in rows if r["setups"]]
else:
    shown = rows

TH = 'style="text-align:left;color:#9ca3af;font-weight:500;padding:10px 12px;border-bottom:1px solid #2a2f3a"'
TD = 'style="padding:10px 12px;border-bottom:1px solid #1f2430;vertical-align:middle"'
headers = ["Ticker", "Price", "Change", "Strat (1H · D · W)", "Continuity", "Setup", "Bias"]
head = "".join(f"<th {TH}>{h}</th>" for h in headers)

body = ""
for r in shown:
    chg_c = GREEN if r["change"] > 0 else RED if r["change"] < 0 else GRAY
    cont_c = GREEN if r["continuity"] == "Full green" else RED if r["continuity"] == "Full red" else GRAY
    bias_c = {"Bullish": GREEN, "Bearish": RED, "Watch": AMBER}.get(r["bias"], GRAY)
    badges = "".join(badge(name, r["tfs"].get(name)) for _, name in TIMEFRAMES)
    setup = "<br>".join(r["setups"]) or "-"
    cells = []
    cells.append(f"<b>{r['ticker']}</b>")
    cells.append(f"${r['price']:.2f}")
    cells.append(f'<span style="color:{chg_c}">{r["change"]:+.2f}%</span>')
    cells.append(badges)
    cells.append(f'<span style="color:{cont_c}">{r["continuity"]}</span>')
    cells.append(setup)
    cells.append(f'<b style="color:{bias_c}">{r["bias"]}</b>')
    body += "<tr>" + "".join(f"<td {TD}>{c}</td>" for c in cells) + "</tr>"

table_html = f'<table style="width:100%;border-collapse:collapse;font-size:14px;color:#e5e7eb"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'
st.markdown(table_html, unsafe_allow_html=True)
st.markdown(table_html, unsafe_allow_html=True)