"""SatelliteAlpha web app.
Reads the monthly ship counts made by the Colab notebook (monthly_ship_counts.csv),
downloads stock prices live, and tests whether ship activity is linked to the next period's excess return."""
import os
import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from scipy.stats import spearmanr

st.set_page_config(page_title="SatelliteAlpha", layout="wide")
st.title("SatelliteAlpha: ship activity near a port vs the port company's share price")
st.caption("Ship counts come from open Sentinel-2 vessel detections (Global Fishing Watch, CC0). "
           "Research exercise, not investment advice.")

RULES = {"M": dict(min_hist=6, min_overlap=12), "Q": dict(min_hist=4, min_overlap=8)}
DATA_PATH = "monthly_ship_counts.csv"


# ---------- data ----------
@st.cache_data
def read_series(file_or_path):
    df = pd.read_csv(file_or_path)
    freq = str(df["freq"].iloc[0])
    df["period"] = pd.PeriodIndex(df["period"], freq=freq)
    return df.set_index("period"), freq


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def period_returns(ticker, freq, start, end):
    import yfinance as yf
    px = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False)
    px = px["Close"] if len(px) else px
    if isinstance(px, pd.DataFrame):
        px = px.iloc[:, 0] if px.shape[1] else pd.Series(dtype=float)
    if len(px) == 0:
        px = yf.Ticker(ticker).history(start=start, end=end, auto_adjust=True)["Close"]
        px.index = px.index.tz_localize(None)
    if len(px) == 0:
        raise ValueError(f"No price data came back for {ticker}.")
    last = px.groupby(px.index.to_period(freq)).last()
    return last.pct_change()


def test_link(ship_change, ticker, bench_ret, freq, start, end, n_shuffles):
    excess = period_returns(ticker, freq, start, end) - bench_ret
    data = pd.DataFrame({"ship_change": ship_change, "next_return": excess.shift(-1)}).dropna()
    need = RULES[freq]["min_overlap"]
    if len(data) < need:
        return dict(n=len(data), rho=np.nan, p=np.nan, data=data, note=f"only {len(data)} overlapping periods, need {need}")
    rho = spearmanr(data["ship_change"], data["next_return"])[0]
    rng = np.random.default_rng(0)
    shuffled = [spearmanr(rng.permutation(data["ship_change"].values), data["next_return"])[0] for _ in range(n_shuffles)]
    p = (1 + np.sum(np.abs(shuffled) >= abs(rho))) / (1 + n_shuffles)
    return dict(n=len(data), rho=rho, p=p, data=data, note="")


# ---------- sidebar ----------
st.sidebar.header("Settings")
ticker = st.sidebar.text_input("Stock linked to the port", "ADANIPORTS.NS")
placebos = st.sidebar.text_input("Unrelated stocks (luck check, comma separated)", "TCS.NS, HINDUNILVR.NS")
bench = st.sidebar.text_input("Benchmark index", "^NSEI")
n_shuffles = st.sidebar.slider("Shuffles for the p-value", 500, 5000, 2000, step=500)
start = st.sidebar.text_input("Price start date", "2019-01-01")
end = st.sidebar.text_input("Price end date", "2026-12-31")

# ---------- load ship data ----------
uploaded = st.file_uploader("Upload monthly_ship_counts.csv (made by the Colab notebook)", type="csv")
if uploaded is not None:
    series_df, freq = read_series(uploaded)
elif os.path.exists(DATA_PATH):
    series_df, freq = read_series(DATA_PATH)
else:
    st.info("Run the Colab notebook first, then upload the file `monthly_ship_counts.csv` here.")
    st.stop()

setting = str(series_df["setting"].iloc[0]) if "setting" in series_df.columns else "unknown"
st.write(f"**Ship-data setting used:** {setting}")
if "port box, monthly, at least 2" not in setting:
    st.warning("This data came from a fallback setting (wider area, fewer passes or quarterly). Say so if you report the result.")

ships = series_df["ships_per_pass"]
st.subheader("1. Ships detected per satellite pass")
chart = ships.copy()
chart.index = chart.index.to_timestamp()
st.line_chart(chart)

# ---------- test ----------
st.subheader("2. Is ship activity linked to the next period's excess return?")
prev_mean = ships.shift(1).expanding(min_periods=RULES[freq]["min_hist"]).mean()
ship_change = (ships / prev_mean - 1).replace([np.inf, -np.inf], np.nan)

tickers = [ticker.strip()] + [t.strip() for t in placebos.split(",") if t.strip()]
try:
    with st.spinner("Downloading prices and running the shuffle test..."):
        bench_ret = period_returns(bench.strip(), freq, start, end)
        res = {t: test_link(ship_change, t, bench_ret, freq, start, end, n_shuffles) for t in tickers}
except Exception as e:
    st.error(f"Could not get prices: {e}. Check the ticker names and try again in a minute.")
    st.stop()

table = pd.DataFrame([{"stock": t, "periods used": r["n"],
                       "correlation": None if np.isnan(r["rho"]) else round(r["rho"], 3),
                       "p-value": None if np.isnan(r["p"]) else round(r["p"], 3),
                       "note": r["note"]} for t, r in res.items()])
st.dataframe(table, hide_index=True)

main = res[tickers[0]]
if np.isnan(main["p"]):
    st.warning(f"No result for {tickers[0]}: {main['note']}.")
else:
    st.write(f"Smallest correlation this test could reliably detect with {main['n']} periods: about {1.96 / np.sqrt(main['n']):.2f}.")
    if main["p"] >= 0.05:
        st.success("p-value is 0.05 or higher: **no evidence of a link** between ship activity and the next period's return. This is a normal result.")
    else:
        others = [t for t in tickers[1:] if not np.isnan(res[t]["p"]) and res[t]["p"] < 0.05]
        msg = "p-value is below 0.05: a possible link, but this is weak evidence (one port, few periods, several stocks tested)."
        if others:
            msg += f" The unrelated stock(s) {', '.join(others)} also look linked, so this may be luck."
        st.warning(msg)

    fig, ax = plt.subplots(figsize=(5, 4))
    ax.scatter(main["data"]["ship_change"], main["data"]["next_return"])
    ax.axhline(0, color="grey", lw=0.5); ax.axvline(0, color="grey", lw=0.5)
    ax.set_xlabel("ships per pass vs earlier average (period t)")
    ax.set_ylabel(f"{tickers[0]} excess return (period t+1)")
    st.pyplot(fig)

with st.expander("How this works and what to be careful about"):
    st.markdown("""
- **Feature:** ships per pass compared with the average of all earlier periods (only past information).
- **Target:** the stock's return minus the benchmark's return in the **next** period.
- **Shuffle test:** the ship numbers are shuffled many times; the p-value is how often a random order gives a correlation as big as the real one.
- **Luck check:** the same test on unrelated stocks. If they also look linked, the result is probably luck.
- **Limits:** detections are another organisation's model output and are not validated here; the port company has other businesses; there are few periods; correlation is not causation.
""")
