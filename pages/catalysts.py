import yfinance as yf
import warnings
warnings.filterwarnings("ignore")
import streamlit as st
from datetime import date

st.set_page_config(page_title="Catalysts", layout="wide")
st.title("Catalysts")
st.caption("Upcoming earnings, dividends and news. For education, not financial advice.")

DEFAULT = "TSLA, NVDA, AMD, MU, AAPL, MSFT, AMZN, META, GOOGL, NFLX, AVGO, LLY, NKE, JPM, COIN, PLTR"
GREEN, RED, GRAY, AMBER, PURPLE = "#22c55e", "#ef4444", "#6b7280", "#f59e0b", "#a78bfa"


def first_date(v):
    if isinstance(v, (list, tuple)):
        v = v[0] if v else None
    if v is None:
        return None
    if hasattr(v, "hour"):
        v = v.date()
    return v


@st.cache_data(ttl=1800)
def get_calendar(t):
    try:
        cal = yf.Ticker(t).calendar
    except Exception:
        return {}
    if not isinstance(cal, dict):
        return {}
    return {
        "earnings": first_date(cal.get("Earnings Date")),
        "ex_div": first_date(cal.get("Ex-Dividend Date")),
    }


@st.cache_data(ttl=900)
def get_news(t):
    try:
        items = yf.Ticker(t).news or []
    except Exception:
        return []
    news = []
    for it in items[:8]:
        c = it.get("content", it)
        title = c.get("title")
        url = (c.get("canonicalUrl") or {}).get("url") or c.get("link")
        source = (c.get("provider") or {}).get("displayName") or c.get("publisher", "")
        when = str(c.get("pubDate") or "")[:10]
        if title:
            news.append({"title": title, "url": url, "source": source, "when": when})
    return news


def days_until(d):
    if d is None:
        return None
    return (d - date.today()).days


def tag(days):
    if days is None:
        return f'<span style="color:{GRAY}">-</span>'
    if days < 0:
        return f'<span style="color:{GRAY}">Passed</span>'
    c = AMBER if days <= 7 else PURPLE
    return f'<span style="display:inline-block;padding:2px 10px;border-radius:999px;color:{c};background:{c}22;font-size:12px">In {days}d</span>'


c1, c2, c3 = st.columns([4, 1, 1])
tickers_text = c1.text_input("Tickers (comma separated)", DEFAULT)
window = c2.selectbox("Window (days)", [7, 14, 30, 60, 90], index=2)
c3.write("")
if c3.button("Refresh"):
    st.cache_data.clear()

tickers = [t.strip().upper() for t in tickers_text.split(",") if t.strip()]
rows = []
with st.spinner("Loading catalysts..."):
    for t in tickers:
        cal = get_calendar(t)
        earnings = cal.get("earnings")
        ex_div = cal.get("ex_div")
        rows.append({
            "ticker": t,
            "earnings": earnings,
            "ex_div": ex_div,
            "e_days": days_until(earnings),
            "d_days": days_until(ex_div),
        })


def in_window(d):
    return d is not None and 0 <= d <= window


m1, m2, m3 = st.columns(3)
m1.metric("Earnings this week", sum(1 for r in rows if r["e_days"] is not None and 0 <= r["e_days"] <= 7))
m2.metric(f"Earnings in {window} days", sum(1 for r in rows if in_window(r["e_days"])))
m3.metric(f"Ex-dividend in {window} days", sum(1 for r in rows if in_window(r["d_days"])))

rows.sort(key=lambda r: r["e_days"] if r["e_days"] is not None and r["e_days"] >= 0 else 9999)

st.subheader("Calendar")
TH = 'style="text-align:left;color:#9ca3af;font-weight:500;padding:10px 12px;border-bottom:1px solid #2a2f3a"'
TD = 'style="padding:10px 12px;border-bottom:1px solid #1f2430;vertical-align:middle"'
headers = ["Ticker", "Earnings date", "Earnings", "Ex-dividend date", "Ex-dividend"]
head = "".join(f"<th {TH}>{h}</th>" for h in headers)

body = ""
for r in rows:
    cells = [
        f"<b>{r['ticker']}</b>",
        r["earnings"].strftime("%b %d, %Y") if r["earnings"] else "-",
        tag(r["e_days"]),
        r["ex_div"].strftime("%b %d, %Y") if r["ex_div"] else "-",
        tag(r["d_days"]),
    ]
    body += "<tr>" + "".join(f"<td {TD}>{c}</td>" for c in cells) + "</tr>"

table_html = f'<table style="width:100%;border-collapse:collapse;font-size:14px;color:#e5e7eb"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'
st.markdown(table_html, unsafe_allow_html=True)

st.subheader("News")
pick = st.selectbox("Ticker", tickers)
news = get_news(pick)
if not news:
    st.info("No recent headlines found.")
for n in news:
    with st.container(border=True):
        if n["url"]:
            st.markdown(f"**[{n['title']}]({n['url']})**")
        else:
            st.markdown(f"**{n['title']}**")
        st.caption(f"{n['source']} · {n['when']}")