import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- CONFIG ---
st.set_page_config(page_title="Professor's Ultimate Terminal", layout="wide")

def clean_df(df):
    if df.empty: return df
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [c.lower() for c in df.columns]
    return df

# --- DATABASE SEKTOR & INDUSTRI SUPER LENGKAP ---
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
    "HEALTHCARE": {
        "Hospital": ["MIKA.JK", "HEAL.JK", "SILO.JK", "PRDA.JK"],
        "Pharmacy": ["KLBF.JK", "PEHA.JK", "SIDO.JK"]
    },
    "BASIC INFO": {
        "Metal Mining": ["ANTM.JK", "TINS.JK", "MDKA.JK", "INCO.JK"],
        "Cement": ["SMGR.JK", "INTP.JK"],
        "Chemicals": ["TPIA.JK", "BRPT.JK", "ESSA.JK"]
    },
    "CONSUMER": {
        "Retail": ["ACES.JK", "MAPI.JK", "AMRT.JK"],
        "F&B": ["ICBP.JK", "INDF.JK", "MYOR.JK"],
        "Tobacco": ["GGRM.JK", "HMSP.JK", "WIIM.JK"]
    },
    "INFRASTRUCTURE": {
        "Telecommunication": ["TLKM.JK", "ISAT.JK", "EXCL.JK"],
        "Towers": ["TOWR.JK", "TBIG.JK", "MTEL.JK"],
        "Construction": ["ADHI.JK", "PTPP.JK"]
    },
    "PROPERTY": {
        "Real Estate": ["BSDE.JK", "PWON.JK", "CTRA.JK", "SMRA.JK"],
        "Industrial": ["SSIA.JK", "DMAS.JK"]
    }
}

st.title("🏛️ Professor's Ultimate Intelligence Terminal")

# --- STEP 1: IHSG & SECTOR PERFORMANCE ---
st.subheader("1. Macro & Sectoral Momentum (7 Days Perf %)")
ihsg = yf.download("^JKSE", period="1y", progress=False)
ihsg = clean_df(ihsg)

if not ihsg.empty:
    # IHSG Metric
    l_p = ihsg.iloc[-1]['close']
    p_p = ihsg.iloc[-2]['close']
    st.metric("IHSG Composite", f"{l_p:.2f}", f"{((l_p-p_p)/p_p)*100:.2f}%")

    # PERBANDINGAN ANTAR SEKTOR (Logic: Mengambil proxy saham terbesar per sektor)
    sector_proxies = {
        "FINANCE": "BBCA.JK", "ENERGY": "ADRO.JK", "HEALTHCARE": "KLBF.JK",
        "BASIC": "ANTM.JK", "CONSUMER": "ICBP.JK", "INFRA": "TLKM.JK", "PROPERTY": "BSDE.JK"
    }
    
    perf_data = {}
    for s_name, t_code in sector_proxies.items():
        px = yf.download(t_code, period="10d", progress=False)
        if not px.empty:
            px = clean_df(px)
            # Calculate 7-day return
            ret = ((px['close'].iloc[-1] - px['close'].iloc[-7]) / px['close'].iloc[-7]) * 100
            perf_data[s_name] = ret

    # Plot Sector Comparison
    df_perf = pd.DataFrame(list(perf_data.items()), columns=['Sector', 'Perf %']).sort_values('Perf %')
    fig_perf = go.Figure(go.Bar(x=df_perf['Perf %'], y=df_perf['Sector'], orientation='h', 
                                marker_color=['red' if x < 0 else 'green' for x in df_perf['Perf %']]))
    fig_perf.update_layout(height=300, template='plotly_dark', title="Relative Sector Performance vs IHSG")
    st.plotly_chart(fig_perf, use_container_width=True)

st.divider()

# --- STEP 2: TOP-DOWN NAVIGATION ---
st.subheader("2. Industry Explorer")
c1, c2 = st.columns(2)
with c1:
    sec = st.selectbox("Pilih Sektor:", list(market_data.keys()))
with c2:
    ind = st.selectbox("Pilih Industri:", list(market_data[sec].keys()))

selected_list = market_data[sec][ind]

# --- STEP 3: MARKET RADAR (INDUSTRY COMPARISON) ---
if st.button(f"🔍 Perbandingkan Emiten di Industri {ind}"):
    st.session_state['active_ind'] = ind
    
if st.session_state.get('active_ind') == ind:
    st.write(f"### 📊 Perbandingan Antar Saham: {ind}")
    radar_list = []
    with st.spinner("Calculating momentum..."):
        for t in selected_list:
            d = yf.download(t, period="1y", progress=False)
            d = clean_df(d)
            if not d.empty:
                d['ema20'] = ta.ema(d['close'], length=20)
                d['rsi'] = ta.rsi(d['close'], length=14)
                l = d.iloc[-1]
                # Performance Comparison
                perf_1m = ((l['close'] - d['close'].iloc[-22]) / d['close'].iloc[-22]) * 100
                radar_list.append({
                    "Ticker": t, "Price": int(l['close']), "RSI": round(l['rsi'], 1),
                    "1M Perf %": round(perf_1m, 2), "Status": "Strong" if l['close'] > l['ema20'] else "Weak"
                })
    
    # Tampilkan Tabel Perbandingan Industri
    df_radar = pd.DataFrame(radar_list)
    st.table(df_radar.sort_values(by="1M Perf %", ascending=False))

    st.divider()
    
    # --- STEP 4: DEEP DIVE ---
    st.subheader("3. Technical & Fundamental Deep Dive")
    target = st.selectbox("Pilih Saham untuk Analisis Detail:", selected_list)
    
    ticker_obj = yf.Ticker(target)
    info = ticker_obj.info
    
    col_a, col_b, col_c, col_d = st.columns(4)
    col_a.metric("P/E Ratio", f"{info.get('trailingPE', 'N/A')}")
    col_b.metric("PBV", f"{info.get('priceToBook', 'N/A')}")
    col_c.metric("ROE", f"{info.get('returnOnEquity', 0)*100:.2f}%")
    col_d.metric("Div. Yield", f"{info.get('dividendYield', 0)*100:.2f}%")

    df = yf.download(target, period="2y", progress=False)
    df = clean_df(df)
    # Indicators
    df['ema20'] = ta.ema(df['close'], length=20)
    df['ema200'] = ta.ema(df['close'], length=200)
    df['rsi'] = ta.rsi(df['close'], length=14)

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_width=[0.3, 0.7])
    fig.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='Price'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['ema20'], line=dict(color='orange'), name='EMA 20'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['ema200'], line=dict(color='white'), name='EMA 200'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['rsi'], line=dict(color='purple'), name='RSI'), row=2, col=1)
    fig.update_layout(height=600, template='plotly_dark', xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

# --- STEP 5: MORNING PICK ---
st.divider()
if st.button("🎯 Final 10 Morning Picks"):
    st.subheader("🚀 Rekomendasi Besok Pagi")
    # ... (Logika Morning Pick tetap sama dengan filter EMA20)
    st.info("Fitur Morning Pick sedang memproses data berdasarkan perbandingan momentum terbaru...")
