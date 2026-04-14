import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta

# --- CONFIG ---
st.set_page_config(page_title="Terminal Screening Stock v2", layout="wide", initial_sidebar_state="collapsed")

# Custom CSS
st.markdown("""
<style>
    .main { background-color: #0a0a0f; }
    .stApp { background-color: #0a0a0f; color: #e0e0e0; }
    .metric-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 1px solid #0f3460;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
    }
    .score-high { color: #00ff88; font-size: 28px; font-weight: bold; }
    .score-mid  { color: #ffcc00; font-size: 28px; font-weight: bold; }
    .score-low  { color: #ff4466; font-size: 28px; font-weight: bold; }
    .tag-buy    { background:#00401a; color:#00ff88; padding:4px 12px; border-radius:20px; font-weight:bold; }
    .tag-sell   { background:#400010; color:#ff4466; padding:4px 12px; border-radius:20px; font-weight:bold; }
    .tag-hold   { background:#404000; color:#ffcc00; padding:4px 12px; border-radius:20px; font-weight:bold; }
    .divider { border-top: 1px solid #1e3a5f; margin: 20px 0; }
    h1, h2, h3 { color: #e0e0ff; }
    .stDataFrame { background: #0d0d1a; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# UTILITY FUNCTIONS
# ─────────────────────────────────────────────

def clean_df(df):
    if df.empty:
        return df
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [c.lower() for c in df.columns]
    return df

def safe_float(val, default=0.0):
    try:
        v = float(val)
        return default if np.isnan(v) or np.isinf(v) else v
    except:
        return default

# ─────────────────────────────────────────────
# CANDLESTICK PATTERN DETECTION
# ─────────────────────────────────────────────

def detect_patterns(df):
    """Detect key daily-trade candlestick patterns."""
    patterns = []
    if len(df) < 3:
        return patterns

    o, h, l, c = df['open'].values, df['high'].values, df['low'].values, df['close'].values
    idx = -1  # last candle

    body = abs(c[idx] - o[idx])
    candle_range = h[idx] - l[idx]
    upper_wick = h[idx] - max(c[idx], o[idx])
    lower_wick = min(c[idx], o[idx]) - l[idx]

    # Hammer / Inverted Hammer
    if candle_range > 0:
        if lower_wick >= 2 * body and upper_wick <= 0.3 * body:
            patterns.append("🔨 Hammer (Bullish)")
        if upper_wick >= 2 * body and lower_wick <= 0.3 * body:
            patterns.append("⬆️ Inverted Hammer")

    # Doji
    if candle_range > 0 and body / candle_range < 0.1:
        patterns.append("✳️ Doji (Reversal Alert)")

    # Engulfing
    prev_body = abs(c[-2] - o[-2])
    if c[-2] < o[-2] and c[idx] > o[idx] and body > prev_body:
        patterns.append("🟢 Bullish Engulfing")
    if c[-2] > o[-2] and c[idx] < o[idx] and body > prev_body:
        patterns.append("🔴 Bearish Engulfing")

    # Marubozu (strong momentum)
    if candle_range > 0 and body / candle_range > 0.85:
        if c[idx] > o[idx]:
            patterns.append("💪 Bullish Marubozu")
        else:
            patterns.append("👇 Bearish Marubozu")

    # Morning / Evening Star (3-candle)
    if len(df) >= 3:
        if c[-3] < o[-3] and abs(c[-2]-o[-2]) < 0.003*c[-2] and c[idx] > o[idx]:
            patterns.append("🌅 Morning Star")
        if c[-3] > o[-3] and abs(c[-2]-o[-2]) < 0.003*c[-2] and c[idx] < o[idx]:
            patterns.append("🌇 Evening Star")

    return patterns if patterns else ["— No Clear Pattern"]

# ─────────────────────────────────────────────
# VOLUME ANALYSIS
# ─────────────────────────────────────────────

def volume_analysis(df):
    if 'volume' not in df.columns or len(df) < 20:
        return 0, "N/A", False
    vol_avg20 = df['volume'].rolling(20).mean().iloc[-1]
    vol_last  = df['volume'].iloc[-1]
    vol_ratio = safe_float(vol_last / vol_avg20) if vol_avg20 > 0 else 0
    surge     = vol_ratio >= 1.5
    label     = f"{vol_ratio:.1f}x avg"
    return vol_ratio, label, surge

# ─────────────────────────────────────────────
# MULTI-FACTOR SCORING ENGINE  (0 – 100)
# ─────────────────────────────────────────────

def score_ticker(df):
    """
    Factors:
      1. Trend   : Price vs EMA20, EMA50        (0-25)
      2. Momentum: RSI 30-65 sweet-spot, MACD   (0-25)
      3. Volume  : Volume surge confirmation    (0-20)
      4. BB      : Near lower band (buy zone)   (0-15)
      5. Candle  : Pattern bonus                (0-15)
    """
    if df.empty or len(df) < 52:
        return 0, {}

    df = df.copy()
    df['ema20']  = ta.ema(df['close'], length=20)
    df['ema50']  = ta.ema(df['close'], length=50)
    df['rsi']    = ta.rsi(df['close'], length=14)
    df['atr']    = ta.atr(df['high'], df['low'], df['close'], length=14)
    macd_df      = ta.macd(df['close'], fast=12, slow=26, signal=9)
    if macd_df is not None and not macd_df.empty:
        df['macd']   = macd_df.iloc[:, 0]
        df['signal'] = macd_df.iloc[:, 1]
        df['hist']   = macd_df.iloc[:, 2]
    else:
        df['macd'] = df['signal'] = df['hist'] = 0

    bb = ta.bbands(df['close'], length=20, std=2)
    if bb is not None and not bb.empty:
        df['bb_upper'] = bb.iloc[:, 0]
        df['bb_mid']   = bb.iloc[:, 1]
        df['bb_lower'] = bb.iloc[:, 2]
    else:
        df['bb_upper'] = df['bb_mid'] = df['bb_lower'] = df['close']

    l = df.iloc[-1]
    score = 0
    detail = {}

    # 1. TREND (0-25)
    trend_score = 0
    close_v = safe_float(l['close'])
    ema20_v  = safe_float(l['ema20'])
    ema50_v  = safe_float(l['ema50'])
    if close_v > ema20_v:
        trend_score += 12
    if close_v > ema50_v:
        trend_score += 8
    gap_pct = (close_v - ema20_v) / ema20_v * 100 if ema20_v else 0
    if -1 <= gap_pct <= 3:  # near but above EMA20 = sweet spot
        trend_score += 5
    score += trend_score
    detail['Trend'] = trend_score

    # 2. MOMENTUM (0-25)
    mom_score = 0
    rsi_v    = safe_float(l['rsi'])
    macd_v   = safe_float(l['macd'])
    signal_v = safe_float(l['signal'])
    hist_v   = safe_float(l['hist'])
    if 40 <= rsi_v <= 60:
        mom_score += 15
    elif 30 <= rsi_v < 40 or 60 < rsi_v <= 65:
        mom_score += 8
    if macd_v > signal_v:
        mom_score += 7
    if hist_v > 0 and hist_v > safe_float(df['hist'].iloc[-2]):  # MACD hist increasing
        mom_score += 3
    score += mom_score
    detail['Momentum'] = mom_score

    # 3. VOLUME (0-20)
    vol_ratio, _, surge = volume_analysis(df)
    vol_score = min(int(vol_ratio * 8), 20)
    score += vol_score
    detail['Volume'] = vol_score

    # 4. BOLLINGER BAND (0-15)
    bb_score = 0
    bb_low_v  = safe_float(l['bb_lower'])
    bb_mid_v  = safe_float(l['bb_mid'])
    if close_v <= bb_low_v * 1.01:        # at/below lower band
        bb_score = 15
    elif close_v <= bb_mid_v:             # below midline
        bb_score = 7
    score += bb_score
    detail['BB Zone'] = bb_score

    # 5. CANDLE PATTERN (0-15)
    patterns  = detect_patterns(df)
    pat_score = 0
    for p in patterns:
        if any(kw in p for kw in ['Bullish Engulfing', 'Morning Star', 'Hammer', 'Marubozu']):
            pat_score = 15
            break
        elif 'Doji' in p or 'Inverted' in p:
            pat_score = max(pat_score, 5)
    score += pat_score
    detail['Pattern'] = pat_score

    return min(score, 100), detail

# ─────────────────────────────────────────────
# SUPPORT / RESISTANCE (Pivot-based)
# ─────────────────────────────────────────────

def calc_support_resistance(df):
    if len(df) < 20:
        return [], []
    highs = df['high'].rolling(5, center=True).max()
    lows  = df['low'].rolling(5, center=True).min()
    res_levels = sorted(df[df['high'] == highs]['high'].dropna().unique(), reverse=True)[:3]
    sup_levels = sorted(df[df['low']  == lows ]['low'].dropna().unique())[:3]
    return list(res_levels), list(sup_levels)

# ─────────────────────────────────────────────
# FULL TICKER ANALYSIS
# ─────────────────────────────────────────────

def analyze_ticker(ticker, period="1y"):
    df = yf.download(ticker, period=period, progress=False)
    df = clean_df(df)
    if df.empty or len(df) < 52:
        return None

    df['ema20'] = ta.ema(df['close'], length=20)
    df['ema50'] = ta.ema(df['close'], length=50)
    df['rsi']   = ta.rsi(df['close'], length=14)
    df['atr']   = ta.atr(df['high'], df['low'], df['close'], length=14)

    macd_df = ta.macd(df['close'], fast=12, slow=26, signal=9)
    if macd_df is not None and not macd_df.empty:
        df['macd']   = macd_df.iloc[:, 0]
        df['macd_s'] = macd_df.iloc[:, 1]
        df['macd_h'] = macd_df.iloc[:, 2]
    else:
        df['macd'] = df['macd_s'] = df['macd_h'] = 0

    bb = ta.bbands(df['close'], length=20, std=2)
    if bb is not None and not bb.empty:
        df['bb_upper'] = bb.iloc[:, 0]
        df['bb_mid']   = bb.iloc[:, 1]
        df['bb_lower'] = bb.iloc[:, 2]
    else:
        df['bb_upper'] = df['bb_mid'] = df['bb_lower'] = df['close']

    df['vol_avg20'] = df['volume'].rolling(20).mean()

    return df

# ─────────────────────────────────────────────
# GENERATE SIGNAL
# ─────────────────────────────────────────────

def get_signal(df, score):
    l = df.iloc[-1]
    close_v  = safe_float(l['close'])
    ema20_v  = safe_float(l['ema20'])
    ema50_v  = safe_float(l['ema50'])
    rsi_v    = safe_float(l['rsi'])
    macd_v   = safe_float(l['macd'])
    macd_s_v = safe_float(l['macd_s'])
    atr_v    = safe_float(l['atr'])

    sl = close_v - (1.5 * atr_v)
    tp = close_v + (2.5 * atr_v)
    rr = round((tp - close_v) / (close_v - sl), 2) if (close_v - sl) > 0 else 0

    if score >= 65 and close_v > ema20_v and rsi_v < 65 and macd_v > macd_s_v:
        signal = "STRONG BUY"
        signal_color = "#00ff88"
    elif score >= 50 and close_v > ema20_v and rsi_v < 70:
        signal = "BUY / ACCUMULATE"
        signal_color = "#44dd77"
    elif rsi_v > 75 or (close_v < ema50_v and close_v < ema20_v):
        signal = "SELL / AVOID"
        signal_color = "#ff4466"
    elif score < 35:
        signal = "WEAK / SKIP"
        signal_color = "#ff8844"
    else:
        signal = "HOLD / WATCH"
        signal_color = "#ffcc00"

    return signal, signal_color, sl, tp, rr

# ─────────────────────────────────────────────
# MARKET DATA
# ─────────────────────────────────────────────

market_data = {
    "FINANCE":    ["BBCA.JK", "BBRI.JK", "BMRI.JK", "BBNI.JK", "BRIS.JK", "ARTO.JK", "BNGA.JK", "PNBN.JK"],
    "ENERGY":     ["ADRO.JK", "ITMG.JK", "PTBA.JK", "MEDC.JK", "AKRA.JK", "PGAS.JK", "ENRG.JK"],
    "HEALTHCARE": ["MIKA.JK", "HEAL.JK", "SILO.JK", "KLBF.JK", "SIDO.JK", "PYFA.JK"],
    "BASIC INFO": ["ANTM.JK", "TINS.JK", "MDKA.JK", "SMGR.JK", "INTP.JK", "TPIA.JK", "INCO.JK"],
    "CONSUMER":   ["ACES.JK", "MAPI.JK", "AMRT.JK", "ICBP.JK", "INDF.JK", "GGRM.JK", "UNVR.JK", "HMSP.JK"],
    "INFRA":      ["TLKM.JK", "ISAT.JK", "EXCL.JK", "TOWR.JK", "TBIG.JK", "ADHI.JK"],
    "PROPERTY":   ["BSDE.JK", "PWON.JK", "CTRA.JK", "SMRA.JK", "SSIA.JK", "LPKR.JK"],
    "TECH/IDX30": ["GOTO.JK", "BUKA.JK", "EMTK.JK", "MTEL.JK"],
}

sector_proxy = {
    "FINANCE": "BBCA.JK", "ENERGY": "ADRO.JK", "HEALTHCARE": "KLBF.JK",
    "BASIC":   "ANTM.JK", "CONSUMER": "ICBP.JK", "INFRA": "TLKM.JK",
    "PROPERTY":"BSDE.JK", "TECH":  "GOTO.JK"
}

# ─────────────────────────────────────────────
# UI START
# ─────────────────────────────────────────────

st.markdown("""
<h1 style='text-align:center; color:#00ccff; letter-spacing:4px; font-family:monospace;'>
⚡ TERMINAL SCREENING STOCK v2
</h1>
<p style='text-align:center; color:#668; font-family:monospace; margin-top:-10px;'>
Multi-Factor Daily Trade Analyzer — IDX Market
</p>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# SECTION 1: MARKET PULSE
# ─────────────────────────────────────────────

c1, c2 = st.columns([1, 1])

with c1:
    st.subheader("📈 IHSG Market Pulse (1Y)")
    ihsg = yf.download("^JKSE", period="1y", progress=False)
    ihsg = clean_df(ihsg)
    ihsg_change = 0.0
    if not ihsg.empty:
        ihsg_change = ((ihsg['close'].iloc[-1] - ihsg['close'].iloc[-2]) / ihsg['close'].iloc[-2]) * 100
        ihsg['ma20'] = ihsg['close'].rolling(20).mean()
        fig_ihsg = go.Figure()
        fig_ihsg.add_trace(go.Scatter(x=ihsg.index, y=ihsg['close'], fill='tozeroy',
                                      line_color='#00ccff', fillcolor='rgba(0,204,255,0.08)', name='IHSG'))
        fig_ihsg.add_trace(go.Scatter(x=ihsg.index, y=ihsg['ma20'],
                                      line=dict(color='orange', width=1.5, dash='dot'), name='MA20'))
        fig_ihsg.update_layout(height=260, template='plotly_dark', margin=dict(l=0,r=0,t=0,b=0),
                                showlegend=False, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig_ihsg, use_container_width=True)
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Last", f"{ihsg['close'].iloc[-1]:,.0f}")
        col_b.metric("Change", f"{ihsg_change:+.2f}%")
        col_c.metric("52W High", f"{ihsg['high'].max():,.0f}")

with c2:
    st.subheader("🗺️ Sectoral Momentum (5D)")
    sector_list = []
    for s, t in sector_proxy.items():
        try:
            px_data = clean_df(yf.download(t, period="10d", progress=False))
            if not px_data.empty and len(px_data) >= 5:
                perf = ((px_data['close'].iloc[-1] - px_data['close'].iloc[-5]) / px_data['close'].iloc[-5]) * 100
                sector_list.append({"Sector": s, "Performance": round(safe_float(perf), 2),
                                    "Parent": "Market", "Size": 10})
        except:
            continue
    if sector_list:
        df_sec = pd.DataFrame(sector_list)
        fig_tree = px.treemap(df_sec, path=['Parent', 'Sector'], values='Size',
                              color='Performance', color_continuous_scale='RdYlGn', range_color=[-3, 3])
        fig_tree.update_layout(height=260, margin=dict(l=0,r=0,t=0,b=0), template='plotly_dark')
        st.plotly_chart(fig_tree, use_container_width=True)

        best = max(sector_list, key=lambda x: x['Performance'])
        worst = min(sector_list, key=lambda x: x['Performance'])
        st.caption(f"🏆 Strongest: **{best['Sector']}** ({best['Performance']:+.2f}%)  |  "
                   f"⚠️ Weakest: **{worst['Sector']}** ({worst['Performance']:+.2f}%)")

st.divider()

# ─────────────────────────────────────────────
# SECTION 2: SINGLE STOCK DEEP ANALYSIS
# ─────────────────────────────────────────────

st.subheader("🔬 Deep Tactical Analysis")
search_col, nav_col, tf_col = st.columns([1, 2, 1])

with search_col:
    manual_ticker = st.text_input("🔍 Kode Saham (contoh: BBRI):", "").upper()
with nav_col:
    sec_choice = st.selectbox("📂 Atau pilih dari Sektor:", ["None"] + list(market_data.keys()))
with tf_col:
    timeframe = st.selectbox("📅 Timeframe:", ["6mo", "1y", "2y"], index=1)

target = None
if manual_ticker:
    target = manual_ticker if manual_ticker.endswith(".JK") else f"{manual_ticker}.JK"
elif sec_choice != "None":
    target = st.selectbox("Pilih Saham:", market_data[sec_choice])

if target:
    with st.spinner(f"Menganalisis {target}..."):
        df = analyze_ticker(target, period=timeframe)

    if df is not None and not df.empty:
        score, score_detail = score_ticker(df)
        signal, sig_color, sl, tp, rr = get_signal(df, score)
        l = df.iloc[-1]
        patterns = detect_patterns(df)
        vol_ratio, vol_label, vol_surge = volume_analysis(df)
        res_levels, sup_levels = calc_support_resistance(df)

        close_v  = safe_float(l['close'])
        rsi_v    = safe_float(l['rsi'])
        atr_v    = safe_float(l['atr'])
        ema20_v  = safe_float(l['ema20'])
        ema50_v  = safe_float(l['ema50'])
        macd_v   = safe_float(l['macd'])
        macd_s_v = safe_float(l['macd_s'])

        # Score color
        score_class = "score-high" if score >= 65 else ("score-mid" if score >= 45 else "score-low")
        sig_tag_class = "tag-buy" if "BUY" in signal else ("tag-sell" if "SELL" in signal or "WEAK" in signal else "tag-hold")

        st.markdown(f"### {target} — Tactical Command")

        # Row 1: Score + Signal + Key Metrics
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.markdown(f"""<div class='metric-card'>
                <div style='color:#888;font-size:12px'>CONFLUENCE SCORE</div>
                <div class='{score_class}'>{score}/100</div>
            </div>""", unsafe_allow_html=True)
        with col2:
            st.markdown(f"""<div class='metric-card'>
                <div style='color:#888;font-size:12px'>SIGNAL</div>
                <div style='margin-top:6px'><span class='{sig_tag_class}'>{signal}</span></div>
            </div>""", unsafe_allow_html=True)
        with col3:
            st.metric("RSI (14)", f"{rsi_v:.1f}",
                      delta="Oversold" if rsi_v < 35 else ("Overbought" if rsi_v > 70 else "Normal"))
        with col4:
            st.metric("Volume vs Avg", vol_label,
                      delta="🔥 SURGE" if vol_surge else None)
        with col5:
            st.metric("ATR (14)", f"{atr_v:.0f}",
                      help="Average True Range — ukuran volatilitas harian")

        st.write("")

        # Row 2: SL / TP / RR / EMA / MACD
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.error(f"❌ Stop Loss: {sl:,.0f}")
        c2.success(f"✅ Take Profit: {tp:,.0f}")
        c3.info(f"⚖️ Risk:Reward = 1:{rr}")
        ema_gap = ((close_v - ema20_v) / ema20_v * 100) if ema20_v else 0
        c4.metric("vs EMA20", f"{ema_gap:+.2f}%",
                  delta="✅ Above" if ema_gap > 0 else "⚠️ Below")
        macd_cross = "Bullish" if macd_v > macd_s_v else "Bearish"
        c5.metric("MACD Cross", macd_cross,
                  delta="↑" if macd_v > macd_s_v else "↓")

        # Row 3: Score Breakdown + Patterns + S/R Levels
        left_col, mid_col, right_col = st.columns([1, 1, 1])

        with left_col:
            st.markdown("**📊 Score Breakdown**")
            score_df = pd.DataFrame(list(score_detail.items()), columns=["Factor", "Score"])
            score_df["Max"] = [25, 25, 20, 15, 15]
            fig_score = go.Figure(go.Bar(
                x=score_df["Score"], y=score_df["Factor"], orientation='h',
                marker_color=['#00ff88' if s/m >= 0.7 else ('#ffcc00' if s/m >= 0.4 else '#ff4466')
                              for s, m in zip(score_df["Score"], score_df["Max"])],
                text=score_df["Score"], textposition='auto'
            ))
            fig_score.update_layout(height=200, template='plotly_dark',
                                    margin=dict(l=0,r=0,t=0,b=0), showlegend=False,
                                    xaxis=dict(range=[0, 25]))
            st.plotly_chart(fig_score, use_container_width=True)

        with mid_col:
            st.markdown("**🕯️ Candle Patterns**")
            for p in patterns:
                st.write(p)
            st.markdown("**📐 Support/Resistance**")
            if res_levels:
                st.markdown(f"🔴 R: {' | '.join([f'{r:,.0f}' for r in res_levels[:2]])}")
            if sup_levels:
                st.markdown(f"🟢 S: {' | '.join([f'{s:,.0f}' for s in sup_levels[:2]])}")

        with right_col:
            st.markdown("**💡 Trade Setup**")
            risk   = close_v - sl
            reward = tp - close_v
            lot_10m = 10_000_000 / close_v / 100 if close_v > 0 else 0
            st.markdown(f"""
            - 💰 **Entry Zone:** {close_v:,.0f} – {close_v * 1.005:,.0f}
            - ❌ **Max Loss / lot:** Rp {risk * 100:,.0f}
            - ✅ **Target Gain / lot:** Rp {reward * 100:,.0f}
            - 📦 **Est. Lot (modal 10jt):** {lot_10m:.0f} lot
            - ⏱️ **Hold Estimate:** 1–3 hari
            """)

        # ─── CHART ───
        st.markdown("---")
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                            row_heights=[0.55, 0.25, 0.20],
                            vertical_spacing=0.04,
                            subplot_titles=("Price + Indicators", "MACD", "RSI + Volume"))

        # Candlestick
        fig.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['high'],
                                     low=df['low'], close=df['close'],
                                     name='Candle', increasing_line_color='#00ff88',
                                     decreasing_line_color='#ff4466'), row=1, col=1)

        # EMA
        fig.add_trace(go.Scatter(x=df.index, y=df['ema20'],
                                 line=dict(color='orange', width=1.8), name='EMA20'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['ema50'],
                                 line=dict(color='#00bfff', width=1.2, dash='dot'), name='EMA50'), row=1, col=1)

        # Bollinger Bands
        fig.add_trace(go.Scatter(x=df.index, y=df['bb_upper'],
                                 line=dict(color='rgba(200,200,255,0.4)', width=1),
                                 name='BB Upper', showlegend=False), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['bb_lower'],
                                 fill='tonexty', fillcolor='rgba(100,100,255,0.05)',
                                 line=dict(color='rgba(200,200,255,0.4)', width=1),
                                 name='BB Lower', showlegend=False), row=1, col=1)

        # SL/TP
        fig.add_hline(y=sl, line_dash="dash", line_color="#ff4466",
                      annotation_text=f"SL {sl:,.0f}", row=1, col=1)
        fig.add_hline(y=tp, line_dash="dash", line_color="#00ff88",
                      annotation_text=f"TP {tp:,.0f}", row=1, col=1)

        # MACD
        colors_hist = ['#00ff88' if v >= 0 else '#ff4466' for v in df['macd_h'].fillna(0)]
        fig.add_trace(go.Bar(x=df.index, y=df['macd_h'],
                             marker_color=colors_hist, name='MACD Hist', showlegend=False), row=2, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['macd'],
                                 line=dict(color='#00ccff', width=1.5), name='MACD'), row=2, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['macd_s'],
                                 line=dict(color='orange', width=1.5), name='Signal'), row=2, col=1)

        # RSI
        fig.add_trace(go.Scatter(x=df.index, y=df['rsi'],
                                 line=dict(color='#bf7fff', width=1.5), name='RSI'), row=3, col=1)
        fig.add_hline(y=70, line_dash="dot", line_color="red", row=3, col=1)
        fig.add_hline(y=30, line_dash="dot", line_color="green", row=3, col=1)

        # Volume bars (scaled to chart)
        vol_scaled = df['volume'] / df['volume'].max() * 30
        vol_colors = ['#00ff88' if c >= o else '#ff4466'
                      for c, o in zip(df['close'], df['open'])]
        fig.add_trace(go.Bar(x=df.index, y=vol_scaled, marker_color=vol_colors,
                             name='Volume', opacity=0.4, showlegend=False), row=3, col=1)

        fig.update_layout(height=700, template='plotly_dark',
                          xaxis_rangeslider_visible=False,
                          legend=dict(orientation='h', y=1.02),
                          margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.warning(f"Data tidak cukup untuk {target}. Coba ticker lain.")

st.divider()

# ─────────────────────────────────────────────
# SECTION 3: DAILY PICK SCANNER
# ─────────────────────────────────────────────

st.subheader("🎯 Daily Pick Scanner — Multi-Factor Ranking")

scan_col1, scan_col2, scan_col3 = st.columns(3)
with scan_col1:
    scan_sectors = st.multiselect("Filter Sektor:", list(market_data.keys()),
                                   default=list(market_data.keys()))
with scan_col2:
    min_score = st.slider("Min Confluence Score:", 0, 100, 50)
with scan_col3:
    top_n = st.number_input("Tampilkan Top N:", min_value=5, max_value=30, value=10)

if st.button("🚀 SCAN SEKARANG", use_container_width=True):
    all_tickers = []
    for sec in scan_sectors:
        all_tickers.extend(market_data.get(sec, []))
    all_tickers = list(set(all_tickers))

    results = []
    prog = st.progress(0)
    status_txt = st.empty()

    for i, t in enumerate(all_tickers):
        prog.progress((i + 1) / len(all_tickers))
        status_txt.text(f"Scanning {t}... ({i+1}/{len(all_tickers)})")
        try:
            d = clean_df(yf.download(t, period="60d", progress=False))
            if d.empty or len(d) < 52:
                continue
            s, detail = score_ticker(d)
            if s < min_score:
                continue
            signal, sig_color, sl, tp, rr = get_signal(d, s)
            if "SELL" in signal or "WEAK" in signal:
                continue
            vol_r, vol_lbl, surge = volume_analysis(d)
            patterns = detect_patterns(d)
            l = d.iloc[-1]
            results.append({
                "Ticker":      t,
                "Score":       s,
                "Signal":      signal,
                "Price":       int(safe_float(l['close'])),
                "RSI":         round(safe_float(l['rsi']), 1),
                "MACD Cross":  "✅" if safe_float(l['macd'] if 'macd' in d.columns else 0) > safe_float(l['macd_s'] if 'macd_s' in d.columns else 0) else "❌",
                "Volume":      vol_lbl,
                "Vol Surge":   "🔥" if surge else "",
                "SL":          int(sl),
                "TP":          int(tp),
                "R:R":         f"1:{rr}",
                "Pattern":     patterns[0] if patterns else "—",
            })
        except Exception as e:
            continue

    prog.empty()
    status_txt.empty()

    if results:
        df_res = pd.DataFrame(results).sort_values("Score", ascending=False).head(top_n)

        # Color-coded score
        def color_score(val):
            if val >= 65:
                return 'background-color: #00401a; color: #00ff88'
            elif val >= 50:
                return 'background-color: #404000; color: #ffcc00'
            else:
                return 'background-color: #400010; color: #ff8888'

        st.success(f"✅ Ditemukan {len(df_res)} saham kandidat dari {len(all_tickers)} yang discan.")
        styled = df_res.style.applymap(color_score, subset=['Score'])
        st.dataframe(styled, use_container_width=True, hide_index=True)

        # Top 3 spotlight
        st.markdown("### 🏆 Top 3 Picks Hari Ini")
        top3 = df_res.head(3)
        cols = st.columns(3)
        for i, (_, row) in enumerate(top3.iterrows()):
            with cols[i]:
                score_class = "score-high" if row['Score'] >= 65 else "score-mid"
                st.markdown(f"""
                <div class='metric-card'>
                    <div style='font-size:18px; font-weight:bold; color:#00ccff'>#{i+1} {row['Ticker']}</div>
                    <div class='{score_class}'>{row['Score']}/100</div>
                    <div style='color:#aaa; font-size:13px'>Price: {row['Price']:,} | RSI: {row['RSI']}</div>
                    <div style='margin-top:6px'><span class='tag-buy'>{row['Signal']}</span></div>
                    <div style='color:#666; font-size:12px; margin-top:6px'>{row['Pattern']}</div>
                    <div style='font-size:12px; margin-top:4px'>
                        ❌ SL: {row['SL']:,}  &nbsp; ✅ TP: {row['TP']:,}  &nbsp; ⚖️ {row['R:R']}
                    </div>
                </div>
                """, unsafe_allow_html=True)

        # Market context review
        st.divider()
        st.subheader("📋 Market Context Review")
        market_bias = "BULLISH ↑" if ihsg_change > 0.3 else ("BEARISH ↓" if ihsg_change < -0.3 else "SIDEWAYS ↔")
        bias_color  = "#00ff88" if "BULL" in market_bias else ("#ff4466" if "BEAR" in market_bias else "#ffcc00")

        st.markdown(f"""
        <div style='background:#0d1a2a; border:1px solid #1e3a5f; border-radius:12px; padding:20px;'>
            <b>🌐 IHSG Bias:</b> <span style='color:{bias_color}; font-weight:bold'>{market_bias}</span> 
            ({ihsg['close'].iloc[-1]:,.0f}, {ihsg_change:+.2f}%)
            <br><br>
            <b>📌 Panduan Eksekusi:</b>
            <ol>
            <li>Prioritaskan saham dengan <b>Score ≥ 65</b> dan konfirmasi <b>Volume Surge 🔥</b>.</li>
            <li>Jangan entry jika IHSG turun {'>'} 1% — tunggu konfirmasi reversal.</li>
            <li>Gunakan <b>SL ketat</b> (1.5x ATR). Jangan holding merugi lebih dari 2x SL.</li>
            <li>R:R minimum 1:2 — lewati setup dengan R:R {'<'} 1:1.5.</li>
            <li>Jika <b>MACD Cross ✅ + Volume Surge 🔥 + Score ≥ 70</b> → Setup Premium.</li>
            </ol>
        </div>
        """, unsafe_allow_html=True)

    else:
        st.warning("Tidak ada saham yang memenuhi kriteria. Coba turunkan min score.")
