import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# --- CONFIG ---
st.set_page_config(page_title="Professor's Tactical Terminal", layout="wide")

def clean_df(df):
    if df.empty: return df
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [c.lower() for c in df.columns]
    return df

# --- DATABASE SEKTOR ---
market_data = {
    "FINANCE": ["BBCA.JK", "BBRI.JK", "BMRI.JK", "BBNI.JK", "BRIS.JK", "ARTO.JK"],
    "ENERGY": ["ADRO.JK", "ITMG.JK", "PTBA.JK", "MEDC.JK", "AKRA.JK", "PGAS.JK"],
    "HEALTHCARE": ["MIKA.JK", "HEAL.JK", "SILO.JK", "KLBF.JK", "SIDO.JK"],
    "BASIC INFO": ["ANTM.JK", "TINS.JK", "MDKA.JK", "SMGR.JK", "INTP.JK", "TPIA.JK"],
    "CONSUMER": ["ACES.JK", "MAPI.JK", "AMRT.JK", "ICBP.JK", "INDF.JK", "GGRM.JK"],
    "INFRA": ["TLKM.JK", "ISAT.JK", "EXCL.JK", "TOWR.JK", "TBIG.JK", "ADHI.JK"],
    "PROPERTY": ["BSDE.JK", "PWON.JK", "CTRA.JK", "SMRA.JK", "SSIA.JK"]
}

st.title("🏛️ Professor's Tactical Terminal")

# --- STEP 1: MARKET PULSE ---
c1, c2 = st.columns([1, 1])
with c1:
    st.subheader("📈 IHSG Market Pulse")
    ihsg = yf.download("^JKSE", period="1y", progress=False)
    ihsg = clean_df(ihsg)
    if not ihsg.empty:
        fig_ihsg = go.Figure(data=[go.Scatter(x=ihsg.index, y=ihsg['close'], fill='tozeroy', line_color='gold')])
        fig_ihsg.update_layout(height=250, template='plotly_dark', margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig_ihsg, use_container_width=True)

with c2:
    st.subheader("🗺️ Sectoral Momentum")
    sector_list = []
    proxy = {"FINANCE":"BBCA.JK", "ENERGY":"ADRO.JK", "HEALTHCARE":"KLBF.JK", "BASIC":"ANTM.JK", "CONSUMER":"ICBP.JK", "INFRA":"TLKM.JK", "PROPERTY":"BSDE.JK"}
    for s, t in proxy.items():
        try:
            px_data = yf.download(t, period="10d", progress=False)
            if not px_data.empty:
                px_data = clean_df(px_data)
                perf = ((px_data['close'].iloc[-1] - px_data['close'].iloc[-5]) / px_data['close'].iloc[-5]) * 100
                sector_list.append({"Sector": s, "Performance": round(perf, 2), "Parent": "Market", "Size": 10})
        except: continue
    if sector_list:
        fig_tree = px.treemap(pd.DataFrame(sector_list), path=['Parent', 'Sector'], values='Size', color='Performance', color_continuous_scale='RdYlGn', range_color=[-3, 3])
        fig_tree.update_layout(height=250, margin=dict(l=0,r=0,t=0,b=0), template='plotly_dark')
        st.plotly_chart(fig_tree, use_container_width=True)

st.divider()

# --- STEP 2: SEARCH ---
search_col, nav_col = st.columns([1, 2])
with search_col:
    manual_ticker = st.text_input("🔍 Cari Kode (Contoh: BBRI.JK):", "").upper()
with nav_col:
    sec_choice = st.selectbox("📂 Pilih Sektor:", ["None"] + list(market_data.keys()))

target = None
if manual_ticker:
    target = manual_ticker if manual_ticker.endswith(".JK") else f"{manual_ticker}.JK"
elif sec_choice != "None":
    target = st.selectbox("Pilih Saham:", market_data[sec_choice])

# --- STEP 3: TACTICAL ANALYSIS ---
if target:
    try:
        t_obj = yf.Ticker(target)
        df = yf.download(target, period="1y", progress=False)
        df = clean_df(df)
        
        if not df.empty:
            # Kalkulasi Indikator
            df['ema20'] = ta.ema(df['close'], length=20)
            df['rsi'] = ta.rsi(df['close'], length=14)
            df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
            
            l = df.iloc[-1]
            atr_val = l['atr']
            
            # LOGIKA SUPPORT / RESISTANCE (Sederhana)
            res = df['high'].rolling(20).max().iloc[-1]
            sup = df['low'].rolling(20).min().iloc[-1]
            
            # LOGIKA SIGNAL & SL/TP
            signal = "HOLD / WAIT"
            color = "white"
            if l['close'] > l['ema20'] and l['rsi'] < 65:
                signal = "BUY / ACCUMULATE"
                color = "#00FF00"
            elif l['close'] < l['ema20'] or l['rsi'] > 75:
                signal = "SELL / TAKE PROFIT"
                color = "#FF0000"

            sl = l['close'] - (2 * atr_val)
            tp = l['close'] + (3 * atr_val)

            # TAMPILAN DASHBOARD TAKTIS
            st.markdown(f"### 🛡️ Tactical Command: {target}")
            
            m1, m2, m3 = st.columns(3)
            m1.markdown(f"<div style='text-align:center; padding:10px; border:2px solid {color}; border-radius:10px;'><b>SIGNAL</b><br><span style='font-size:20px; color:{color};'>{signal}</span></div>", unsafe_allow_html=True)
            m2.metric("Resistance (Target)", f"{int(res)}")
            m3.metric("Support (Batas Aman)", f"{int(sup)}")
            
            st.write("")
            c_sl, c_tp, c_roe = st.columns(3)
            c_sl.error(f"❌ STOP LOSS (SL): {int(sl)}")
            c_tp.success(f"✅ TAKE PROFIT (TP): {int(tp)}")
            c_roe.info(f"📊 ROE: {t_obj.info.get('returnOnEquity', 0)*100:.2f}%")

            # Interactive Chart
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_width=[0.3, 0.7], vertical_spacing=0.05)
            fig.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='Price'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['ema20'], line=dict(color='orange', width=2), name='EMA 20'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['rsi'], line=dict(color='purple'), name='RSI'), row=2, col=1)
            # Add SL/TP Lines on Chart
            fig.add_hline(y=sl, line_dash="dash", line_color="red", annotation_text="SL Zone", row=1, col=1)
            fig.add_hline(y=tp, line_dash="dash", line_color="green", annotation_text="TP Zone", row=1, col=1)
            
            fig.update_layout(height=600, template='plotly_dark', xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Data error: {e}")

# --- STEP 4: GENERATE REFS ---
st.divider()
if st.button("🎯 Generate Top 10 Picks"):
    st.subheader("🚀 Morning Buy List")
    picks = []
    all_tickers = [item for sublist in market_data.values() for item in sublist]
    with st.spinner("Scanning..."):
        for t in list(set(all_tickers)):
            d = yf.download(t, period="50d", progress=False)
            d = clean_df(d)
            if not d.empty and len(d) > 20:
                d['ema20'] = ta.ema(d['close'], length=20)
                d['rsi'] = ta.rsi(d['close'], length=14)
                l = d.iloc[-1]
                if 0 <= (l['close'] - l['ema20'])/l['ema20'] <= 0.02 and 40 <= l['rsi'] <= 60:
                    picks.append({"Ticker": t, "Price": int(l['close']), "RSI": round(l['rsi'], 1), "Signal": "EMA20 Rebound"})
    if picks:
        st.table(pd.DataFrame(picks).head(10))

    # --- TOP-DOWN REVIEW ---
    st.write("---")
    st.subheader("🧐 Professor's Market Review")
    ihsg_change = ((ihsg['close'].iloc[-1] - ihsg['close'].iloc[-2]) / ihsg['close'].iloc[-2]) * 100
    st.info(f"""
    **Analisis Top-Down:**
    1. **IHSG:** Sedang bergerak di {ihsg['close'].iloc[-1]:.0f} ({ihsg_change:.2f}%).
    2. **Tactical:** Gunakan level **Support/Resistance** di atas sebagai panduan entri. Jangan pernah 'All-In' tanpa memperhatikan level **SL (Stop Loss)**.
    3. **Note:** Jika ROE emiten di bawah 5%, pertimbangkan untuk *Scalping* saja daripada *Hold* jangka panjang.
    """)
