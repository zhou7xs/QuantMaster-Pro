# -*- coding: utf-8 -*-
"""
QuantMaster Pro - 专业A股量化交易系统
功能：行情数据 / 策略编辑器 / 历史回测 / 模拟交易 / 实盘终端 / 绩效分析 / 风险管理
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import akshare as ak
from datetime import datetime, timedelta
import time
import random
import warnings
import json

warnings.filterwarnings("ignore")

# ═══════════════════════════════════════════
# 页面基础配置
# ═══════════════════════════════════════════
st.set_page_config(
    page_title="QuantMaster Pro",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ═══════════════════════════════════════════
# 全局CSS（含可折叠导航栏样式）
# ═══════════════════════════════════════════
st.markdown("""
<style>
/* ---- 主色调 ---- */
:root {
    --primary: #1565c0;
    --primary-light: #1976d2;
    --accent: #e53935;
    --accent-green: #43a047;
    --bg-sidebar: #0d1b2a;
    --bg-card: #ffffff;
    --text-light: #ecf0f1;
    --border: #e0e0e0;
}

/* ---- 侧边栏背景 ---- */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d1b2a 0%, #1a2f4a 100%) !important;
    min-width: 240px !important;
}
section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] div, section[data-testid="stSidebar"] label { color: #ecf0f1 !important; }

/* ---- 顶部 Banner ---- */
.qm-banner {
    background: linear-gradient(135deg, #0d47a1, #1565c0 50%, #283593);
    padding: 1.6rem 2rem;
    border-radius: 14px;
    color: white;
    margin-bottom: 1.6rem;
    box-shadow: 0 4px 24px rgba(13,71,161,0.25);
    display: flex;
    align-items: center;
    gap: 1rem;
}
.qm-banner h1 { margin: 0; font-size: 1.7rem; }
.qm-banner p  { margin: 0.2rem 0 0; opacity: 0.85; font-size: 0.9rem; }

/* ---- 指标卡片 ---- */
.metric-card {
    background: #fff;
    border-radius: 12px;
    padding: 1.1rem 1.3rem;
    box-shadow: 0 2px 12px rgba(0,0,0,0.07);
    border-left: 5px solid var(--primary);
    transition: transform 0.18s, box-shadow 0.18s;
    margin-bottom: 0.6rem;
}
.metric-card:hover { transform: translateY(-3px); box-shadow: 0 6px 20px rgba(0,0,0,0.12); }
.metric-card .val  { font-size: 1.6rem; font-weight: 700; }
.metric-card .lbl  { font-size: 0.82rem; color: #888; margin-top: 2px; }

/* ---- 红涨绿跌 ---- */
.up   { color: #e53935 !important; font-weight: 600; }
.down { color: #43a047 !important; font-weight: 600; }

/* ---- 导航按钮（侧边栏） ---- */
.nav-btn {
    display: block;
    width: 100%;
    padding: 0.65rem 1rem;
    margin: 3px 0;
    border: none;
    border-radius: 8px;
    background: transparent;
    color: #b0bec5 !important;
    font-size: 0.93rem;
    text-align: left;
    cursor: pointer;
    transition: background 0.15s, color 0.15s;
}
.nav-btn:hover   { background: rgba(255,255,255,0.08); color: #fff !important; }
.nav-btn.active  { background: rgba(25,118,210,0.5); color: #fff !important; font-weight: 600; }
.nav-section     { color: #78909c !important; font-size: 0.73rem; letter-spacing: 1px;
                   text-transform: uppercase; padding: 0.8rem 1rem 0.3rem; }

/* ---- 策略代码编辑器 ---- */
.code-block {
    background: #1e1e1e;
    color: #d4d4d4;
    font-family: 'Consolas', monospace;
    font-size: 13px;
    border-radius: 8px;
    padding: 1rem;
    overflow: auto;
    max-height: 420px;
}

/* ---- 预警卡片 ---- */
.alert-high { background: #fff3e0; border-left: 4px solid #e53935; }
.alert-mid  { background: #e8f5e9; border-left: 4px solid #43a047; }
.alert-low  { background: #e3f2fd; border-left: 4px solid #1976d2; }
.alert-box  { padding: 10px 14px; border-radius: 8px; margin-bottom: 8px; font-size: 0.9rem; }

/* ---- 侧边栏强制显示（保留header，否则折叠按钮消失） ---- */
header[data-testid="stHeader"] { display: block !important; }
#MainMenu, footer { visibility: visible !important; }
.stDeployButton { display: none !important; }

/* ---- 侧边栏模块导航按钮（彩色区分） ---- */
.nav-market  { display: block; width: 100%; padding: .6rem .9rem; margin: 3px 0; border: none; border-radius: 8px; background: rgba(21,101,192,.35); color: #90caf9!important; font-size: .88rem; text-align: left; cursor: pointer; transition: background .15s, color .15s; }
.nav-market:hover, .nav-market.active { background: rgba(21,101,192,.7); color: #fff!important; font-weight: 600; }
.nav-strategy { display: block; width: 100%; padding: .6rem .9rem; margin: 3px 0; border: none; border-radius: 8px; background: rgba(46,125,50,.30); color: #a5d6a7!important; font-size: .88rem; text-align: left; cursor: pointer; transition: background .15s, color .15s; }
.nav-strategy:hover, .nav-strategy.active { background: rgba(46,125,50,.65); color: #fff!important; font-weight: 600; }
.nav-backtest { display: block; width: 100%; padding: .6rem .9rem; margin: 3px 0; border: none; border-radius: 8px; background: rgba(142,36,170,.28); color: #ce93d8!important; font-size: .88rem; text-align: left; cursor: pointer; transition: background .15s, color .15s; }
.nav-backtest:hover, .nav-backtest.active { background: rgba(142,36,170,.65); color: #fff!important; font-weight: 600; }
.nav-paper  { display: block; width: 100%; padding: .6rem .9rem; margin: 3px 0; border: none; border-radius: 8px; background: rgba(255,111,0,.28); color: #ffcc80!important; font-size: .88rem; text-align: left; cursor: pointer; transition: background .15s, color .15s; }
.nav-paper:hover, .nav-paper.active { background: rgba(255,111,0,.65); color: #fff!important; font-weight: 600; }
.nav-live   { display: block; width: 100%; padding: .6rem .9rem; margin: 3px 0; border: none; border-radius: 8px; background: rgba(229,57,53,.28); color: #ef9a9a!important; font-size: .88rem; text-align: left; cursor: pointer; transition: background .15s, color .15s; }
.nav-live:hover, .nav-live.active { background: rgba(229,57,53,.65); color: #fff!important; font-weight: 600; }
.nav-report { display: block; width: 100%; padding: .6rem .9rem; margin: 3px 0; border: none; border-radius: 8px; background: rgba(0,172,193,.28); color: #80deea!important; font-size: .88rem; text-align: left; cursor: pointer; transition: background .15s, color .15s; }
.nav-report:hover, .nav-report.active { background: rgba(0,172,193,.65); color: #fff!important; font-weight: 600; }
.nav-risk   { display: block; width: 100%; padding: .6rem .9rem; margin: 3px 0; border: none; border-radius: 8px; background: rgba(255,160,0,.28); color: #ffe082!important; font-size: .88rem; text-align: left; cursor: pointer; transition: background .15s, color .15s; }
.nav-risk:hover, .nav-risk.active { background: rgba(255,160,0,.65); color: #333!important; font-weight: 600; }
.nav-divider { border: none; border-top: 1px solid rgba(255,255,255,.12); margin: 8px 0; }

/* ---- 标签页样式 ---- */
button[data-baseweb="tab"] { font-size: 0.9rem; }

/* ---- 模拟交易持仓表 ---- */
.pos-table th { background: #1565c0; color: white; padding: 8px 12px; }
.pos-table td { padding: 7px 12px; font-size: 13px; border-bottom: 1px solid #f0f0f0; }
.pos-table tr:hover td { background: #f5f5f5; }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════
# Session State 初始化
# ═══════════════════════════════════════════
if "page" not in st.session_state:
    st.session_state["page"] = "行情数据"
if "sim_positions" not in st.session_state:
    st.session_state["sim_positions"] = {}   # 模拟持仓 {code: {shares, cost, name}}
if "sim_capital" not in st.session_state:
    st.session_state["sim_capital"] = 1_000_000.0   # 模拟账户初始资金100万
if "sim_trades" not in st.session_state:
    st.session_state["sim_trades"] = []      # 模拟交易记录
if "live_orders" not in st.session_state:
    st.session_state["live_orders"] = []     # 实盘委托记录（演示）
if "strategy_code" not in st.session_state:
    st.session_state["strategy_code"] = """# QuantMaster Pro 策略编辑器
# 支持 Python 3.12，可使用 pandas / numpy / akshare
# 函数签名：strategy(df) -> signals_df
# df 列：date, open, high, low, close, volume
# 返回：含 date, signal('BUY'/'SELL'), price 列的 DataFrame

import pandas as pd
import numpy as np

def strategy(df: pd.DataFrame) -> pd.DataFrame:
    \"\"\"双均线金叉死叉策略（默认示例）\"\"\"
    df = df.copy()
    df['MA5']  = df['close'].rolling(5).mean()
    df['MA20'] = df['close'].rolling(20).mean()
    df = df.dropna()
    
    signals = []
    position = 0
    for i in range(1, len(df)):
        if df['MA5'].iloc[i] > df['MA20'].iloc[i] and df['MA5'].iloc[i-1] <= df['MA20'].iloc[i-1]:
            if position == 0:
                signals.append({'date': df['date'].iloc[i], 'signal': 'BUY',  'price': df['close'].iloc[i]})
                position = 1
        elif df['MA5'].iloc[i] < df['MA20'].iloc[i] and df['MA5'].iloc[i-1] >= df['MA20'].iloc[i-1]:
            if position == 1:
                signals.append({'date': df['date'].iloc[i], 'signal': 'SELL', 'price': df['close'].iloc[i]})
                position = 0
    
    return pd.DataFrame(signals) if signals else pd.DataFrame(columns=['date','signal','price'])
"""


# ═══════════════════════════════════════════
# 数据层：重试 + 备用 + 模拟兜底
# ═══════════════════════════════════════════

def safe_request(func, max_retries=2, delay=2, fallback=None):
    for i in range(max_retries):
        try:
            r = func()
            if r is not None and not (isinstance(r, pd.DataFrame) and r.empty):
                return r
        except Exception:
            if i < max_retries - 1:
                time.sleep(delay)
    if fallback:
        try:
            return fallback()
        except Exception:
            pass
    return None


def _mock_stock_list(n=200):
    random.seed(42)
    names = ["平安银行","万科A","美的集团","格力电器","比亚迪","宁德时代","贵州茅台","五粮液",
             "中国平安","招商银行","工商银行","建设银行","隆基绿能","阳光电源","通威股份",
             "紫金矿业","中国神华","三一重工","立讯精密","京东方A","恒瑞医药","迈瑞医疗",
             "药明康德","中国中免","长江电力","中联重科","汇川技术","歌尔股份","TCL科技",
             "兴业银行","中国海油","中国石化","陕西煤业","山西汾酒","泸州老窖","洋河股份"]
    codes = ["000001","000002","000333","000651","002594","300750","600519","000858",
             "601318","600036","601398","601939","601012","300274","600438",
             "601899","601088","600031","002475","000725","600276","300760",
             "603259","601888","600900","000157","300124","002241","000100",
             "601166","600938","600028","601225","600809","000568","002304"]
    while len(names) < n:
        i = len(names)
        names.append(f"股票{i:04d}")
        codes.append(f"{random.randint(600000,699999)}")
    rows = []
    for i in range(n):
        p = round(random.uniform(3, 200), 2)
        pct = round(random.uniform(-10, 10), 2)
        rows.append({
            "代码": codes[i] if i < len(codes) else f"{600000+i}",
            "名称": names[i],
            "最新价": p,
            "涨跌幅": pct,
            "涨跌额": round(p * pct / 100, 2),
            "成交量": random.randint(10000, 50000000),
            "成交额": round(random.uniform(1e6, 5e9), 0),
            "振幅": round(abs(pct) * random.uniform(1, 2.5), 2),
            "换手率": round(random.uniform(0.1, 30), 2),
            "市盈率": round(random.uniform(5, 200), 1),
            "最高": round(p * (1 + abs(pct)/200), 2),
            "最低": round(p * (1 - abs(pct)/200), 2),
        })
    return pd.DataFrame(rows).sort_values("涨跌幅", ascending=False)


def _mock_kline(code, n_days=250):
    rng = random.Random(hash(code))
    p = rng.uniform(10, 100)
    end = datetime.now()
    dates = pd.bdate_range(end=end, periods=n_days)
    rows = []
    for dt in dates:
        chg = rng.gauss(0, 0.018)
        o = p
        c = round(p * (1 + chg), 2)
        h = round(max(o, c) * (1 + rng.uniform(0, 0.012)), 2)
        l = round(min(o, c) * (1 - rng.uniform(0, 0.012)), 2)
        rows.append({"date": pd.Timestamp(dt), "open": round(o,2), "high": h,
                     "low": l, "close": c, "volume": rng.randint(50000, 5000000),
                     "amount": 0, "pct_change": round(chg*100, 2)})
        p = c
    df = pd.DataFrame(rows)
    df["amount"] = df["volume"] * df["close"]
    return df


@st.cache_data(ttl=300)
def get_stock_list():
    def pri():
        df = ak.stock_zh_a_spot_em()
        cols = ["代码","名称","最新价","涨跌幅","涨跌额","成交量","成交额","振幅","换手率","最高","最低"]
        if "市盈率-动态" in df.columns: cols.append("市盈率-动态")
        avail = [c for c in cols if c in df.columns]
        df = df[avail].rename(columns={"市盈率-动态":"市盈率"})
        return df.dropna(subset=["最新价"]).sort_values("涨跌幅", ascending=False)
    r = safe_request(pri, 2, 3)
    if r is not None: return r
    st.warning("⚠️ 网络不通，显示模拟行情数据")
    return _mock_stock_list()


@st.cache_data(ttl=300)
def get_kline(code, period="daily", start="", end=""):
    def pri():
        if period in ("daily","weekly","monthly"):
            df = ak.stock_zh_a_hist(symbol=code, period=period,
                                    start_date=start, end_date=end, adjust="qfq")
        else:
            df = ak.stock_zh_a_hist_min_em(symbol=code,
                                            period=period.replace("min",""), adjust="qfq")
        return df
    df = safe_request(pri, 2, 3)
    if df is None or (isinstance(df, pd.DataFrame) and df.empty):
        st.warning(f"⚠️ {code} K线数据获取失败，显示模拟数据")
        return _mock_kline(code)
    col_map = {"日期":"date","开盘":"open","收盘":"close","最高":"high","最低":"low",
               "成交量":"volume","成交额":"amount","涨跌幅":"pct_change","涨跌额":"change","换手率":"turnover"}
    df = df.rename(columns=col_map)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
    return df


# ═══════════════════════════════════════════
# 技术指标
# ═══════════════════════════════════════════

def add_ma(df, windows=(5,10,20,60)):
    for w in windows:
        df[f"MA{w}"] = df["close"].rolling(w).mean()
    return df

def add_boll(df, w=20, k=2):
    df["BOLL_MID"]  = df["close"].rolling(w).mean()
    std = df["close"].rolling(w).std()
    df["BOLL_UP"]   = df["BOLL_MID"] + k * std
    df["BOLL_DOWN"] = df["BOLL_MID"] - k * std
    return df

def add_rsi(df, n=14):
    d = df["close"].diff()
    g = d.where(d>0,0).rolling(n).mean()
    l = (-d.where(d<0,0)).rolling(n).mean()
    df["RSI"] = 100 - 100/(1+g/l)
    return df

def add_macd(df, f=12, s=26, sig=9):
    ef = df["close"].ewm(span=f, adjust=False).mean()
    es = df["close"].ewm(span=s, adjust=False).mean()
    df["DIF"] = ef - es
    df["DEA"] = df["DIF"].ewm(span=sig, adjust=False).mean()
    df["MACD_HIST"] = 2*(df["DIF"]-df["DEA"])
    return df

def add_kdj(df, n=9):
    lo = df["low"].rolling(n,min_periods=1).min()
    hi = df["high"].rolling(n,min_periods=1).max()
    rsv = (df["close"]-lo)/(hi-lo+1e-9)*100
    df["K"] = rsv.ewm(com=2,adjust=False).mean()
    df["D"] = df["K"].ewm(com=2,adjust=False).mean()
    df["J"] = 3*df["K"]-2*df["D"]
    return df


# ═══════════════════════════════════════════
# 回测引擎
# ═══════════════════════════════════════════

def run_strategy_signals(df, name, **params):
    df = df.copy().dropna(subset=["close"])
    signals = []
    pos = 0
    if name == "均线交叉":
        fast, slow = params.get("fast",5), params.get("slow",20)
        df = add_ma(df, [fast, slow])
        df = df.dropna()
        for i in range(1, len(df)):
            if df[f"MA{fast}"].iloc[i]>df[f"MA{slow}"].iloc[i] and df[f"MA{fast}"].iloc[i-1]<=df[f"MA{slow}"].iloc[i-1]:
                if pos==0: signals.append({"date":df["date"].iloc[i],"signal":"BUY","price":df["close"].iloc[i]}); pos=1
            elif df[f"MA{fast}"].iloc[i]<df[f"MA{slow}"].iloc[i] and df[f"MA{fast}"].iloc[i-1]>=df[f"MA{slow}"].iloc[i-1]:
                if pos==1: signals.append({"date":df["date"].iloc[i],"signal":"SELL","price":df["close"].iloc[i]}); pos=0
    elif name == "RSI":
        df = add_rsi(df, params.get("n",14)); df = df.dropna()
        ob, os_ = params.get("ob",70), params.get("os",30)
        for i in range(1,len(df)):
            r = df["RSI"].iloc[i]
            if r<os_ and pos==0: signals.append({"date":df["date"].iloc[i],"signal":"BUY","price":df["close"].iloc[i]}); pos=1
            elif r>ob and pos==1: signals.append({"date":df["date"].iloc[i],"signal":"SELL","price":df["close"].iloc[i]}); pos=0
    elif name == "布林带":
        df = add_boll(df, params.get("w",20), params.get("k",2)); df = df.dropna()
        for i in range(1,len(df)):
            if df["close"].iloc[i]<=df["BOLL_DOWN"].iloc[i] and pos==0: signals.append({"date":df["date"].iloc[i],"signal":"BUY","price":df["close"].iloc[i]}); pos=1
            elif df["close"].iloc[i]>=df["BOLL_UP"].iloc[i] and pos==1: signals.append({"date":df["date"].iloc[i],"signal":"SELL","price":df["close"].iloc[i]}); pos=0
    elif name == "MACD":
        df = add_macd(df, params.get("f",12), params.get("s",26), params.get("sig",9)); df = df.dropna()
        for i in range(1,len(df)):
            if df["DIF"].iloc[i]>df["DEA"].iloc[i] and df["DIF"].iloc[i-1]<=df["DEA"].iloc[i-1]:
                if pos==0: signals.append({"date":df["date"].iloc[i],"signal":"BUY","price":df["close"].iloc[i]}); pos=1
            elif df["DIF"].iloc[i]<df["DEA"].iloc[i] and df["DIF"].iloc[i-1]>=df["DEA"].iloc[i-1]:
                if pos==1: signals.append({"date":df["date"].iloc[i],"signal":"SELL","price":df["close"].iloc[i]}); pos=0
    return pd.DataFrame(signals) if signals else pd.DataFrame(columns=["date","signal","price"])


def calc_result(signals, capital=100000, fee_rate=0.0003):
    if signals.empty or len(signals)<2:
        return None
    cash = capital; shares = 0; trades = []; peak = capital; mdd = 0
    for _, row in signals.iterrows():
        if row["signal"]=="BUY":
            sh = int(cash/(row["price"]*(1+fee_rate))/100)*100
            if sh>0:
                cost = sh*row["price"]*(1+fee_rate)
                cash -= cost
                trades.append({"type":"买入","date":row["date"],"price":row["price"],"shares":sh,"amount":cost,"cash":cash})
                shares = sh
        elif row["signal"]=="SELL" and shares>0:
            rev = shares*row["price"]*(1-fee_rate)
            cash += rev
            trades.append({"type":"卖出","date":row["date"],"price":row["price"],"shares":shares,"amount":rev,"cash":cash})
            shares = 0
        total = cash + shares*row["price"]
        if total>peak: peak=total
        mdd = max(mdd, (peak-total)/peak*100)
    last = signals.iloc[-1]["price"]
    fv = cash + shares*last
    ret = (fv-capital)/capital*100
    sell_t = [t for t in trades if t["type"]=="卖出"]
    buy_t  = [t for t in trades if t["type"]=="买入"]
    wins = sum(1 for i in range(min(len(sell_t),len(buy_t))) if sell_t[i]["amount"]>buy_t[i]["amount"])
    n_tr = min(len(sell_t),len(buy_t))
    return {"initial":capital,"final":fv,"return":ret,"mdd":mdd,
            "n_trades":n_tr,"win_rate":wins/n_tr*100 if n_tr>0 else 0,
            "trades":pd.DataFrame(trades)}


# ═══════════════════════════════════════════
# 图表
# ═══════════════════════════════════════════

def fig_kline(df, title="K线图", show_ma=True, show_boll=False):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                         vertical_spacing=0.03, row_heights=[0.75,0.25])
    fig.add_trace(go.Candlestick(x=df["date"],open=df["open"],high=df["high"],
        low=df["low"],close=df["close"],name="K线",
        increasing_line_color="#e53935",increasing_fillcolor="#e53935",
        decreasing_line_color="#43a047",decreasing_fillcolor="#43a047"), row=1,col=1)
    ma_colors = {"MA5":"#FF6B35","MA10":"#FFD700","MA20":"#00BFFF","MA60":"#FF69B4"}
    if show_ma:
        for m,c in ma_colors.items():
            if m in df.columns:
                fig.add_trace(go.Scatter(x=df["date"],y=df[m],mode="lines",name=m,
                    line=dict(color=c,width=1.2)),row=1,col=1)
    if show_boll and "BOLL_UP" in df.columns:
        for col,nm in [("BOLL_UP","上轨"),("BOLL_MID","中轨"),("BOLL_DOWN","下轨")]:
            fig.add_trace(go.Scatter(x=df["date"],y=df[col],mode="lines",name=f"布林{nm}",
                line=dict(color="rgba(156,39,176,0.6)",width=1,dash="dash")),row=1,col=1)
    if "volume" in df.columns:
        colors = ["#e53935" if c>=o else "#43a047" for c,o in zip(df["close"],df["open"])]
        fig.add_trace(go.Bar(x=df["date"],y=df["volume"],name="成交量",
            marker_color=colors,opacity=0.6),row=2,col=1)
    fig.update_layout(title=title,template="plotly_white",height=650,
        xaxis_rangeslider_visible=False,hovermode="x unified",
        legend=dict(orientation="h",y=1.02,x=1,xanchor="right"),
        margin=dict(l=60,r=30,t=55,b=40))
    fig.update_yaxes(title_text="价格(元)",row=1,col=1,side="right")
    fig.update_yaxes(title_text="成交量",row=2,col=1,side="right")
    return fig


# ═══════════════════════════════════════════
# 侧边栏导航
# ═══════════════════════════════════════════

NAV_ITEMS = [
    ("行情数据",    "📊", "nav-market"),
    ("策略编辑器",  "✏️", "nav-strategy"),
    ("历史回测",    "🧪", "nav-backtest"),
    ("模拟交易",    "🎮", "nav-paper"),
    ("实盘终端",    "💹", "nav-live"),
    ("绩效分析",    "📈", "nav-report"),
    ("风险管理",    "🛡️", "nav-risk"),
]





# ═══════════════════════════════════════════
# 模块1：行情数据
# ═══════════════════════════════════════════

def page_market():
    st.markdown("""<div class='qm-banner'>
        <span style='font-size:2rem;'>📊</span>
        <div><h1>行情数据</h1><p>实时行情 · K线分析 · 涨跌排行</p></div>
    </div>""", unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["📈 大盘概览", "🏆 涨跌排行", "🔍 个股K线"])

    with tab1:
        with st.spinner("获取行情中…"):
            df = get_stock_list()
        up = (df["涨跌幅"]>0).sum(); dn = (df["涨跌幅"]<0).sum()
        avg = df["涨跌幅"].mean()
        c1,c2,c3,c4 = st.columns(4)
        def mcard(col, val, lbl, color="#1565c0"):
            col.markdown(f"""<div class='metric-card' style='border-color:{color}'>
                <div class='val' style='color:{color}'>{val}</div><div class='lbl'>{lbl}</div></div>""",
                unsafe_allow_html=True)
        mcard(c1, len(df), "全市场股票数")
        mcard(c2, up, "上涨家数", "#e53935")
        mcard(c3, dn, "下跌家数", "#43a047")
        mcard(c4, f"{avg:+.2f}%", "平均涨幅", "#e53935" if avg>=0 else "#43a047")

        st.markdown("---")
        bins = [-11,-7,-5,-3,-1,0,1,3,5,7,11]
        hdata = pd.cut(df["涨跌幅"], bins=bins).value_counts().sort_index()
        fig_h = go.Figure(go.Bar(
            x=[str(x) for x in hdata.index], y=hdata.values,
            marker_color=["#43a047" if i < len(hdata)//2 else "#e53935" for i in range(len(hdata))]
        ))
        fig_h.update_layout(title="涨跌幅分布图", template="plotly_white", height=320,
                             xaxis_title="涨跌幅区间(%)", yaxis_title="股票数", margin=dict(l=50,r=20,t=45,b=60))
        st.plotly_chart(fig_h, use_container_width=True)

    with tab2:
        with st.spinner("加载排行…"):
            df2 = get_stock_list()
        col_t, col_b = st.columns(2)
        def render_rank(col, title, data):
            col.subheader(title)
            d = data[["代码","名称","最新价","涨跌幅","成交额"]].copy()
            d["涨跌幅"] = d["涨跌幅"].apply(lambda x: f"{x:+.2f}%")
            d["最新价"] = d["最新价"].apply(lambda x: f"{x:.2f}")
            d["成交额"] = d["成交额"].apply(lambda x: f"{x/1e8:.1f}亿" if pd.notna(x) else "-")
            col.dataframe(d.head(20), use_container_width=True, hide_index=True)
        render_rank(col_t, "🔴 涨幅TOP20", df2.head(20))
        render_rank(col_b, "🟢 跌幅TOP20", df2.tail(20).iloc[::-1])

    with tab3:
        cc1, cc2, cc3 = st.columns([2,2,1])
        code = cc1.text_input("股票代码", value="000001")
        period = cc2.selectbox("周期", ["daily","weekly","monthly"],
                               format_func=lambda x: {"daily":"日K","weekly":"周K","monthly":"月K"}[x])
        cc3.markdown("<br>",unsafe_allow_html=True)
        load = cc3.button("加载", type="primary", use_container_width=True)

        if code:
            end_d = datetime.now().strftime("%Y%m%d")
            start_d = (datetime.now()-timedelta(days=365)).strftime("%Y%m%d")
            with st.spinner("加载K线…"):
                kdf = get_kline(code, period, start_d, end_d)
            if not kdf.empty:
                kdf = add_ma(kdf); kdf = add_boll(kdf)
                sm, sb = st.columns(2)
                show_ma   = sm.checkbox("显示均线", value=True)
                show_boll = sb.checkbox("显示布林带", value=False)
                st.plotly_chart(fig_kline(kdf, f"{code} K线图", show_ma, show_boll), use_container_width=True)

                ind_tabs = st.tabs(["RSI", "MACD", "KDJ"])
                with ind_tabs[0]:
                    kdf = add_rsi(kdf)
                    if "RSI" in kdf.columns:
                        fig_r = go.Figure()
                        fig_r.add_trace(go.Scatter(x=kdf["date"],y=kdf["RSI"],mode="lines",name="RSI",line=dict(color="#1976d2",width=2)))
                        fig_r.add_hline(y=70,line_dash="dash",line_color="#e53935",annotation_text="超买70")
                        fig_r.add_hline(y=30,line_dash="dash",line_color="#43a047",annotation_text="超卖30")
                        fig_r.update_layout(template="plotly_white",height=300,margin=dict(l=50,r=20,t=40,b=30))
                        st.plotly_chart(fig_r, use_container_width=True)
                with ind_tabs[1]:
                    kdf = add_macd(kdf)
                    if "DIF" in kdf.columns:
                        fig_m = make_subplots(rows=2,cols=1,shared_xaxes=True,vertical_spacing=0.06)
                        fig_m.add_trace(go.Scatter(x=kdf["date"],y=kdf["DIF"],mode="lines",name="DIF",line=dict(color="#e53935",width=1.5)),row=1,col=1)
                        fig_m.add_trace(go.Scatter(x=kdf["date"],y=kdf["DEA"],mode="lines",name="DEA",line=dict(color="#1976d2",width=1.5)),row=1,col=1)
                        mc = ["#e53935" if v>=0 else "#43a047" for v in kdf["MACD_HIST"]]
                        fig_m.add_trace(go.Bar(x=kdf["date"],y=kdf["MACD_HIST"],name="柱",marker_color=mc),row=2,col=1)
                        fig_m.update_layout(template="plotly_white",height=380,margin=dict(l=50,r=20,t=35,b=30))
                        st.plotly_chart(fig_m, use_container_width=True)
                with ind_tabs[2]:
                    kdf = add_kdj(kdf)
                    if "K" in kdf.columns:
                        fig_k = go.Figure()
                        for col_n, color in [("K","#e53935"),("D","#1976d2"),("J","#FF6B35")]:
                            fig_k.add_trace(go.Scatter(x=kdf["date"],y=kdf[col_n],mode="lines",name=col_n,line=dict(color=color,width=1.5)))
                        fig_k.add_hline(y=80,line_dash="dash",line_color="#e53935",annotation_text="超买80")
                        fig_k.add_hline(y=20,line_dash="dash",line_color="#43a047",annotation_text="超卖20")
                        fig_k.update_layout(template="plotly_white",height=300,margin=dict(l=50,r=20,t=40,b=30))
                        st.plotly_chart(fig_k, use_container_width=True)


# ═══════════════════════════════════════════
# 模块2：策略编辑器
# ═══════════════════════════════════════════

def page_strategy_editor():
    st.markdown("""<div class='qm-banner'>
        <span style='font-size:2rem;'>✏️</span>
        <div><h1>策略编辑器</h1><p>在线编写Python量化策略 · 语法检查 · 一键提交回测</p></div>
    </div>""", unsafe_allow_html=True)

    col_l, col_r = st.columns([3, 2])

    with col_l:
        st.subheader("📝 策略代码")
        code_text = st.text_area(
            "Python 策略代码",
            value=st.session_state["strategy_code"],
            height=480,
            label_visibility="collapsed",
            key="editor_code"
        )

        ca, cb, cc = st.columns(3)
        if ca.button("✅ 语法检查", use_container_width=True):
            try:
                compile(code_text, "<string>", "exec")
                st.success("✅ 语法正确，可以提交回测")
            except SyntaxError as e:
                st.error(f"❌ 语法错误 第{e.lineno}行：{e.msg}")
        if cb.button("💾 保存策略", use_container_width=True):
            st.session_state["strategy_code"] = code_text
            st.success("策略已保存到会话")
        if cc.button("🔄 重置示例", use_container_width=True):
            st.session_state["strategy_code"] = """import pandas as pd

def strategy(df):
    df = df.copy()
    df['MA5']  = df['close'].rolling(5).mean()
    df['MA20'] = df['close'].rolling(20).mean()
    df = df.dropna()
    signals, pos = [], 0
    for i in range(1, len(df)):
        if df['MA5'].iloc[i]>df['MA20'].iloc[i] and df['MA5'].iloc[i-1]<=df['MA20'].iloc[i-1]:
            if pos==0: signals.append({'date':df['date'].iloc[i],'signal':'BUY','price':df['close'].iloc[i]}); pos=1
        elif df['MA5'].iloc[i]<df['MA20'].iloc[i] and df['MA5'].iloc[i-1]>=df['MA20'].iloc[i-1]:
            if pos==1: signals.append({'date':df['date'].iloc[i],'signal':'SELL','price':df['close'].iloc[i]}); pos=0
    return pd.DataFrame(signals) if signals else pd.DataFrame(columns=['date','signal','price'])
"""
            st.rerun()

    with col_r:
        st.subheader("🎯 策略模板库")
        templates = {
            "双均线金叉": "MA5/MA20 金叉买入，死叉卖出",
            "RSI均值回归": "RSI<30 超卖买入，>70 超买卖出",
            "布林带突破": "价格跌破下轨买入，升破上轨卖出",
            "MACD动量": "DIF金叉DEA买入，死叉卖出",
            "趋势跟踪": "20日高点突破买入，跌破10日低点卖出",
        }
        for name, desc in templates.items():
            with st.expander(f"📌 {name}"):
                st.caption(desc)
                if st.button(f"加载 {name}", key=f"tpl_{name}", use_container_width=True):
                    st.info(f"已选择「{name}」模板，请在左侧编辑后保存")

        st.markdown("---")
        st.subheader("📚 API 参考")
        st.markdown("""
| 变量/函数 | 说明 |
|---|---|
| `df['close']` | 收盘价 Series |
| `df['open/high/low']` | 开盘/最高/最低 |
| `df['volume']` | 成交量 |
| `df['date']` | 日期 |
| 返回 `signal='BUY'` | 买入信号 |
| 返回 `signal='SELL'` | 卖出信号 |
        """)

    st.markdown("---")
    st.info("💡 保存策略后，前往「历史回测」页面选择「自定义策略」进行回测验证")


# ═══════════════════════════════════════════
# 模块3：历史回测平台
# ═══════════════════════════════════════════

def page_backtest():
    st.markdown("""<div class='qm-banner'>
        <span style='font-size:2rem;'>🧪</span>
        <div><h1>历史回测平台</h1><p>多策略对比 · 参数优化 · 绩效评估</p></div>
    </div>""", unsafe_allow_html=True)

    with st.expander("⚙️ 回测参数", expanded=True):
        c1,c2,c3,c4 = st.columns(4)
        code     = c1.text_input("股票代码", value="000001", key="bt_code")
        s_date   = c2.date_input("开始日期", value=datetime(2023,1,1))
        e_date   = c3.date_input("结束日期", value=datetime.now())
        capital  = c4.number_input("初始资金(元)", value=100000, step=10000, min_value=10000)
        fee      = c4.number_input("手续费率(‰)", value=0.3, step=0.1, min_value=0.0) / 1000

    st.markdown("---")
    c1,c2,c3,c4 = st.columns(4)
    with c1:
        st.markdown("**均线交叉**")
        ma_f = st.number_input("快线", 2, 60, 5,  key="bt_maf")
        ma_s = st.number_input("慢线", 5,250,20,  key="bt_mas")
    with c2:
        st.markdown("**RSI**")
        rsi_n  = st.number_input("周期", 5,50,14,  key="bt_rsin")
        rsi_ob = st.number_input("超买", 60,90,70, key="bt_rsiob")
        rsi_os = st.number_input("超卖", 10,40,30, key="bt_rsios")
    with c3:
        st.markdown("**布林带**")
        bw  = st.number_input("窗口",  5,60,20, key="bt_bw")
        bk  = st.number_input("倍数", 0.5,4.0,2.0,step=0.5, key="bt_bk")
    with c4:
        st.markdown("**MACD**")
        mf  = st.number_input("快线",  5,30,12, key="bt_mf")
        ms  = st.number_input("慢线", 10,60,26, key="bt_ms")
        msig= st.number_input("信号线",3,20, 9, key="bt_msig")

    run = st.button("🚀 开始回测", type="primary", use_container_width=True)

    if run:
        with st.spinner("回测中…"):
            kdf = get_kline(code,"daily",s_date.strftime("%Y%m%d"),e_date.strftime("%Y%m%d"))
        if kdf.empty:
            st.error("K线数据获取失败")
            return

        strats = {
            "均线交叉": run_strategy_signals(kdf,"均线交叉",fast=ma_f,slow=ma_s),
            "RSI":      run_strategy_signals(kdf,"RSI",n=rsi_n,ob=rsi_ob,os=rsi_os),
            "布林带":   run_strategy_signals(kdf,"布林带",w=bw,k=bk),
            "MACD":     run_strategy_signals(kdf,"MACD",f=mf,s=ms,sig=msig),
        }

        # 自定义策略
        try:
            ns = {}
            exec(st.session_state["strategy_code"], ns)
            if "strategy" in ns:
                custom_sig = ns["strategy"](kdf.copy())
                strats["自定义策略"] = custom_sig
        except Exception as e:
            st.warning(f"自定义策略执行出错：{e}")

        results = {n: calc_result(sig, capital, fee) for n,sig in strats.items()}

        st.markdown("---")
        st.subheader("📊 回测结果对比")
        rows = []
        for n,r in results.items():
            if r:
                rows.append({"策略":n,
                             "总收益率": f"{r['return']:+.2f}%",
                             "最大回撤": f"{r['mdd']:.2f}%",
                             "交易次数": r["n_trades"],
                             "胜率": f"{r['win_rate']:.1f}%",
                             "最终资金": f"¥{r['final']:,.0f}"})
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

            # 资金曲线
            fig_eq = go.Figure()
            for n,r in results.items():
                if r and not r["trades"].empty:
                    t = r["trades"]
                    fig_eq.add_trace(go.Scatter(x=list(range(len(t)+1)),
                        y=[capital]+list(t["cash"]), mode="lines", name=n, line=dict(width=2)))
            fig_eq.update_layout(title="策略资金曲线对比", template="plotly_white", height=420,
                xaxis_title="交易次数", yaxis_title="资金(元)",
                legend=dict(orientation="h",y=1.02), margin=dict(l=60,r=30,t=50,b=40))
            st.plotly_chart(fig_eq, use_container_width=True)

            # 最优策略详细
            best_n = max((n for n,r in results.items() if r), key=lambda n: results[n]["return"])
            best_r = results[best_n]
            st.subheader(f"🏆 最优：{best_n}  收益 {best_r['return']:+.2f}%  最大回撤 {best_r['mdd']:.2f}%")
            t_show = best_r["trades"].copy()
            if "date" in t_show.columns:
                t_show["date"] = t_show["date"].astype(str)
            for col in ["amount","cash"]:
                if col in t_show.columns:
                    t_show[col] = t_show[col].apply(lambda x: f"¥{x:,.0f}")
            st.dataframe(t_show, use_container_width=True, hide_index=True)
        else:
            st.warning("所有策略均未产生交易信号，请扩大时间范围或调整参数")


# ═══════════════════════════════════════════
# 模块4：模拟交易
# ═══════════════════════════════════════════

def page_sim_trade():
    st.markdown("""<div class='qm-banner'>
        <span style='font-size:2rem;'>🎮</span>
        <div><h1>模拟交易</h1><p>虚拟资金 · 真实行情 · 练习交易</p></div>
    </div>""", unsafe_allow_html=True)

    # 账户概览
    cap = st.session_state["sim_capital"]
    pos = st.session_state["sim_positions"]

    # 计算持仓市值
    mkt_val = 0
    for code, info in pos.items():
        mkt_val += info["shares"] * info.get("cur_price", info["cost"])

    total_asset = cap + mkt_val
    init = 1_000_000.0
    pnl = total_asset - init
    pnl_pct = pnl / init * 100

    c1,c2,c3,c4 = st.columns(4)
    def mcard2(col, lbl, val, color="#1565c0"):
        col.markdown(f"""<div class='metric-card' style='border-color:{color}'>
            <div class='val' style='color:{color}'>{val}</div><div class='lbl'>{lbl}</div></div>""",
            unsafe_allow_html=True)
    mcard2(c1,"总资产", f"¥{total_asset:,.0f}")
    mcard2(c2,"可用资金", f"¥{cap:,.0f}")
    mcard2(c3,"持仓市值", f"¥{mkt_val:,.0f}")
    mcard2(c4,"累计盈亏", f"{'+'if pnl>=0 else ''}{pnl_pct:.2f}%", "#e53935" if pnl>=0 else "#43a047")

    st.markdown("---")
    tab_order, tab_pos, tab_hist = st.tabs(["📝 下单", "📦 持仓", "📋 历史记录"])

    with tab_order:
        oc1, oc2 = st.columns(2)
        with oc1:
            st.subheader("委托下单")
            t_code   = st.text_input("股票代码", value="000001", key="sim_code")
            t_dir    = st.radio("方向", ["买入", "卖出"], horizontal=True, key="sim_dir")
            t_price  = st.number_input("委托价格(元)", value=10.0, min_value=0.01, step=0.01, key="sim_price")
            t_shares = st.number_input("委托数量(股)", value=100, min_value=100, step=100, key="sim_shares")

            est_amt  = t_price * t_shares
            st.caption(f"预计{t_dir}金额：¥{est_amt:,.2f}（含万三手续费）")

            if st.button("✅ 确认委托", type="primary", use_container_width=True):
                fee = est_amt * 0.0003
                if t_dir == "买入":
                    total_need = est_amt + fee
                    if total_need > cap:
                        st.error(f"资金不足！需要 ¥{total_need:,.2f}，可用 ¥{cap:,.2f}")
                    else:
                        st.session_state["sim_capital"] -= total_need
                        if t_code in pos:
                            old = pos[t_code]
                            old_cost = old["shares"] * old["cost"]
                            new_cost = t_shares * t_price
                            total_shares = old["shares"] + t_shares
                            pos[t_code] = {"shares": total_shares, "cost": (old_cost+new_cost)/total_shares,
                                           "name": t_code, "cur_price": t_price}
                        else:
                            pos[t_code] = {"shares": t_shares, "cost": t_price, "name": t_code, "cur_price": t_price}
                        st.session_state["sim_trades"].append({
                            "时间": datetime.now().strftime("%H:%M:%S"),
                            "代码": t_code, "方向": "买入", "价格": t_price,
                            "数量": t_shares, "金额": f"¥{est_amt:,.0f}", "手续费": f"¥{fee:.2f}"
                        })
                        st.success(f"✅ 买入成功：{t_code}  {t_shares}股 @ ¥{t_price}")
                        st.rerun()
                else:
                    if t_code not in pos or pos[t_code]["shares"] < t_shares:
                        st.error("持仓不足")
                    else:
                        rev = est_amt - fee
                        st.session_state["sim_capital"] += rev
                        pos[t_code]["shares"] -= t_shares
                        if pos[t_code]["shares"] == 0:
                            del pos[t_code]
                        st.session_state["sim_trades"].append({
                            "时间": datetime.now().strftime("%H:%M:%S"),
                            "代码": t_code, "方向": "卖出", "价格": t_price,
                            "数量": t_shares, "金额": f"¥{rev:,.0f}", "手续费": f"¥{fee:.2f}"
                        })
                        st.success(f"✅ 卖出成功：{t_code}  {t_shares}股 @ ¥{t_price}")
                        st.rerun()

        with oc2:
            st.subheader("快速报价")
            if t_code:
                with st.spinner("获取报价…"):
                    df_q = get_stock_list()
                row_q = df_q[df_q["代码"]==t_code]
                if not row_q.empty:
                    r = row_q.iloc[0]
                    pct_cls = "up" if r["涨跌幅"]>=0 else "down"
                    st.markdown(f"""
                    <div class='metric-card'>
                        <b>{r['名称']} ({t_code})</b><br/>
                        <span class='{pct_cls}' style='font-size:1.8rem'>{r['最新价']:.2f}</span>
                        <span class='{pct_cls}' style='font-size:1rem'> {r['涨跌幅']:+.2f}%</span><br/>
                        <span style='color:#888;font-size:0.82rem'>
                        最高:{r['最高']:.2f}  最低:{r['最低']:.2f}  
                        换手:{r.get('换手率','-')}%
                        </span>
                    </div>""", unsafe_allow_html=True)
                else:
                    st.info("未查询到该股票行情")

    with tab_pos:
        if pos:
            rows = []
            for code, info in pos.items():
                cost  = info["cost"]
                cur   = info.get("cur_price", cost)
                pnl_s = (cur - cost) * info["shares"]
                pnl_pct_s = (cur - cost) / cost * 100
                rows.append({"代码":code,"持仓(股)":info["shares"],
                              "成本价":f"{cost:.2f}","现价":f"{cur:.2f}",
                              "持仓盈亏":f"{'+'if pnl_s>=0 else ''}{pnl_s:,.0f}",
                              "盈亏%":f"{'+'if pnl_pct_s>=0 else ''}{pnl_pct_s:.2f}%",
                              "市值":f"¥{cur*info['shares']:,.0f}"})
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info("暂无持仓")

        if st.button("🔄 重置账户", type="secondary"):
            st.session_state["sim_capital"]   = 1_000_000.0
            st.session_state["sim_positions"] = {}
            st.session_state["sim_trades"]    = []
            st.success("账户已重置为100万初始资金")
            st.rerun()

    with tab_hist:
        trades = st.session_state["sim_trades"]
        if trades:
            st.dataframe(pd.DataFrame(trades[::-1]), use_container_width=True, hide_index=True)
        else:
            st.info("暂无交易记录")


# ═══════════════════════════════════════════
# 模块5：实盘交易终端（演示）
# ═══════════════════════════════════════════

def page_live_terminal():
    st.markdown("""<div class='qm-banner'>
        <span style='font-size:2rem;'>💹</span>
        <div><h1>实盘交易终端</h1><p>委托下单 · 撤单 · 成交记录（演示模式）</p></div>
    </div>""", unsafe_allow_html=True)

    st.warning("⚠️ **当前为演示模式**，实盘对接需配置券商交易接口（easytrader / miniQMT）。所有操作均不产生真实交易。")

    tab1, tab2, tab3, tab4 = st.tabs(["📝 委托下单", "📋 当日委托", "💰 成交记录", "📊 资金账户"])

    with tab1:
        lc1, lc2 = st.columns(2)
        with lc1:
            st.subheader("股票委托")
            lcode   = st.text_input("证券代码", value="000001", key="live_code")
            lname   = st.text_input("证券名称", value="平安银行", key="live_name", disabled=True)
            ldir    = st.radio("买卖方向", ["买入","卖出"], horizontal=True, key="live_dir")
            ltype   = st.selectbox("委托类型", ["限价委托","市价委托","止损限价","条件单"], key="live_type")
            lprice  = st.number_input("委托价格", value=10.0, step=0.01, key="live_price")
            lshares = st.number_input("委托数量", value=100, step=100, key="live_shares")

            if ltype == "条件单":
                st.selectbox("触发条件", ["价格>=","价格<=","涨幅>=","跌幅>="], key="live_cond")
                st.number_input("触发值", value=10.0, step=0.01, key="live_trig")

            st.caption(f"预计金额：¥{lprice*lshares:,.2f}")

            if st.button("⚡ 提交委托（演示）", type="primary", use_container_width=True):
                order = {
                    "委托时间": datetime.now().strftime("%H:%M:%S"),
                    "代码": lcode, "名称": lname,
                    "方向": ldir, "类型": ltype,
                    "委托价": f"{lprice:.2f}", "数量": lshares,
                    "状态": "已报", "委托号": f"DEMO{random.randint(10000,99999)}"
                }
                st.session_state["live_orders"].append(order)
                st.success(f"委托已提交（演示）：{ldir} {lcode} {lshares}股 @ {lprice:.2f}")

        with lc2:
            st.subheader("盘口信息（演示）")
            prices = [round(10.0 + i*0.01, 2) for i in range(-5, 6)]
            vols   = [random.randint(100, 50000) for _ in range(11)]
            fig_ob = go.Figure()
            fig_ob.add_trace(go.Bar(x=vols[6:],y=[f"{p:.2f}" for p in prices[6:]],
                orientation="h",marker_color="#e53935",name="卖盘"))
            fig_ob.add_trace(go.Bar(x=[-v for v in vols[:5]],y=[f"{p:.2f}" for p in prices[:5]],
                orientation="h",marker_color="#43a047",name="买盘"))
            fig_ob.update_layout(template="plotly_white",height=300,
                title="买卖盘口（演示数据）",
                xaxis=dict(title="量",tickformat=".0f"),
                margin=dict(l=60,r=20,t=45,b=30),barmode="overlay")
            st.plotly_chart(fig_ob, use_container_width=True)

    with tab2:
        orders = st.session_state["live_orders"]
        if orders:
            df_ord = pd.DataFrame(orders[::-1])
            st.dataframe(df_ord, use_container_width=True, hide_index=True)
            if st.button("撤销全部演示委托"):
                st.session_state["live_orders"] = []
                st.rerun()
        else:
            st.info("暂无当日委托")

    with tab3:
        st.info("成交记录将在委托撮合后显示（演示模式下无真实成交）")
        # 演示成交记录
        demo_deals = [
            {"成交时间":"09:32:15","代码":"000001","名称":"平安银行","方向":"买入","成交价":"10.25","数量":1000,"金额":"¥10,250"},
            {"成交时间":"10:15:43","代码":"600519","名称":"贵州茅台","方向":"卖出","成交价":"1680.00","数量":10,"金额":"¥16,800"},
        ]
        st.dataframe(pd.DataFrame(demo_deals), use_container_width=True, hide_index=True)

    with tab4:
        st.subheader("资金账户（演示）")
        acct_info = {
            "账户": ["演示账户001"],
            "可用资金": ["¥ 286,450.00"],
            "持仓市值": ["¥ 342,800.00"],
            "总资产":   ["¥ 629,250.00"],
            "今日盈亏": ["+¥ 12,380.00"],
            "总收益率": ["+2.01%"]
        }
        st.dataframe(pd.DataFrame(acct_info), use_container_width=True, hide_index=True)

        st.info("💡 接入实盘需配置：easytrader（同花顺/通达信/雪球）或 miniQMT（迅投QMT）")
        st.code("""# easytrader 接入示例
import easytrader
user = easytrader.use('ths')  # 同花顺
user.connect(r'C:/同花顺/xiadan.exe')
user.buy('000001', price=10.20, amount=1000)
""", language="python")


# ═══════════════════════════════════════════
# 模块6：绩效分析报告
# ═══════════════════════════════════════════

def page_performance():
    st.markdown("""<div class='qm-banner'>
        <span style='font-size:2rem;'>📈</span>
        <div><h1>绩效分析报告</h1><p>收益分析 · 夏普比率 · 最大回撤 · 年化报告</p></div>
    </div>""", unsafe_allow_html=True)

    st.subheader("📂 加载回测数据")
    code = st.text_input("股票代码", value="000001", key="perf_code")
    c1,c2 = st.columns(2)
    s_d = c1.date_input("开始日期", value=datetime(2023,1,1), key="perf_start")
    e_d = c2.date_input("结束日期", value=datetime.now(), key="perf_end")
    sel_strategy = st.selectbox("选择策略", ["均线交叉","RSI","布林带","MACD"])

    if st.button("📊 生成绩效报告", type="primary", use_container_width=True):
        with st.spinner("分析中…"):
            kdf = get_kline(code,"daily",s_d.strftime("%Y%m%d"),e_d.strftime("%Y%m%d"))

        if kdf.empty:
            st.error("数据获取失败")
            return

        sig = run_strategy_signals(kdf, sel_strategy,
                                   fast=5,slow=20,n=14,ob=70,os=30,w=20,k=2,f=12,s=26,sig=9)
        res = calc_result(sig, 100000)

        if not res:
            st.warning("无足够交易信号生成报告")
            return

        # 核心指标
        st.markdown("---")
        st.subheader("🎯 核心绩效指标")
        m1,m2,m3,m4,m5,m6 = st.columns(6)
        def pm(col, lbl, val, color="#1565c0"):
            col.markdown(f"""<div class='metric-card' style='border-color:{color};padding:0.8rem'>
                <div class='val' style='color:{color};font-size:1.3rem'>{val}</div>
                <div class='lbl'>{lbl}</div></div>""", unsafe_allow_html=True)

        ret = res["return"]
        pm(m1,"总收益率",f"{ret:+.2f}%","#e53935" if ret>=0 else "#43a047")
        pm(m2,"最大回撤",f"{res['mdd']:.2f}%","#e53935")
        pm(m3,"交易次数",str(res["n_trades"]))
        pm(m4,"胜率",f"{res['win_rate']:.1f}%","#1565c0")
        pm(m5,"最终资金",f"¥{res['final']:,.0f}")
        days = (e_d-s_d).days
        ann_ret = ((1+ret/100)**(365/max(days,1))-1)*100 if days>0 else 0
        pm(m6,"年化收益",f"{ann_ret:+.2f}%","#e53935" if ann_ret>=0 else "#43a047")

        if not res["trades"].empty:
            st.markdown("---")
            trades = res["trades"]

            # 资金曲线
            st.subheader("📈 资金曲线")
            equity = [100000] + list(trades["cash"])
            fig_e = go.Figure()
            fig_e.add_trace(go.Scatter(y=equity, mode="lines", name="资金",
                line=dict(color="#1976d2",width=2), fill="tozeroy",
                fillcolor="rgba(25,118,210,0.08)"))
            fig_e.update_layout(template="plotly_white",height=350,
                xaxis_title="交易次数",yaxis_title="资金(元)",
                margin=dict(l=60,r=30,t=40,b=40))
            st.plotly_chart(fig_e, use_container_width=True)

            # 每笔盈亏
            if "amount" in trades.columns:
                buys  = trades[trades["type"]=="买入"]["amount"].reset_index(drop=True)
                sells = trades[trades["type"]=="卖出"]["amount"].reset_index(drop=True)
                n_tr  = min(len(buys),len(sells))
                if n_tr > 0:
                    pnls = [(sells.iloc[i]-buys.iloc[i]) for i in range(n_tr)]
                    colors_pnl = ["#e53935" if p>=0 else "#43a047" for p in pnls]
                    fig_pnl = go.Figure(go.Bar(
                        x=list(range(1,n_tr+1)), y=pnls, marker_color=colors_pnl, name="盈亏"))
                    fig_pnl.update_layout(title="每笔交易盈亏",template="plotly_white",
                        height=300,xaxis_title="交易编号",yaxis_title="盈亏(元)",
                        margin=dict(l=60,r=30,t=45,b=40))
                    st.plotly_chart(fig_pnl, use_container_width=True)

            # 月度收益
            st.subheader("📅 月度收益分布")
            if "date" in trades.columns:
                trades_c = trades.copy()
                trades_c["month"] = pd.to_datetime(trades_c["date"]).dt.to_period("M").astype(str)
                sells_m = trades_c[trades_c["type"]=="卖出"].groupby("month")["amount"].sum()
                buys_m  = trades_c[trades_c["type"]=="买入"].groupby("month")["amount"].sum()
                monthly = (sells_m - buys_m).dropna()
                if not monthly.empty:
                    fig_m = go.Figure(go.Bar(
                        x=monthly.index.tolist(), y=monthly.values,
                        marker_color=["#e53935" if v>=0 else "#43a047" for v in monthly.values]
                    ))
                    fig_m.update_layout(template="plotly_white",height=300,
                        xaxis_title="月份",yaxis_title="盈亏(元)",
                        margin=dict(l=60,r=30,t=35,b=40))
                    st.plotly_chart(fig_m, use_container_width=True)

        # 导出报告
        st.markdown("---")
        report = f"""QuantMaster Pro 绩效分析报告
========================================
策略：{sel_strategy}
股票：{code}
时间：{s_d} ~ {e_d}
----------------------------------------
总收益率：{ret:+.2f}%
年化收益：{ann_ret:+.2f}%
最大回撤：{res['mdd']:.2f}%
交易次数：{res['n_trades']}
胜率：{res['win_rate']:.1f}%
最终资金：¥{res['final']:,.0f}
========================================
生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        st.download_button("📥 下载文字报告", report, file_name=f"绩效报告_{code}_{sel_strategy}.txt")


# ═══════════════════════════════════════════
# 模块7：风险管理系统
# ═══════════════════════════════════════════

def page_risk():
    st.markdown("""<div class='qm-banner'>
        <span style='font-size:2rem;'>🛡️</span>
        <div><h1>风险管理系统</h1><p>VaR评估 · 集中度分析 · 预警规则 · 风险报告</p></div>
    </div>""", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["📉 VaR风险评估", "📊 持仓集中度", "🔔 预警规则", "📋 风险报告"])

    with tab1:
        st.subheader("VaR (在险价值) 计算")
        vc1,vc2,vc3 = st.columns(3)
        risk_code    = vc1.text_input("股票代码", value="000001", key="var_code")
        confidence   = vc2.selectbox("置信度", [0.95, 0.99, 0.999],
                                     format_func=lambda x: f"{x*100:.1f}%", key="var_conf")
        holding_days = vc3.number_input("持有天数", value=1, min_value=1, max_value=30, key="var_days")
        position_val = vc3.number_input("持仓金额(元)", value=100000, step=10000, key="var_pos")

        if st.button("计算VaR", type="primary"):
            with st.spinner("获取历史数据…"):
                end_s   = datetime.now().strftime("%Y%m%d")
                start_s = (datetime.now()-timedelta(days=500)).strftime("%Y%m%d")
                kdf_r   = get_kline(risk_code,"daily",start_s,end_s)

            if not kdf_r.empty and "close" in kdf_r.columns:
                returns = kdf_r["close"].pct_change().dropna()
                std_d   = returns.std()
                # 历史VaR
                var_hist = float(np.percentile(returns, (1-confidence)*100))
                # 参数VaR（正态分布）
                from scipy.stats import norm
                z = norm.ppf(1 - confidence)
                var_para = returns.mean() + z * std_d

                var_amt_hist = abs(var_hist) * position_val * np.sqrt(holding_days)
                var_amt_para = abs(var_para) * position_val * np.sqrt(holding_days)

                rc1,rc2,rc3,rc4 = st.columns(4)
                rc1.metric("日均波动率", f"{std_d*100:.2f}%")
                rc2.metric("历史VaR", f"-{abs(var_hist)*100:.2f}%")
                rc3.metric("参数VaR", f"-{abs(var_para)*100:.2f}%")
                rc4.metric(f"{holding_days}日VaR金额", f"¥{var_amt_hist:,.0f}")

                # 收益率分布图
                fig_ret = go.Figure()
                fig_ret.add_trace(go.Histogram(x=returns*100, nbinsx=50,
                    marker_color="#1976d2", opacity=0.7, name="收益率分布"))
                fig_ret.add_vline(x=var_hist*100, line_dash="dash",
                    line_color="#e53935", annotation_text=f"VaR {var_hist*100:.2f}%")
                fig_ret.update_layout(title=f"{risk_code} 历史收益率分布",
                    template="plotly_white", height=350,
                    xaxis_title="日收益率(%)", yaxis_title="频次",
                    margin=dict(l=60,r=30,t=50,b=40))
                st.plotly_chart(fig_ret, use_container_width=True)

    with tab2:
        st.subheader("持仓集中度分析")
        st.info("输入您的持仓组合进行集中度评估")

        portfolio_input = st.text_area(
            "输入持仓（格式：代码,名称,金额  每行一个）",
            value="000001,平安银行,50000\n600519,贵州茅台,80000\n002594,比亚迪,60000\n300750,宁德时代,40000\n601318,中国平安,30000",
            height=150
        )

        if st.button("分析集中度"):
            try:
                rows = []
                for line in portfolio_input.strip().split("\n"):
                    parts = line.strip().split(",")
                    if len(parts) >= 3:
                        rows.append({"代码":parts[0].strip(),"名称":parts[1].strip(),
                                     "市值":float(parts[2].strip())})
                if rows:
                    df_port = pd.DataFrame(rows)
                    total = df_port["市值"].sum()
                    df_port["占比"] = df_port["市值"]/total*100
                    df_port["市值显示"] = df_port["市值"].apply(lambda x: f"¥{x:,.0f}")
                    df_port["占比显示"] = df_port["占比"].apply(lambda x: f"{x:.1f}%")

                    pc1, pc2 = st.columns(2)
                    with pc1:
                        fig_pie = go.Figure(go.Pie(
                            labels=df_port["名称"], values=df_port["市值"],
                            hole=0.4, textinfo="label+percent"
                        ))
                        fig_pie.update_layout(title="持仓分布", height=380,
                            margin=dict(l=20,r=20,t=50,b=20))
                        st.plotly_chart(fig_pie, use_container_width=True)
                    with pc2:
                        st.dataframe(df_port[["代码","名称","市值显示","占比显示"]].rename(
                            columns={"市值显示":"市值","占比显示":"占比"}),
                            use_container_width=True, hide_index=True)

                        # 集中度指标
                        hhi = (df_port["占比"]/100**2).sum() * 10000  # HHI指数
                        max_pos = df_port["占比"].max()
                        top3 = df_port.nlargest(3,"占比")["占比"].sum()
                        st.metric("HHI集中度指数", f"{hhi:.0f}", help="<1000低，1000-1800中，>1800高")
                        st.metric("最大单仓占比", f"{max_pos:.1f}%")
                        st.metric("TOP3占比", f"{top3:.1f}%")

                        if max_pos > 30:
                            st.warning(f"⚠️ 单仓占比 {max_pos:.1f}% 超过30%，集中度偏高")
                        if top3 > 70:
                            st.warning(f"⚠️ TOP3占比 {top3:.1f}% 超过70%，分散度不足")
            except Exception as e:
                st.error(f"解析失败：{e}")

    with tab3:
        st.subheader("预警规则设置")
        with st.expander("📉 价格预警", expanded=True):
            wc1,wc2,wc3 = st.columns(3)
            w_code    = wc1.text_input("监控股票", value="000001", key="warn_code")
            w_up_pct  = wc2.number_input("涨幅预警(%)", value=5.0, key="warn_up")
            w_dn_pct  = wc3.number_input("跌幅预警(%)", value=5.0, key="warn_dn")
            w_up_abs  = wc2.number_input("价格上限(元)", value=0.0, key="warn_uabs")
            w_dn_abs  = wc3.number_input("价格下限(元)", value=0.0, key="warn_dabs")

        with st.expander("📊 成交量预警"):
            vc_r = st.number_input("放量倍数", value=3.0, step=0.5, key="warn_vol")
            vc_t = st.number_input("换手率上限(%)", value=10.0, key="warn_turn")

        with st.expander("💰 资金预警"):
            rk_max_loss   = st.number_input("单日最大亏损(元)", value=5000, step=1000, key="warn_loss")
            rk_total_loss = st.number_input("总亏损上限(元)", value=20000, step=1000, key="warn_tloss")
            rk_pos_limit  = st.number_input("单股仓位上限(%)", value=30.0, key="warn_pos")

        if st.button("💾 保存预警规则", type="primary"):
            st.success("✅ 预警规则已保存！监控中…")

    with tab4:
        st.subheader("风险评估报告")
        rcode = st.text_input("分析股票", value="000001", key="risk_code2")
        if st.button("🛡️ 生成风险报告", type="primary", use_container_width=True):
            with st.spinner("计算风险指标…"):
                end_s   = datetime.now().strftime("%Y%m%d")
                start_s = (datetime.now()-timedelta(days=365)).strftime("%Y%m%d")
                kdf_r   = get_kline(rcode,"daily",start_s,end_s)

            if kdf_r.empty or "close" not in kdf_r.columns:
                st.error("数据获取失败")
                return

            rets = kdf_r["close"].pct_change().dropna()
            vol_ann = rets.std() * np.sqrt(252) * 100
            var95   = abs(np.percentile(rets, 5)) * 100
            var99   = abs(np.percentile(rets, 1)) * 100
            max_r   = rets.max() * 100
            min_r   = rets.min() * 100
            sk      = float(rets.skew())
            ku      = float(rets.kurtosis())

            # 计算最大回撤
            prices  = kdf_r["close"]
            roll_max = prices.cummax()
            dd      = (prices - roll_max) / roll_max * 100
            max_dd  = dd.min()
            days_dd = int(dd.idxmin() - dd.where(dd==0).last_valid_index()) if dd.where(dd==0).last_valid_index() else 0

            rr1,rr2,rr3 = st.columns(3)
            rr1.metric("年化波动率", f"{vol_ann:.2f}%")
            rr2.metric("95% VaR(日)", f"-{var95:.2f}%")
            rr3.metric("99% VaR(日)", f"-{var99:.2f}%")
            rr1.metric("历史最大回撤", f"{max_dd:.2f}%")
            rr2.metric("日最大涨幅", f"+{max_r:.2f}%")
            rr3.metric("日最大跌幅", f"{min_r:.2f}%")
            rr1.metric("偏度(Skewness)", f"{sk:.3f}")
            rr2.metric("峰度(Kurtosis)", f"{ku:.3f}")

            # 风险等级评估
            risk_score = 0
            if vol_ann > 40: risk_score += 3
            elif vol_ann > 25: risk_score += 2
            else: risk_score += 1
            if abs(max_dd) > 40: risk_score += 3
            elif abs(max_dd) > 25: risk_score += 2
            else: risk_score += 1
            risk_level = "🔴 高风险" if risk_score >= 5 else "🟡 中风险" if risk_score >= 3 else "🟢 低风险"
            st.markdown(f"### 综合风险评级：{risk_level}（得分：{risk_score}/6）")

            # 回撤曲线
            fig_dd = go.Figure()
            fig_dd.add_trace(go.Scatter(x=kdf_r["date"],y=dd,mode="lines",
                name="回撤", fill="tozeroy",
                line=dict(color="#e53935",width=1.5), fillcolor="rgba(229,57,53,0.12)"))
            fig_dd.update_layout(title=f"{rcode} 历史回撤曲线", template="plotly_white",
                height=320, xaxis_title="日期", yaxis_title="回撤(%)",
                margin=dict(l=60,r=30,t=45,b=40))
            st.plotly_chart(fig_dd, use_container_width=True)


# ═══════════════════════════════════════════
# 主程序
# ═══════════════════════════════════════════

def main():
    # ── 侧边栏（必须在顶层调用，不能放在函数内部）─────────────────
    with st.sidebar:
        st.markdown("""
        <div style='text-align:center;padding:1rem 0 0.5rem;'>
            <span style='font-size:2.2rem;'>📈</span>
            <div style='font-size:1.1rem;font-weight:700;color:#fff;margin-top:4px;'>QuantMaster Pro</div>
            <div style='font-size:0.72rem;color:#78909c;margin-top:2px;'>专业量化交易系统</div>
        </div>
        <hr style='border-color:rgba(255,255,255,0.1);margin:0.6rem 0;'/>
        """, unsafe_allow_html=True)

        nav_labels = [f"{icon}  {name}" for name, icon, _ in NAV_ITEMS]
        current_idx = next((i for i, (n, _, _) in enumerate(NAV_ITEMS) if n == st.session_state.get("page", "行情数据")), 0)

        selected = st.radio(
            "导航",
            options=range(len(NAV_ITEMS)),
            index=current_idx,
            format_func=lambda i: nav_labels[i],
            label_visibility="collapsed"
        )
        st.session_state["page"] = NAV_ITEMS[selected][0]

        st.markdown("""
        <hr style='border-color:rgba(255,255,255,0.1);margin:0.8rem 0 0.4rem;'/>
        """, unsafe_allow_html=True)

        st.caption(f"⏰ {datetime.now().strftime('%m-%d  %H:%M:%S')}")

        with st.expander("📖 使用说明"):
            st.markdown("""
- **行情数据** — 实时行情、K线、排行
- **策略编辑器** — 在线编写Python策略
- **历史回测** — 多策略参数回测对比
- **模拟交易** — 虚拟资金实盘演练
- **实盘终端** — 委托/撤单/成交(演示)
- **绩效分析** — 收益/夏普/回撤报告
- **风险管理** — VaR/集中度/预警规则
            """)
        with st.expander("⚙️ 系统设置"):
            st.caption("数据源：东方财富 AkShare")
            st.caption("注意：实盘终端为演示模式")
    # ── 侧边栏结束 ───────────────────────────────────────────

    page = st.session_state["page"]

    if page == "行情数据":
        page_market()
    elif page == "策略编辑器":
        page_strategy_editor()
    elif page == "历史回测":
        page_backtest()
    elif page == "模拟交易":
        page_sim_trade()
    elif page == "实盘终端":
        page_live_terminal()
    elif page == "绩效分析":
        page_performance()
    elif page == "风险管理":
        page_risk()


if __name__ == "__main__":
    main()
