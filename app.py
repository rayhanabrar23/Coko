import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- CONFIG ---
st.set_page_config(page_title="Professor's Master Terminal", layout="wide")

def clean_df(df):
    if df.empty: return df
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [c.lower() for c in df.columns]
    return df

# --- DATABASE SEKTOR & INDUSTRI LENGKAP ---
market_data = {
    "FINANCE": {
        "Big Banks": ["BBCA.JK", "BBRI.JK", "BMRI.JK", "BBNI.JK"],
        "Mid-Small Banks": ["BDMN.JK", "PNBN.JK", "BJBR.JK", "BJTM.JK", "BRIS.JK"],
        "Digital Banks": ["ARTO.JK", "BBYB.JK", "BBNK.JK", "BANK.JK"],
        "Multi-Finance": ["ADMF.JK", "BBLD.JK", "CFIN.JK"]
    },
    "ENERGY": {
        "Coal": ["ADRO.JK", "ITMG.JK", "PTBA.JK", "HRUM.JK", "BUMI.JK", "BYAN.JK", "GEMS.JK"],
        "Oil & Gas": ["MEDC.JK", "AKRA.JK", "ENRG.JK", "PGAS.JK", "ELSA.JK"],
        "Renewable": ["PGEO.JK", "BREN.JK", "KEEN.JK"]
    },
    "BASIC INFO": {
        "Metal Mining": ["ANTM.JK", "TINS.JK", "MDKA.JK", "MBMA.JK", "INCO.JK", "NCKL.JK"],
        "Cement": ["SMGR.JK", "INTP.JK"],
        "Chemicals": ["TPIA.JK", "BRPT.JK", "ESSA.JK"]
    },
    "CONSUMER CYCLICAL": {
        "Retail": ["ACES.JK", "MAPI.JK", "MAPA.JK", "AMRT.JK", "MIDI.JK"],
        "Automotive": ["ASII.JK", "ASLC.JK", "DRMA.JK", "SMSM.JK"]
    },
    "INFRASTRUCTURE": {
        "Telecommunication": ["TLKM.JK", "ISAT.JK", "EXCL.JK", "FREN.JK"],
        "Towers": ["TOWR.JK", "TBIG.JK", "MTEL.JK"],
        "Construction": ["ADHI.JK", "PTPP.JK", "WIKA.JK"]
    },
    "PROPERTY": {
        "Real Estate": ["BSDE.JK", "PWON.JK", "CTRA.JK", "SMRA.JK"],
        "Industrial": ["SSIA.JK", "DMAS.JK", "KIJA.JK"]
    }
}

st.title("🏛️ Professor's Master Terminal")

# --- STEP 1: IHSG MONITOR ---
st.subheader("1. Market Condition (IHSG)")
ihsg = yf.download("^JKSE", period="1y", progress=False)
ihsg = clean_df(ihsg)
if not ihsg.empty:
    l_p = ihsg.iloc[-1]['close']
    p_p = ihsg.iloc[-2]['close']
    change = l_p - p_p
    pct = (change/p_p)*100
    st.metric("IHSG Composite", f"{l_p:.2f}", f"{change:.2f} ({pct:.2f}%)")
    
    fig_i = go.Figure(data=[go.Scatter(x=ihsg.index, y=ihsg['close'], fill='tozeroy', line_color='gold', name="IHSG")])
    fig_i.update_layout(height=250, template='plotly_dark', margin=dict(l=0,r=0,t=0,b=0))
    st.plotly_chart(fig_i, use_container_width=True)

st.divider()

# --- STEP 2: NAVIGATION ---
st.subheader("2. Top-Down Explorer")
c1, c2 = st.columns(2)
with c1:
    sec = st.selectbox("Pilih Sektor:", list(market_data.keys()))
with c2:
    ind = st.selectbox("Pilih Industri:", list(market_data[sec].keys()))

selected_list = market_data[sec][ind]

# --- STEP 3: MARKET RADAR & DETAIL CHART ---
if st.button(f"🔍 Scan Industri {ind}"):
    st.session_state['active_ind'] = ind
    
if st.session_state.get('active_ind') == ind:
    st.write(f"### 📊 Market Radar: {ind}")
    radar_data = []
    
    with st.spinner("Mengambil data industri..."):
        for t in selected_list:
            d = yf.download(t, period="1y", progress=False)
            d = clean_df(d)
            if not d.empty:
                d['ema20'] = ta.ema(d['close'], length=20)
                d['rsi'] = ta.rsi(d['close'], length=14)
                d['atr'] = ta.atr(d['high'], d['low'], d['close'], length=14)
                
                last = d.iloc[-1]
                radar_data.append({
                    "Ticker": t,
                    "Price": int(last['close']),
                    "RSI": round(last['rsi'], 1),
                    "Entry (EMA20)": int(last['ema20']),
                    "SL (2xATR)": int(last['ema20'] - (last['atr']*2)),
                    "Status": "🔥 Overbought" if last['rsi'] > 70 else "🧊 Oversold" if last['rsi'] < 30 else "Neutral"
                })
        
        st.table(pd.DataFrame(radar_data))

    st.divider()
    st.subheader("3. Deep Dive Visual Analysis")
    target = st.selectbox("Pilih Saham untuk Chart Detail:", selected_list)
    
    df = yf.download(target, period="2y", progress=False)
    df = clean_df(df)
    
    if not df.empty:
        # Technicals
        df['ema20'] = ta.ema(df['close'], length=20)
        df['ema50'] = ta.ema(df['close'], length=50)
        df['ema200'] = ta.ema(df['close'], length=200)
        df['rsi'] = ta.rsi(df['close'], length=14)
        bb = ta.bbands(df['close'], length=20, std=2)
        df = pd.concat([df, bb], axis=1)
        df.columns = [c.lower() for c in df.columns]
        
        bbu = [c for c in df.columns if 'bbu' in c][0]
        bbl = [c for c in df.columns if 'bbl' in c][0]
        
        # S/R Logic
        w = 20
        sup_l = df[df.low == df.low.rolling(w, center=True).min()]['low'].unique()
        res_l = df[df.high == df.high.rolling(w, center=True).max()]['high'].unique()

        # Plot
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_width=[0.15, 0.15, 0.7])
        fig.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='Price'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['ema20'], line=dict(color='orange'), name='EMA 20'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['ema200'], line=dict(color='white', width=2), name='EMA 200'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df[bbu], line=dict(color='rgba(173,216,230,0.2)', dash='dash'), name='BB Upper'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df[bbl], line=dict(color='rgba(173,216,230,0.2)', dash='dash'), name='BB Lower'), row=1, col=1)
        
        for s in sup_l[-3:]:
            fig.add_hline(y=s, line_color="green", line_dash="dash", opacity=0.3, row=1, col=1)
        for r in res_l[-3:]:
            fig.add_hline(y=r, line_color="red", line_dash="dash", opacity=0.3, row=1, col=1)

        fig.add_trace(go.Scatter(x=df.index, y=df['rsi'], line=dict(color='purple'), name='RSI'), row=2, col=1)
        fig.add_hline(y=70, line_color="red", line_dash="dot", row=2, col=1)
        fig.add_hline(y=30, line_color="green", line_dash="dot", row=2, col=1)
        
        v_c = ['red' if df['open'].iloc[i] > df['close'].iloc[i] else 'green' for i in range(len(df))]
        fig.add_trace(go.Bar(x=df.index, y=df['volume'], marker_color=v_c, name='Volume'), row=3, col=1)

        fig.update_layout(height=850, template='plotly_dark', xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

# --- STEP 5: PROFESSOR'S MORNING PICK ---
st.divider()
st.subheader("🎯 4. Professor's Morning Pick (Rekomendasi Besok)")
if st.button("🔥 Generate 10 Saham Potensial"):
    all_tickers = []
    for s_sect in market_data.values():
        for i_list in s_sect.values():
            all_tickers.extend(i_list)
    
    recs = []
    with st.spinner("Scanning seluruh database bursa..."):
        for t in list(set(all_tickers)):
            d = yf.download(t, period="1y", progress=False)
            d = clean_df(d)
            if not d.empty and len(d) > 20:
                d['ema20'] = ta.ema(d['close'], length=20)
                d['rsi'] = ta.rsi(d['close'], length=14)
                last = d.iloc[-1]
                
                # Filter: Dekat EMA20, RSI Sehat, Price > EMA20
                dist = (last['close'] - last['ema20']) / last['ema20']
                if 0 <= dist <= 0.03 and 40 <= last['rsi'] <= 65:
                    recs.append({
                        "Ticker": t, "Price": int(last['close']), 
                        "RSI": round(last['rsi'], 1), 
                        "Reason": "Uptrend & Area Pantul EMA20"
                    })
        
        if recs:
            top_10 = pd.DataFrame(recs).sort_values(by="RSI").head(10)
            st.table(top_10)
            st.success("Saran Profesor: Beli saat harga koreksi mendekati EMA 20 dan pantau volume saat pembukaan market jam 09.00.")
        else:
            st.warning("Market sedang ekstrem, belum ada saham yang masuk kriteria aman malam ini.")
