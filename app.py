import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- CONFIG ---
st.set_page_config(page_title="Professor's Intel Terminal", layout="wide")

def clean_df(df):
    if df.empty: return df
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [c.lower() for c in df.columns]
    return df

# --- DATABASE SEKTOR & INDUSTRI ---
market_data = {
    "FINANCE": {
        "Big Banks": ["BBCA.JK", "BBRI.JK", "BMRI.JK", "BBNI.JK"],
        "Mid-Small Banks": ["BDMN.JK", "PNBN.JK", "BRIS.JK"],
        "Digital Banks": ["ARTO.JK", "BBYB.JK", "BBNK.JK"]
    },
    "ENERGY": {
        "Coal": ["ADRO.JK", "ITMG.JK", "PTBA.JK", "HRUM.JK", "BUMI.JK"],
        "Oil & Gas": ["MEDC.JK", "AKRA.JK", "PGAS.JK", "ELSA.JK"],
        "Renewable": ["PGEO.JK", "BREN.JK"]
    },
    "BASIC INFO": {
        "Metal Mining": ["ANTM.JK", "TINS.JK", "MDKA.JK", "INCO.JK"],
        "Chemicals": ["TPIA.JK", "BRPT.JK", "ESSA.JK"]
    },
    "INFRASTRUCTURE": {
        "Telecommunication": ["TLKM.JK", "ISAT.JK", "EXCL.JK"],
        "Towers": ["TOWR.JK", "TBIG.JK", "MTEL.JK"],
        "Construction": ["ADHI.JK", "PTPP.JK", "WIKA.JK"]
    }
}

st.title("🏛️ Professor's Intelligence Terminal")

# --- STEP 1: IHSG MONITOR ---
st.subheader("1. Market Snapshot")
ihsg = yf.download("^JKSE", period="1y", progress=False)
ihsg = clean_df(ihsg)
if not ihsg.empty:
    l_p = ihsg.iloc[-1]['close']
    p_p = ihsg.iloc[-2]['close']
    st.metric("IHSG Composite", f"{l_p:.2f}", f"{(l_p-p_p):.2f} ({((l_p-p_p)/p_p)*100:.2f}%)")
    fig_i = go.Figure(data=[go.Scatter(x=ihsg.index, y=ihsg['close'], fill='tozeroy', line_color='gold')])
    fig_i.update_layout(height=200, template='plotly_dark', margin=dict(l=0,r=0,t=0,b=0))
    st.plotly_chart(fig_i, use_container_width=True)

st.divider()

# --- STEP 2: NAVIGATION ---
c1, c2 = st.columns(2)
with c1:
    sec = st.selectbox("Pilih Sektor:", list(market_data.keys()))
with c2:
    ind = st.selectbox("Pilih Industri:", list(market_data[sec].keys()))

selected_list = market_data[sec][ind]

# --- STEP 3: MARKET RADAR ---
if st.button(f"🔍 Scan Industri {ind}"):
    st.session_state['active_ind'] = ind
    
if st.session_state.get('active_ind') == ind:
    st.write(f"### 📊 Radar Sektor: {ind}")
    radar_data = []
    for t in selected_list:
        d = yf.download(t, period="1y", progress=False)
        d = clean_df(d)
        if not d.empty:
            d['ema20'] = ta.ema(d['close'], length=20)
            d['rsi'] = ta.rsi(d['close'], length=14)
            d['atr'] = ta.atr(d['high'], d['low'], d['close'], length=14)
            l = d.iloc[-1]
            radar_data.append({
                "Ticker": t, "Price": int(l['close']), "RSI": round(l['rsi'], 1),
                "Entry": int(l['ema20']), "SL": int(l['ema20'] - (l['atr']*2)),
                "Status": "🔥 OB" if l['rsi'] > 70 else "🧊 OS" if l['rsi'] < 30 else "OK"
            })
    st.table(pd.DataFrame(radar_data))

    st.divider()
    
    # --- STEP 4: DEEP DIVE (TECHNICAL + FUNDAMENTAL + NEWS) ---
    st.subheader("3. Deep Dive Intelligence")
    target = st.selectbox("Pilih Saham untuk Analisis Total:", selected_list)
    
    # Fundamental Metrics
    ticker_obj = yf.Ticker(target)
    info = ticker_obj.info
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("P/E Ratio", f"{info.get('trailingPE', 'N/A')}")
    m2.metric("PBV Ratio", f"{info.get('priceToBook', 'N/A')}")
    m3.metric("Div. Yield", f"{info.get('dividendYield', 0)*100:.2f}%")
    m4.metric("Market Cap", f"{info.get('marketCap', 0)//10**12}T IDR")

    # Chart Section
    df = yf.download(target, period="2y", progress=False)
    df = clean_df(df)
    df['ema20'] = ta.ema(df['close'], length=20)
    df['ema200'] = ta.ema(df['close'], length=200)
    df['rsi'] = ta.rsi(df['close'], length=14)
    bb = ta.bbands(df['close'], length=20, std=2)
    df = pd.concat([df, bb], axis=1)
    df.columns = [c.lower() for c in df.columns]
    bbu = [c for c in df.columns if 'bbu' in c][0]
    bbl = [c for c in df.columns if 'bbl' in c][0]

    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_width=[0.15, 0.15, 0.7])
    fig.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='Price'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['ema20'], line=dict(color='orange'), name='EMA 20'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['ema200'], line=dict(color='white', width=2), name='EMA 200'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df[bbu], line=dict(color='gray', dash='dash'), name='BB Upper'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df[bbl], line=dict(color='gray', dash='dash'), name='BB Lower'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['rsi'], line=dict(color='purple'), name='RSI'), row=2, col=1)
    fig.add_trace(go.Bar(x=df.index, y=df['volume'], name='Volume'), row=3, col=1)
    fig.update_layout(height=700, template='plotly_dark', xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

    # News Feed
    st.write("### 📰 Latest News")
    news = ticker_obj.news
    if news:
        for item in news[:3]:
            st.write(f"**[{item['publisher']}]** {item['title']}")
            st.write(f"Link: {item['link']}")
    else:
        st.write("Tidak ada berita terbaru untuk emiten ini.")

# --- STEP 5: MORNING PICK ---
st.divider()
if st.button("🎯 Generate 10 Morning Picks"):
    st.subheader("🚀 Rekomendasi Besok Pagi")
    all_t = []
    for s in market_data.values():
        for i in s.values():
            all_t.extend(i)
    
    recs = []
    for t in list(set(all_t)):
        d = yf.download(t, period="1y", progress=False)
        d = clean_df(d)
        if not d.empty and len(d) > 20:
            d['ema20'] = ta.ema(d['close'], length=20)
            d['rsi'] = ta.rsi(d['close'], length=14)
            last = d.iloc[-1]
            dist = (last['close'] - last['ema20']) / last['ema20']
            if 0 <= dist <= 0.03 and 40 <= last['rsi'] <= 65:
                recs.append({"Ticker": t, "Price": int(last['close']), "RSI": round(last['rsi'], 1), "Note": "Area Pantul EMA20"})
    
    if recs:
        st.table(pd.DataFrame(recs).sort_values(by="RSI").head(10))
    else:
        st.warning("Belum ada yang masuk kriteria.")
