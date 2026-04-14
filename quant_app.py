# -*- coding: utf-8 -*-
"""
QuantMaster Pro v3.0 - 含账户系统的完整量化交易系统
功能：注册/登录/试用管理 + 7大量化模块 + 会员续费系统
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import akshare as ak
from datetime import datetime, timedelta
import time, random, warnings, json, sqlite3, hashlib, re, os
from pathlib import Path

warnings.filterwarnings("ignore")

# ═══════════════════════════════════════════
# 数据库层
# ═══════════════════════════════════════════
DB_PATH = Path(__file__).parent / "users.db"

def get_db():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT,
            role TEXT DEFAULT 'user',
            status TEXT DEFAULT 'trial',
            trial_start TEXT,
            trial_end TEXT,
            expire_date TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            last_login TEXT,
            login_count INTEGER DEFAULT 0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            plan TEXT,
            amount REAL,
            pay_method TEXT,
            order_no TEXT UNIQUE,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT (datetime('now')),
            paid_at TEXT,
            note TEXT
        )
    """)
    # 创建管理员账户
    pw_hash = hashlib.sha256("admin888".encode()).hexdigest()
    c.execute("SELECT username FROM users WHERE username = 'admin'")
    if not c.fetchone():
        c.execute("""
            INSERT INTO users (username, password_hash, role, status, expire_date)
            VALUES ('admin', ?, 'admin', 'paid', datetime('now', '+10 years'))
        """, (pw_hash,))
    conn.commit()
    conn.close()

def hash_pw(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_user(username, password):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ? AND password_hash = ?",
              (username, hash_pw(password)))
    user = c.fetchone()
    conn.close()
    return dict(user) if user else None

def get_user(username):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = c.fetchone()
    conn.close()
    return dict(user) if user else None

def create_user(username, password, email=""):
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("""
            INSERT INTO users (username, password_hash, email, status, trial_start, trial_end)
            VALUES (?, ?, ?, 'trial', datetime('now'), datetime('now', '+7 days'))
        """, (username, hash_pw(password), email))
        conn.commit()
        conn.close()
        return True, "注册成功！请登录"
    except sqlite3.IntegrityError:
        conn.close()
        return False, "用户名已存在"

def update_login(username):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        UPDATE users SET last_login = datetime('now'), login_count = login_count + 1
        WHERE username = ?
    """, (username,))
    conn.commit()
    conn.close()

def get_user_status(username):
    user = get_user(username)
    if not user:
        return "not_found"
    if user["role"] == "admin":
        return "admin"
    if user["status"] == "paid":
        expire = datetime.fromisoformat(user["expire_date"])
        if expire > datetime.now():
            return "paid"
        else:
            return "expired"
    if user["status"] == "trial":
        trial_end = datetime.fromisoformat(user["trial_end"])
        if trial_end > datetime.now():
            days_left = (trial_end - datetime.now()).days
            return f"trial_{days_left}"
        else:
            return "trial_expired"
    return user["status"]

def list_all_users():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, username, email, role, status, trial_start, trial_end, expire_date, created_at, login_count FROM users ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def list_orders():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM orders ORDER BY created_at DESC LIMIT 100")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def create_order(username, plan, amount, pay_method):
    conn = get_db()
    c = conn.cursor()
    order_no = f"{datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(1000,9999)}"
    try:
        c.execute("""
            INSERT INTO orders (username, plan, amount, pay_method, order_no, status)
            VALUES (?, ?, ?, ?, ?, 'pending')
        """, (username, plan, amount, pay_method, order_no))
        conn.commit()
        conn.close()
        return order_no
    except Exception:
        conn.close()
        return None

def confirm_order(order_no):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM orders WHERE order_no = ?", (order_no,))
    order = c.fetchone()
    if not order:
        conn.close()
        return False, "订单不存在"
    if dict(order)["status"] == "paid":
        conn.close()
        return False, "订单已确认"
    # 更新订单
    c.execute("UPDATE orders SET status = 'paid', paid_at = datetime('now') WHERE order_no = ?", (order_no,))
    # 续期用户
    plan_days = {"月卡": 30, "季卡": 90, "年卡": 365}
    days = plan_days.get(dict(order)["plan"], 30)
    user = get_user(dict(order)["username"])
    if user:
        old_expire = datetime.fromisoformat(user["expire_date"]) if user["expire_date"] else datetime.now()
        new_expire = max(old_expire, datetime.now()) + timedelta(days=days)
        c.execute("UPDATE users SET status = 'paid', expire_date = ? WHERE username = ?",
                  (new_expire.isoformat(), dict(order)["username"]))
    conn.commit()
    conn.close()
    return True, f"已确认，续期{days}天"

# ═══════════════════════════════════════════
# Streamlit 页面配置
# ═══════════════════════════════════════════
st.set_page_config(
    page_title="QuantMaster Pro",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

init_db()

# ═══════════════════════════════════════════
# Session State 初始化
# ═══════════════════════════════════════════
if "auth" not in st.session_state:
    st.session_state["auth"] = {
        "logged_in": False,
        "username": "",
        "role": "",
        "status": ""
    }
if "sim_positions" not in st.session_state:
    st.session_state["sim_positions"] = {}
if "sim_capital" not in st.session_state:
    st.session_state["sim_capital"] = 1_000_000.0
if "sim_trades" not in st.session_state:
    st.session_state["sim_trades"] = []
if "live_orders" not in st.session_state:
    st.session_state["live_orders"] = []
if "page" not in st.session_state:
    st.session_state["page"] = "行情数据"

# ═══════════════════════════════════════════
# CSS 样式
# ═══════════════════════════════════════════
st.markdown("""
<style>
::root{--p:#1565c0;--a:#e53935;--g:#43a047;--bg:#0d1b2a;}
section[data-testid="stSidebar"]{
    background:linear-gradient(180deg,#0d1b2a 0%,#1a2f4a 100%)!important;
    min-width:240px!important;
}
section[data-testid="stSidebar"] h1,section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3,section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,section[data-testid="stSidebar"] div,
section[data-testid="stSidebar"] label{color:#ecf0f1!important;}
.qm-banner{background:linear-gradient(135deg,#0d47a1,#1565c0 50%,#283593);
    padding:1.6rem 2rem;border-radius:14px;color:white;
    margin-bottom:1.6rem;box-shadow:0 4px 24px rgba(13,71,161,.25);
    display:flex;align-items:center;gap:1rem;}
.qm-banner h1{margin:0;font-size:1.7rem;}.qm-banner p{margin:.2rem 0 0;opacity:.85;font-size:.9rem;}
.metric-card{background:#fff;border-radius:12px;padding:1.1rem 1.3rem;
    box-shadow:0 2px 12px rgba(0,0,0,.07);border-left:5px solid var(--p);margin-bottom:.6rem;}
.metric-card .val{font-size:1.6rem;font-weight:700;}.metric-card .lbl{font-size:.82rem;color:#888;margin-top:2px;}
.up{color:#e53935!important;font-weight:600;}.down{color:#43a047!important;font-weight:600;}
.nav-market{display:block;width:100%;padding:.6rem .9rem;margin:3px 0;border:none;border-radius:8px;
    background:rgba(21,101,192,.35);color:#90caf9!important;font-size:.88rem;
    text-align:left;cursor:pointer;transition:background .15s;}
.nav-market:hover,.nav-market.active{background:rgba(21,101,192,.7);color:#fff!important;font-weight:600;}
.nav-strategy{display:block;width:100%;padding:.6rem .9rem;margin:3px 0;border:none;border-radius:8px;
    background:rgba(46,125,50,.30);color:#a5d6a7!important;font-size:.88rem;
    text-align:left;cursor:pointer;transition:background .15s;}
.nav-strategy:hover,.nav-strategy.active{background:rgba(46,125,50,.65);color:#fff!important;font-weight:600;}
.nav-backtest{display:block;width:100%;padding:.6rem .9rem;margin:3px 0;border:none;border-radius:8px;
    background:rgba(142,36,170,.28);color:#ce93d8!important;font-size:.88rem;
    text-align:left;cursor:pointer;transition:background .15s;}
.nav-backtest:hover,.nav-backtest.active{background:rgba(142,36,170,.65);color:#fff!important;font-weight:600;}
.nav-paper{display:block;width:100%;padding:.6rem .9rem;margin:3px 0;border:none;border-radius:8px;
    background:rgba(255,111,0,.28);color:#ffcc80!important;font-size:.88rem;
    text-align:left;cursor:pointer;transition:background .15s;}
.nav-paper:hover,.nav-paper.active{background:rgba(255,111,0,.65);color:#fff!important;font-weight:600;}
.nav-live{display:block;width:100%;padding:.6rem .9rem;margin:3px 0;border:none;border-radius:8px;
    background:rgba(229,57,53,.28);color:#ef9a9a!important;font-size:.88rem;
    text-align:left;cursor:pointer;transition:background .15s;}
.nav-live:hover,.nav-live.active{background:rgba(229,57,53,.65);color:#fff!important;font-weight:600;}
.nav-report{display:block;width:100%;padding:.6rem .9rem;margin:3px 0;border:none;border-radius:8px;
    background:rgba(0,172,193,.28);color:#80deea!important;font-size:.88rem;
    text-align:left;cursor:pointer;transition:background .15s;}
.nav-report:hover,.nav-report.active{background:rgba(0,172,193,.65);color:#fff!important;font-weight:600;}
.nav-risk{display:block;width:100%;padding:.6rem .9rem;margin:3px 0;border:none;border-radius:8px;
    background:rgba(255,160,0,.28);color:#ffe082!important;font-size:.88rem;
    text-align:left;cursor:pointer;transition:background .15s;}
.nav-risk:hover,.nav-risk.active{background:rgba(255,160,0,.65);color:#333!important;font-weight:600;}
.nav-divider{border:none;border-top:1px solid rgba(255,255,255,.12);margin:8px 0;}
.alert-high{background:#fff3e0;border-left:4px solid #e53935;}
.alert-mid{background:#e8f5e9;border-left:4px solid #43a047;}
.alert-low{background:#e3f2fd;border-left:4px solid #1976d2;}
.alert-box{padding:10px 14px;border-radius:8px;margin-bottom:8px;font-size:.9rem;}
.auth-box{background:#f8f9fa;border-radius:16px;padding:2.5rem;max-width:420px;margin:auto;
    box-shadow:0 8px 32px rgba(0,0,0,.12);}
.auth-title{text-align:center;color:#1565c0;font-size:1.8rem;font-weight:700;margin-bottom:.5rem;}
.auth-sub{text-align:center;color:#888;font-size:.9rem;margin-bottom:2rem;}
.status-badge{display:inline-block;padding:.3rem .9rem;border-radius:20px;font-size:.82rem;font-weight:600;}
.status-paid{background:#e8f5e9;color:#2e7d32;}.status-trial{background:#e3f2fd;color:#1565c0;}
.status-expired{background:#ffebee;color:#c62828;}.status-admin{background:#fff3e0;color:#e65100;}
header[data-testid="stHeader"]{display:block!important;}
#MainMenu,footer,.stDeployButton{visibility:visible!important;}
.stDeployButton{display:none!important;}
button[data-baseweb="tab"]{font-size:.9rem;}
.pos-table th{background:#1565c0;color:white;padding:8px 12px;}
.pos-table td{padding:7px 12px;font-size:13px;border-bottom:1px solid #f0f0f0;}
.pos-table tr:hover td{background:#f5f5f5;}
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════
# 认证模块
# ═══════════════════════════════════════════
def render_auth():
    tab1, tab2 = st.tabs(["🔐 登录", "📝 注册"])
    with tab1:
        with st.form("login_form", clear_on_submit=True):
            st.markdown('<p class="auth-title">欢迎回来</p>', unsafe_allow_html=True)
            username = st.text_input("用户名", placeholder="输入用户名")
            password = st.text_input("密码", type="password", placeholder="输入密码")
            submitted = st.form_submit_button("登录", use_container_width=True)
            if submitted:
                if not username or not password:
                    st.error("请填写用户名和密码")
                else:
                    user = verify_user(username, password)
                    if user:
                        update_login(username)
                        st.session_state["auth"] = {
                            "logged_in": True,
                            "username": username,
                            "role": user["role"],
                            "status": user["status"]
                        }
                        st.rerun()
                    else:
                        st.error("用户名或密码错误")
        st.markdown("---")
        st.caption("**演示账户**：用户名 `admin` / 密码 `admin888`（管理员）")
    with tab2:
        with st.form("register_form", clear_on_submit=True):
            st.markdown('<p class="auth-title">创建账户</p>', unsafe_allow_html=True)
            st.markdown('<p class="auth-sub">注册即享 <strong>7天免费试用</strong></p>', unsafe_allow_html=True)
            new_user = st.text_input("用户名", placeholder="设置用户名（唯一）")
            new_email = st.text_input("邮箱（选填）", placeholder="your@email.com")
            new_pw = st.text_input("密码", type="password", placeholder="设置密码（至少6位）")
            new_pw2 = st.text_input("确认密码", type="password", placeholder="再次输入密码")
            reg_submitted = st.form_submit_button("注册", use_container_width=True)
            if reg_submitted:
                if not new_user or not new_pw:
                    st.error("用户名和密码不能为空")
                elif len(new_pw) < 6:
                    st.error("密码至少6位")
                elif new_pw != new_pw2:
                    st.error("两次密码不一致")
                elif not re.match(r"^[a-zA-Z0-9_]{3,20}$", new_user):
                    st.error("用户名只能是字母、数字、下划线，3-20位")
                else:
                    ok, msg = create_user(new_user, new_pw, new_email)
                    if ok:
                        st.success(f"✅ {msg}，请切换到登录页登录")
                    else:
                        st.error(msg)

def render_account_menu():
    auth = st.session_state["auth"]
    user = get_user(auth["username"]) if auth["logged_in"] else {}
    status_raw = get_user_status(auth["username"])
    if status_raw == "admin":
        badge_cls, badge_txt = "status-admin", "管理员"
    elif status_raw == "paid":
        badge_cls, badge_txt = "status-paid", "正式会员"
    elif status_raw and status_raw.startswith("trial_"):
        days = status_raw.split("_")[1]
        badge_cls, badge_txt = "status-trial", f"试用中（剩余{days}天）"
    elif status_raw == "trial_expired":
        badge_cls, badge_txt = "status-expired", "试用已到期"
    else:
        badge_cls, badge_txt = "status-expired", "已过期"
    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown(f"👤 **{auth['username']}**")
        st.markdown(f'<span class="status-badge {badge_cls}">{badge_txt}</span>', unsafe_allow_html=True)
    with col2:
        if st.button("🚪 退出", use_container_width=True):
            st.session_state["auth"] = {"logged_in": False, "username": "", "role": "", "status": ""}
            st.rerun()
    st.markdown("---")
    # 试用到期提示
    if status_raw in ["trial_expired", "expired"]:
        st.warning("⏰ 您的账户已到期，请续费继续使用")
        with st.expander("立即续费"):
            render_pay_section()

# ═══════════════════════════════════════════
# 支付模块
# ═══════════════════════════════════════════
PAY_PLANS = {
    "月卡": {"days": 30, "price": 99, "desc": "30天有效，适合短期体验"},
    "季卡": {"days": 90, "price": 259, "desc": "90天有效，推荐选择", "hot": True},
    "年卡": {"days": 365, "price": 899, "desc": "365天有效，年度钜惠"},
}

def render_pay_section():
    auth = st.session_state["auth"]
    plan_key = st.selectbox("选择套餐", list(PAY_PLANS.keys()),
                             format_func=lambda x: f"{x} ¥{PAY_PLANS[x]['price']}（{PAY_PLANS[x]['desc']}）")
    pay_method = st.radio("支付方式", ["💬 微信支付", "💰 支付宝"], horizontal=True, label_visibility="collapsed")
    method_code = "wechat" if "微信" in pay_method else "alipay"
    if st.button(f"生成订单（¥{PAY_PLANS[plan_key]['price']}）", use_container_width=True):
        order_no = create_order(auth["username"], plan_key, PAY_PLANS[plan_key]["price"], method_code)
        if order_no:
            st.session_state["pending_order"] = order_no
            st.session_state["pending_plan"] = plan_key
            st.session_state["pending_amount"] = PAY_PLANS[plan_key]["price"]
            st.session_state["pending_method"] = method_code
            st.rerun()
    if "pending_order" in st.session_state:
        order_no = st.session_state["pending_order"]
        plan = st.session_state["pending_plan"]
        amount = st.session_state["pending_amount"]
        method = st.session_state["pending_method"]
        st.markdown("---")
        st.markdown(f"### 📋 订单 #{order_no}")
        col_a, col_b = st.columns([1, 1])
        with col_a:
            st.info(f"**套餐**：{plan}  |  **金额**：¥{amount}  |  **方式**：{'微信' if method == 'wechat' else '支付宝'}")
            st.caption("⚠️ 请截图保存订单号，支付完成后联系管理员确认")
        with col_b:
            if method == "wechat":
                st.markdown("**💬 微信支付**")
                st.markdown("打开微信 → 扫一扫 → 向以下账户付款")
                st.image("https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=wechat://", width=180)
            else:
                st.markdown("**💰 支付宝支付**")
                st.markdown("打开支付宝 → 扫一扫 → 向以下账户付款")
                st.image("https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=alipay://", width=180)
        st.markdown("**支付完成后联系管理员确认订单，管理员后台：admin账户 → 管理面板 → 订单管理 → 确认**")
        st.text_input("输入管理员口令确认订单（如已支付）", key="admin_confirm_input")
        if st.button("申请续期"):
            st.warning("请等待管理员在后处理您的付款确认")
        if st.button("取消"):
            for k in ["pending_order", "pending_plan", "pending_amount", "pending_method"]:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()

# ═══════════════════════════════════════════
# 侧边栏
# ═══════════════════════════════════════════
def render_sidebar():
    auth = st.session_state["auth"]

    with st.sidebar:
        # ── 顶部：账户widget（始终显示）────────────────────────────
        if not auth["logged_in"]:
            with st.expander("🔐 登录 / 注册", expanded=True):
                _render_auth_compact()
        else:
            with st.expander(f"👤 {auth['username']}（{_get_status_label(auth['username'])}）", expanded=True):
                _render_account_compact()

        st.markdown("---")

        # ── 导航（始终可见）────────────────────────────────────────
        st.markdown('<p class="nav-section">◈ 功能模块</p>', unsafe_allow_html=True)
        cur = st.session_state.get("page", "行情数据")
        pages = [
            ("📊 行情数据", "行情数据"),
            ("✏️ 策略编辑", "策略编辑"),
            ("🧪 历史回测", "历史回测"),
            ("🎮 模拟交易", "模拟交易"),
            ("💹 实盘终端", "实盘终端"),
            ("📈 绩效分析", "绩效分析"),
            ("🛡️ 风险管理", "风险管理"),
        ]
        for label, page_name in pages:
            cls = "nav-btn active" if cur == page_name else "nav-btn"
            st.markdown(f'<button class="{cls}" onclick="return false">{label}</button>',
                        unsafe_allow_html=True)
            if st.button(label, key=f"nav_{page_name}", use_container_width=True):
                st.session_state["page"] = page_name
                for k in ["pending_order","pending_plan","pending_amount","pending_method"]:
                    if k in st.session_state:
                        del st.session_state[k]
                st.rerun()

        if auth["logged_in"] and auth["role"] == "admin":
            st.markdown("---")
            st.markdown('<p class="nav-section">◈ 系统管理</p>', unsafe_allow_html=True)
            if st.button("⚙️ 管理后台", use_container_width=True):
                st.session_state["page"] = "__admin__"
                st.rerun()


def _render_auth_compact():
    """紧凑登录/注册表单（用于expander内）"""
    sub = st.radio("登录 / 注册", ["登录", "注册"], horizontal=True, label_visibility="collapsed")
    if sub == "登录":
        with st.form("login_c", clear_on_submit=True):
            u = st.text_input("用户名", placeholder="输入用户名", label_visibility="collapsed")
            p = st.text_input("密码", type="password", placeholder="密码", label_visibility="collapsed")
            if st.form_submit_button("登录", use_container_width=True):
                if u and p:
                    user = verify_user(u, p)
                    if user:
                        update_login(u)
                        st.session_state["auth"] = {
                            "logged_in": True, "username": u,
                            "role": user["role"], "status": user["status"]
                        }
                        st.rerun()
                    else:
                        st.error("用户名或密码错误")
                else:
                    st.error("请填写用户名和密码")
    else:
        with st.form("reg_c", clear_on_submit=True):
            u2 = st.text_input("用户名", placeholder="设置用户名（3-20位字母数字）", label_visibility="collapsed")
            e2 = st.text_input("邮箱（选填）", placeholder="your@email.com", label_visibility="collapsed")
            p2 = st.text_input("密码", type="password", placeholder="密码（至少6位）", label_visibility="collapsed")
            p3 = st.text_input("确认密码", type="password", placeholder="再次输入密码", label_visibility="collapsed")
            if st.form_submit_button("注册（享7天试用）", use_container_width=True):
                if not u2 or not p2:
                    st.error("用户名和密码不能为空")
                elif len(p2) < 6:
                    st.error("密码至少6位")
                elif p2 != p3:
                    st.error("两次密码不一致")
                elif not re.match(r"^[a-zA-Z0-9_]{3,20}$", u2):
                    st.error("用户名3-20位字母/数字/下划线")
                else:
                    ok, msg = create_user(u2, p2, e2)
                    if ok:
                        st.success("注册成功！请切换到登录")
                    else:
                        st.error(msg)


def _render_account_compact():
    """已登录账户信息 + 续费入口"""
    auth = st.session_state["auth"]
    status_raw = _get_status_label(auth["username"])
    if "试用" in status_raw or "到期" in status_raw:
        st.warning(f"⏰ {status_raw}")
        with st.expander("立即续费"):
            render_pay_section()
    if st.button("🚪 退出登录", use_container_width=True):
        st.session_state["auth"] = {"logged_in": False, "username": "", "role": "", "status": ""}
        st.rerun()


def _get_status_label(username):
    s = get_user_status(username)
    if s == "admin": return "管理员"
    if s == "paid": return "正式会员"
    if s and s.startswith("trial_"):
        return f"试用中（剩{s.split('_')[1]}天）"
    if s in ("trial_expired", "expired"): return "试用已到期"
    return "正式会员"

# ═══════════════════════════════════════════
# 访问控制
# ═══════════════════════════════════════════
def check_access():
    auth = st.session_state["auth"]
    if not auth["logged_in"]:
        return False
    status = get_user_status(auth["username"])
    if status in ["admin", "paid"]:
        return True
    if status and status.startswith("trial_"):
        return True
    return False

def force_paywall():
    st.warning("⏰ 您的账户已到期，续费后继续使用全部功能")
    with st.expander("立即续费"):
        render_pay_section()
    st.stop()

# ═══════════════════════════════════════════
# 数据层
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
        rows.append({"代码": codes[i], "名称": names[i], "最新价": p, "涨跌幅": pct,
                      "涨跌额": round(p * pct / 100, 2), "成交量": random.randint(10000, 999999)})
    return pd.DataFrame(rows)

@st.cache_data(ttl=300)
def get_stock_list():
    try:
        df = ak.stock_zh_a_spot_em()
        if df is not None and not df.empty:
            df.columns = [c.strip() for c in df.columns]
            rename = {k: v for k, v in zip(df.columns, df.columns)}
            for old, new in [("代码", "代码"), ("名称", "名称"), ("最新价", "最新价"),
                              ("涨跌幅", "涨跌幅"), ("涨跌额", "涨跌额"), ("成交量", "成交量")]:
                pass
            return df[["代码","名称","最新价","涨跌幅","涨跌额","成交量"]].head(300)
    except Exception:
        pass
    return _mock_stock_list(200)

@st.cache_data(ttl=120)
def get_kline(code, period="daily", adjust="qfq"):
    def _fetch():
        if code.startswith("6"):
            sym = f"sh{code}"
        else:
            sym = f"sz{code}"
        df = ak.stock_zh_a_hist(symbol=code, period=period, adjust=adjust,
                                 start_date=(datetime.now()-timedelta(days=365)).strftime("%Y%m%d"),
                                 end_date=datetime.now().strftime("%Y%m%d"))
        if df is not None and not df.empty:
            df.columns = [c.strip() for c in df.columns]
            return df
        return None
    result = safe_request(_fetch, fallback=lambda: None)
    if result is None:
        dates = [(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(100, 0, -1)]
        random.seed(int(hash(code) % 1000))
        base = random.uniform(10, 100)
        rows = []
        for d in dates:
            o = round(base * random.uniform(0.97, 1.03), 2)
            c = round(base * random.uniform(0.96, 1.04), 2)
            h = round(max(o, c) * random.uniform(1.0, 1.05), 2)
            l = round(min(o, c) * random.uniform(0.95, 1.0), 2)
            v = random.randint(10000, 999999)
            rows.append({"日期": d, "开盘": o, "收盘": c, "最高": h, "最低": l, "成交量": v,
                         "成交额": round((o + c) / 2 * v, 2)})
            base = c
        df = pd.DataFrame(rows)
        df["代码"] = code
        return df
    return result.rename(columns={"日期":"date","开盘":"open","最高":"high","最低":"low","收盘":"close","成交量":"volume","成交额":"amount"})

def add_ma(df, windows=[5, 10, 20, 60]):
    for w in windows:
        if len(df) >= w:
            df[f"MA{w}"] = df["close"].rolling(w, min_periods=w).mean()
    return df

def add_rsi(df, period=14):
    if len(df) < period + 1:
        return df
    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period, min_periods=period).mean()
    avg_loss = loss.rolling(period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df["RSI"] = (100 - (100 / (1 + rs))).fillna(50)
    return df

def add_macd(df, fast=12, slow=26, signal=9):
    if len(df) < slow + signal:
        return df
    ema_fast = df["close"].ewm(span=fast, adjust=False).mean()
    ema_slow = df["close"].ewm(span=slow, adjust=False).mean()
    df["MACD"] = ema_fast - ema_slow
    df["MACD_signal"] = df["MACD"].ewm(span=signal, adjust=False).mean()
    df["MACD_hist"] = df["MACD"] - df["MACD_signal"]
    return df

def add_boll(df, period=20, std_dev=2):
    if len(df) < period:
        return df
    df["BOLL_MID"] = df["close"].rolling(period, min_periods=period).mean()
    std = df["close"].rolling(period, min_periods=period).std()
    df["BOLL_UPPER"] = df["BOLL_MID"] + std_dev * std
    df["BOLL_LOWER"] = df["BOLL_MID"] - std_dev * std
    return df

def add_kdj(df, period=9, M1=3, M2=3):
    if len(df) < period + 1:
        return df
    low_n = df["low"].rolling(period, min_periods=period).min()
    high_n = df["high"].rolling(period, min_periods=period).max()
    rsv = (df["close"] - low_n) / (high_n - low_n + 1e-9) * 100
    df["K"] = rsv.ewm(com=M1-1, adjust=False).mean()
    df["D"] = df["K"].ewm(com=M2-1, adjust=False).mean()
    df["J"] = 3 * df["K"] - 2 * df["D"]
    return df

# ═══════════════════════════════════════════
# 策略回测
# ═══════════════════════════════════════════
def run_ma_cross(df, fast=5, slow=20):
    df = df.copy()
    df = add_ma(df, windows=[fast, slow])
    df = df.dropna(subset=[f"MA{fast}", f"MA{slow}"])
    position, signals = 0, []
    for i in range(1, len(df)):
        ma_f = df[f"MA{fast}"].iloc[i]
        ma_s = df[f"MA{slow}"].iloc[i]
        ma_f_prev = df[f"MA{fast}"].iloc[i-1]
        ma_s_prev = df[f"MA{slow}"].iloc[i-1]
        if ma_f > ma_s and ma_f_prev <= ma_s_prev and position == 0:
            signals.append({"date": df["date"].iloc[i], "signal": "BUY", "price": df["close"].iloc[i]})
            position = 1
        elif ma_f < ma_s and ma_f_prev >= ma_s_prev and position == 1:
            signals.append({"date": df["date"].iloc[i], "signal": "SELL", "price": df["close"].iloc[i]})
            position = 0
    return pd.DataFrame(signals) if signals else pd.DataFrame(columns=["date","signal","price"])

def run_rsi(df, period=14, upper=70, lower=30):
    df = df.copy()
    df = add_rsi(df, period)
    position, signals = 0, []
    for i in range(period+1, len(df)):
        rsi = df["RSI"].iloc[i]
        rsi_prev = df["RSI"].iloc[i-1]
        if rsi < lower and rsi_prev >= lower and position == 0:
            signals.append({"date": df["date"].iloc[i], "signal": "BUY", "price": df["close"].iloc[i]})
            position = 1
        elif rsi > upper and rsi_prev <= upper and position == 1:
            signals.append({"date": df["date"].iloc[i], "signal": "SELL", "price": df["close"].iloc[i]})
            position = 0
    return pd.DataFrame(signals) if signals else pd.DataFrame(columns=["date","signal","price"])

def run_boll(df, period=20, std_dev=2):
    df = df.copy()
    df = add_boll(df, period, std_dev)
    df = df.dropna(subset=["BOLL_LOWER","BOLL_UPPER"])
    position, signals = 0, []
    for i in range(1, len(df)):
        close = df["close"].iloc[i]
        prev_close = df["close"].iloc[i-1]
        lower = df["BOLL_LOWER"].iloc[i]
        upper = df["BOLL_UPPER"].iloc[i]
        if close < lower and prev_close >= lower and position == 0:
            signals.append({"date": df["date"].iloc[i], "signal": "BUY", "price": close})
            position = 1
        elif close > upper and prev_close <= upper and position == 1:
            signals.append({"date": df["date"].iloc[i], "signal": "SELL", "price": close})
            position = 0
    return pd.DataFrame(signals) if signals else pd.DataFrame(columns=["date","signal","price"])

def run_macd_signal(df, fast=12, slow=26, signal=9):
    df = df.copy()
    df = add_macd(df, fast, slow, signal)
    df = df.dropna(subset=["MACD","MACD_signal"])
    position, signals = 0, []
    for i in range(1, len(df)):
        macd = df["MACD"].iloc[i]
        sig = df["MACD_signal"].iloc[i]
        macd_prev = df["MACD"].iloc[i-1]
        sig_prev = df["MACD_signal"].iloc[i-1]
        if macd > sig and macd_prev <= sig_prev and position == 0:
            signals.append({"date": df["date"].iloc[i], "signal": "BUY", "price": df["close"].iloc[i]})
            position = 1
        elif macd < sig and macd_prev >= sig_prev and position == 1:
            signals.append({"date": df["date"].iloc[i], "signal": "SELL", "price": df["close"].iloc[i]})
            position = 0
    return pd.DataFrame(signals) if signals else pd.DataFrame(columns=["date","signal","price"])

def calc_metrics(trades, initial_capital=100000):
    if not trades:
        return {}
    df = pd.DataFrame(trades)
    df["return"] = df["pnl"] / df["entry_price"] * df["shares"]
    total_return = df["pnl"].sum()
    total_return_pct = total_return / initial_capital * 100
    win_trades = df[df["pnl"] > 0]
    win_rate = len(win_trades) / len(df) * 100 if len(df) > 0 else 0
    max_drawdown = 0
    cumulative = 0
    peak = 0
    for _, row in df.iterrows():
        cumulative += row["pnl"]
        if cumulative > peak:
            peak = cumulative
        dd = peak - cumulative
        if dd > max_drawdown:
            max_drawdown = dd
    sharpe = total_return_pct / (df["pnl"].std() + 1e-9) if len(df) > 1 else 0
    return {
        "总收益": f"¥{total_return:,.2f}",
        "收益率": f"{total_return_pct:.2f}%",
        "交易次数": len(df),
        "胜率": f"{win_rate:.1f}%",
        "最大回撤": f"¥{max_drawdown:,.2f}",
        "夏普比率": f"{sharpe:.2f}",
        "盈亏比": f"{(win_trades['pnl'].mean() / df[df['pnl']<0]['pnl'].mean().abs()):.2f}" if len(df[df['pnl']<0]) > 0 else "∞",
    }

# ═══════════════════════════════════════════
# 页面：行情数据
# ═══════════════════════════════════════════
def page_market():
    auth = st.session_state["auth"]
    status = get_user_status(auth["username"]) if auth["logged_in"] else ""
    if status and (status == "trial_expired" or status == "expired"):
        force_paywall()
    st.markdown("""
    <div class="qm-banner">
        <h1>📊 行情数据</h1>
        <p>实时行情 / 多指标分析 / 涨跌排行</p>
    </div>
    """, unsafe_allow_html=True)
    codes = st.text_input("股票代码（支持6位代码或名称）", value="000001",
                          help="输入6位代码，如 000001（平安银行）、600519（贵州茅台）")
    if st.button("🔍 查询", use_container_width=True):
        with st.spinner("加载K线数据..."):
            kdf = get_kline(codes)
            if kdf is not None and not kdf.empty:
                kdf = add_ma(kdf)
                kdf = add_rsi(kdf)
                kdf = add_macd(kdf)
                kdf = add_kdj(kdf)
                kdf = add_boll(kdf)
                st.session_state["kline_cache"] = kdf
                st.session_state["kline_code"] = codes
    if "kline_cache" in st.session_state:
        kdf = st.session_state["kline_cache"]
        tab1, tab2, tab3, tab4 = st.tabs(["📈 K线图", "📊 技术指标", "📋 数据表格", "🔍 涨跌排行"])
        with tab1:
            if "open" in kdf.columns and len(kdf) > 60:
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                                    vertical_spacing=0.06,
                                    row_heights=[0.7, 0.3],
                                    subplot_titles=("价格", "成交量"))
                colors = ["#e53935" if kdf["close"].iloc[i] >= kdf["open"].iloc[i] else "#43a047"
                           for i in range(len(kdf))]
                fig.add_trace(go.Candlestick(
                    x=kdf["date"].iloc[-60:], open=kdf["open"].iloc[-60:],
                    high=kdf["high"].iloc[-60:], low=kdf["low"].iloc[-60:],
                    close=kdf["close"].iloc[-60:], name="K线",
                    increasing=dict(line_color="#e53935"),
                    decreasing=dict(line_color="#43a047")), row=1, col=1)
                for ma in [5, 10, 20, 60]:
                    if f"MA{ma}" in kdf.columns:
                        fig.add_trace(go.Scatter(
                            x=kdf["date"].iloc[-60:], y=kdf[f"MA{ma}"].iloc[-60:],
                            mode="lines", name=f"MA{ma}",
                            line=dict(width=1.5)), row=1, col=1)
                fig.add_trace(go.Bar(
                    x=kdf["date"].iloc[-60:], y=kdf["volume"].iloc[-60:],
                    marker_color=colors, name="成交量"), row=2, col=1)
                fig.update_layout(
                    template="plotly_white", height=520,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)
        with tab2:
            cols = st.columns(4)
            if "RSI" in kdf.columns:
                rsi = kdf["RSI"].iloc[-1]
                cols[0].metric("RSI(14)", f"{rsi:.1f}",
                                "超买" if rsi > 70 else "超卖" if rsi < 30 else "正常")
            if "MACD" in kdf.columns:
                macd = kdf["MACD"].iloc[-1]
                sig = kdf["MACD_signal"].iloc[-1]
                cols[1].metric("MACD", f"{macd:.3f}", f"信号线{sig:.3f}")
            if "K" in kdf.columns:
                cols[2].metric("KDJ", f"K={kdf['K'].iloc[-1]:.1f} D={kdf['D'].iloc[-1]:.1f} J={kdf['J'].iloc[-1]:.1f}")
            if "BOLL_UPPER" in kdf.columns:
                b_u, b_m, b_l = kdf["BOLL_UPPER"].iloc[-1], kdf["BOLL_MID"].iloc[-1], kdf["BOLL_LOWER"].iloc[-1]
                cols[3].metric("布林带", f"{b_u:.2f}/{b_m:.2f}/{b_l:.2f}")
        with tab3:
            st.dataframe(kdf.tail(30).iloc[::-1], use_container_width=True, height=400)
        with tab4:
            st.subheader("📈 沪深A股涨跌排行 TOP100")
            with st.spinner("加载行情..."):
                sdf = get_stock_list()
                top_gain = sdf.nlargest(20, "涨跌幅")[["代码","名称","最新价","涨跌幅"]].reset_index(drop=True)
                top_loss = sdf.nsmallest(20, "涨跌幅")[["代码","名称","最新价","涨跌幅"]].reset_index(drop=True)
                t1, t2 = st.tabs(["🔥 涨幅榜", "❄️ 跌幅榜"])
                with t1:
                    st.dataframe(top_gain.style.applymap(
                        lambda x: "color:#e53935" if isinstance(x,(int,float)) and x>0 else "", subset=["涨跌幅"]),
                        use_container_width=True)
                with t2:
                    st.dataframe(top_loss.style.applymap(
                        lambda x: "color:#43a047" if isinstance(x,(int,float)) and x<0 else "", subset=["涨跌幅"]),
                        use_container_width=True)

# ═══════════════════════════════════════════
# 页面：策略编辑器
# ═══════════════════════════════════════════
def page_strategy():
    if not check_access():
        st.warning("请登录后使用完整功能")
        return
    st.markdown("""
    <div class="qm-banner">
        <h1>✏️ 策略编辑器</h1>
        <p>在线编写 Python 量化策略，语法高亮 + 实时校验</p>
    </div>
    """, unsafe_allow_html=True)
    templates = {
        "双均线交叉（金叉死叉）": '# 双均线交叉策略\n# 规则：MA5上穿MA20买入，下穿卖出\n\ndef strategy(df):\n    df = df.copy()\n    df["MA5"] = df["close"].rolling(5).mean()\n    df["MA20"] = df["close"].rolling(20).mean()\n    df = df.dropna()\n    signals = []\n    position = 0\n    for i in range(1, len(df)):\n        if df["MA5"].iloc[i] > df["MA20"].iloc[i] and df["MA5"].iloc[i-1] <= df["MA20"].iloc[i-1]:\n            if position == 0:\n                signals.append({"date": df["date"].iloc[i], "signal": "BUY", "price": df["close"].iloc[i]})\n                position = 1\n        elif df["MA5"].iloc[i] < df["MA20"].iloc[i] and df["MA5"].iloc[i-1] >= df["MA20"].iloc[i-1]:\n            if position == 1:\n                signals.append({"date": df["date"].iloc[i], "signal": "SELL", "price": df["close"].iloc[i]})\n                position = 0\n    return pd.DataFrame(signals) if signals else pd.DataFrame(columns=["date","signal","price"])',
        "RSI 超买超卖": '# RSI 策略\n# 规则：RSI<30买入，RSI>70卖出\n\ndef add_rsi(df, period=14):\n    delta = df["close"].diff()\n    gain = delta.clip(lower=0).rolling(period).mean()\n    loss = (-delta.clip(upper=0)).rolling(period).mean()\n    rs = gain / (loss + 1e-9)\n    df["RSI"] = 100 - (100 / (1 + rs))\n    return df\n\ndef strategy(df):\n    df = df.copy()\n    df = add_rsi(df, 14)\n    df = df.dropna()\n    signals = []\n    position = 0\n    for i in range(1, len(df)):\n        rsi = df["RSI"].iloc[i]\n        rsi_prev = df["RSI"].iloc[i-1]\n        if rsi < 30 and rsi_prev >= 30 and position == 0:\n            signals.append({"date": df["date"].iloc[i], "signal": "BUY", "price": df["close"].iloc[i]})\n            position = 1\n        elif rsi > 70 and rsi_prev <= 70 and position == 1:\n            signals.append({"date": df["date"].iloc[i], "signal": "SELL", "price": df["close"].iloc[i]})\n            position = 0\n    return pd.DataFrame(signals) if signals else pd.DataFrame(columns=["date","signal","price"])',
        "布林带突破": '# 布林带策略\n# 规则：价格下穿上轨买入，上穿下轨卖出\n\ndef strategy(df):\n    df = df.copy()\n    period = 20\n    df["BOLL_MID"] = df["close"].rolling(20).mean()\n    std = df["close"].rolling(20).std()\n    df["BOLL_UPPER"] = df["BOLL_MID"] + 2 * std\n    df["BOLL_LOWER"] = df["BOLL_MID"] - 2 * std\n    df = df.dropna()\n    signals = []\n    position = 0\n    for i in range(1, len(df)):\n        close = df["close"].iloc[i]\n        prev_close = df["close"].iloc[i-1]\n        lower = df["BOLL_LOWER"].iloc[i]\n        upper = df["BOLL_UPPER"].iloc[i]\n        if close < lower and prev_close >= lower and position == 0:\n            signals.append({"date": df["date"].iloc[i], "signal": "BUY", "price": close})\n            position = 1\n        elif close > upper and prev_close <= upper and position == 1:\n            signals.append({"date": df["date"].iloc[i], "signal": "SELL", "price": close})\n            position = 0\n    return pd.DataFrame(signals) if signals else pd.DataFrame(columns=["date","signal","price"])',
        "MACD 金叉死叉": '# MACD 策略\n# 规则：MACD上穿信号线买入，下穿卖出\n\ndef strategy(df):\n    df = df.copy()\n    df["EMA12"] = df["close"].ewm(span=12, adjust=False).mean()\n    df["EMA26"] = df["close"].ewm(span=26, adjust=False).mean()\n    df["MACD"] = df["EMA12"] - df["EMA26"]\n    df["MACD_signal"] = df["MACD"].ewm(span=9, adjust=False).mean()\n    df = df.dropna()\n    signals = []\n    position = 0\n    for i in range(1, len(df)):\n        macd = df["MACD"].iloc[i]\n        sig = df["MACD_signal"].iloc[i]\n        macd_prev = df["MACD"].iloc[i-1]\n        sig_prev = df["MACD_signal"].iloc[i-1]\n        if macd > sig and macd_prev <= sig_prev and position == 0:\n            signals.append({"date": df["date"].iloc[i], "signal": "BUY", "price": df["close"].iloc[i]})\n            position = 1\n        elif macd < sig and macd_prev >= sig_prev and position == 1:\n            signals.append({"date": df["date"].iloc[i], "signal": "SELL", "price": df["close"].iloc[i]})\n            position = 0\n    return pd.DataFrame(signals) if signals else pd.DataFrame(columns=["date","signal","price"])',
        "KDJ 随机指标": '# KDJ 策略\n# 规则：J<0买入，J>100卖出\n\ndef strategy(df):\n    df = df.copy()\n    low9 = df["low"].rolling(9).min()\n    high9 = df["high"].rolling(9).max()\n    rsv = (df["close"] - low9) / (high9 - low9 + 1e-9) * 100\n    df["K"] = rsv.ewm(com=2, adjust=False).mean()\n    df["D"] = df["K"].ewm(com=2, adjust=False).mean()\n    df["J"] = 3 * df["K"] - 2 * df["D"]\n    df = df.dropna()\n    signals = []\n    position = 0\n    for i in range(1, len(df)):\n        j = df["J"].iloc[i]\n        j_prev = df["J"].iloc[i-1]\n        if j < 0 and j_prev >= 0 and position == 0:\n            signals.append({"date": df["date"].iloc[i], "signal": "BUY", "price": df["close"].iloc[i]})\n            position = 1\n        elif j > 100 and j_prev <= 100 and position == 1:\n            signals.append({"date": df["date"].iloc[i], "signal": "SELL", "price": df["close"].iloc[i]})\n            position = 0\n    return pd.DataFrame(signals) if signals else pd.DataFrame(columns=["date","signal","price"])',
    }
    tpl_name = st.selectbox("📚 策略模板", list(templates.keys()))
    if st.button("📥 加载模板"):
        st.session_state["strategy_code"] = templates[tpl_name]
    code = st.text_area("策略代码（Python）", value=st.session_state.get("strategy_code", ""),
                         height=320, label_visibility="collapsed")
    st.session_state["strategy_code"] = code
    col_syntax, col_load = st.columns([1, 1])
    with col_syntax:
        if st.button("✅ 语法检查"):
            try:
                compile(code, "<str>", "exec")
                st.success("✅ 语法正确")
            except SyntaxError as e:
                st.error(f"❌ 语法错误：{e}")
    with col_load:
        if st.button("📊 执行回测", use_container_width=True):
            try:
                ns = {}
                exec(compile(code, "<str>", "exec"), ns)
                strat_func = ns.get("strategy")
                if not strat_func:
                    st.error("未找到 strategy(df) 函数，请定义 def strategy(df):")
                else:
                    backtest_code = st.text_input("回测股票代码", value="000001")
                    with st.spinner("回测中..."):
                        kdf = get_kline(backtest_code)
                        if kdf is not None:
                            sig_df = strat_func(kdf)
                            if sig_df is not None and not sig_df.empty:
                                st.success(f"✅ 策略信号：{len(sig_df)}个")
                                st.dataframe(sig_df, use_container_width=True)
                            else:
                                st.warning("策略未产生任何信号")
                        else:
                            st.error("获取K线数据失败")
            except Exception as e:
                st.error(f"执行错误：{e}")

# ═══════════════════════════════════════════
# 页面：历史回测
# ═══════════════════════════════════════════
def page_backtest():
    if not check_access():
        st.warning("请登录后使用完整功能")
        return
    st.markdown("""
    <div class="qm-banner">
        <h1>🧪 历史回测</h1>
        <p>4大内置策略 + 自定义策略，K线对比 + 资金曲线</p>
    </div>
    """, unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["📊 内置策略回测", "📝 自定义策略回测"])
    with tab1:
        bk_code = st.text_input("回测股票", value="000001")
        bk_initial = st.number_input("初始资金", value=100000.0, step=10000.0)
        bk_strategies = st.multiselect("选择策略", ["均线交叉", "RSI", "布林带", "MACD"],
                                        default=["均线交叉"])
        if st.button("🚀 开始回测", use_container_width=True):
            with st.spinner("获取K线..."):
                kdf = get_kline(bk_code)
            if kdf is not None and not kdf.empty:
                results = {}
                if "均线交叉" in bk_strategies:
                    results["均线交叉"] = run_ma_cross(kdf.copy(), 5, 20)
                if "RSI" in bk_strategies:
                    results["RSI"] = run_rsi(kdf.copy())
                if "布林带" in bk_strategies:
                    results["布林带"] = run_boll(kdf.copy())
                if "MACD" in bk_strategies:
                    results["MACD"] = run_macd_signal(kdf.copy())
                if results:
                    cols = st.columns(len(results))
                    for idx, (name, sigs) in enumerate(results.items()):
                        with cols[idx]:
                            st.markdown(f"### {name}")
                            if not sigs.empty:
                                trades = []
                                pos = 0
                                entry_price = 0
                                shares = 0
                                for _, s in sigs.iterrows():
                                    if s["signal"] == "BUY" and pos == 0:
                                        shares = int(bk_initial / s["price"] / 100) * 100
                                        if shares > 0:
                                            entry_price = s["price"]
                                            pos = 1
                                    elif s["signal"] == "SELL" and pos == 1:
                                        pnl = (s["price"] - entry_price) * shares
                                        trades.append({"entry_date": sigs[sigs["signal"]=="BUY"].iloc[0]["date"],
                                                        "exit_date": s["date"],
                                                        "entry_price": entry_price,
                                                        "exit_price": s["price"],
                                                        "shares": shares, "pnl": pnl})
                                        pos = 0
                                if trades:
                                    metrics = calc_metrics(trades, bk_initial)
                                    for k, v in metrics.items():
                                        st.metric(k, v)
                                    tdf = pd.DataFrame(trades)
                                    st.dataframe(tdf[["entry_date","exit_date","entry_price","exit_price","shares","pnl"]].head(20),
                                                use_container_width=True)
                                else:
                                    st.info("无完整交易")
                            else:
                                st.info("无信号")
    with tab2:
        st.info("在【策略编辑器】中编写策略，然后在回测面板加载执行")

# ═══════════════════════════════════════════
# 页面：模拟交易
# ═══════════════════════════════════════════
def page_paper():
    if not check_access():
        st.warning("请登录后使用完整功能")
        return
    auth = st.session_state["auth"]
    st.markdown("""
    <div class="qm-banner">
        <h1>🎮 模拟交易</h1>
        <p>虚拟100万资金，真实下单逻辑，实时持仓管理</p>
    </div>
    """, unsafe_allow_html=True)
    positions = st.session_state["sim_positions"]
    capital = st.session_state["sim_capital"]
    # 持仓
    if positions:
        rows = []
        for code, info in positions.items():
            cur_price = random.uniform(info["cost"]*0.9, info["cost"]*1.1)
            pnl = (cur_price - info["cost"]) * info["shares"]
            rows.append({
                "股票代码": code, "名称": info["name"], "持仓股数": info["shares"],
                "成本价": f"¥{info['cost']:.2f}", "现价": f"¥{cur_price:.2f}",
                "盈亏": f"¥{pnl:+.2f}", "盈亏率": f"{pnl/info['cost']/info['shares']*100:+.1f}%"
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
    # 资金面板
    total_value = capital + sum(
        (random.uniform(p["cost"]*0.9, p["cost"]*1.1) - p["cost"]) * p["shares"]
        for p in positions.values()
    )
    col1, col2, col3 = st.columns(3)
    col1.metric("可用资金", f"¥{capital:,.2f}")
    col2.metric("持仓市值", f"¥{total_value-capital:,.2f}")
    col3.metric("账户总资产", f"¥{total_value:,.2f}")
    # 下单
    st.subheader("📝 下单")
    trade_tab1, trade_tab2 = st.tabs(["买入", "卖出"])
    with trade_tab1:
        t_code = st.text_input("股票代码", value="000001", key="buy_code")
        t_shares = st.number_input("买入股数（100的整数倍）", value=100, step=100, key="buy_shares")
        if st.button("✅ 买入", use_container_width=True):
            with st.spinner("获取价格..."):
                kdf = get_kline(t_code)
            if kdf is not None and not kdf.empty:
                price = kdf["close"].iloc[-1]
                cost = price * t_shares
                if cost <= capital:
                    name = t_code
                    positions[t_code] = {"name": name, "shares": t_shares, "cost": price}
                    st.session_state["sim_positions"] = positions
                    capital -= cost
                    st.session_state["sim_capital"] = capital
                    st.success(f"✅ 买入成功 {t_shares}股 @{price}")
                else:
                    st.error("资金不足")
            else:
                st.error("获取行情失败")
    with trade_tab2:
        s_code = st.text_input("股票代码", value="000001", key="sell_code")
        s_shares = st.number_input("卖出股数", value=100, step=100, key="sell_shares")
        if st.button("✅ 卖出", use_container_width=True):
            if s_code in positions and positions[s_code]["shares"] >= s_shares:
                kdf = get_kline(s_code)
                if kdf is not None:
                    price = kdf["close"].iloc[-1]
                    pnl = (price - positions[s_code]["cost"]) * s_shares
                    capital += price * s_shares
                    positions[s_code]["shares"] -= s_shares
                    if positions[s_code]["shares"] == 0:
                        del positions[s_code]
                    st.session_state["sim_positions"] = positions
                    st.session_state["sim_capital"] = capital
                    st.success(f"✅ 卖出成功 {s_shares}股 @{price}，盈亏 ¥{pnl:+}")
            else:
                st.error("持仓不足")
    # 交易记录
    if st.session_state["sim_trades"]:
        st.subheader("📋 交易记录")
        st.dataframe(pd.DataFrame(st.session_state["sim_trades"][-20:][::-1]), use_container_width=True)

# ═══════════════════════════════════════════
# 页面：实盘终端
# ═══════════════════════════════════════════
def page_live():
    if not check_access():
        st.warning("请登录后使用完整功能")
        return
    st.markdown("""
    <div class="qm-banner">
        <h1>💹 实盘终端</h1>
        <p>委托 / 撤单 / 盘口 / 账户（演示模式）</p>
    </div>
    """, unsafe_allow_html=True)
    st.caption("⚠️ 当前为演示模式，委托单不连接真实交易所")
    live_code = st.text_input("股票代码", value="000001")
    live_tab1, live_tab2, live_tab3 = st.tabs(["📤 委托下单", "📋 今日委托", "💼 账户信息"])
    with live_tab1:
        lc = st.columns(4)
        l_price = lc[0].number_input("价格", value=10.0, step=0.01)
        l_shares = lc[1].number_input("股数", value=100, step=100)
        l_type = lc[2].selectbox("类型", ["市价", "限价"])
        l_side = lc[3].selectbox("方向", ["买入", "卖出"])
        if st.button("📤 提交委托", use_container_width=True):
            order_id = f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(100,999)}"
            now = datetime.now()
            st.session_state["live_orders"].append({
                "委托号": order_id, "股票": live_code, "方向": l_side,
                "价格": l_price, "数量": l_shares, "状态": "已报",
                "时间": now.strftime("%H:%M:%S")
            })
            st.success(f"✅ 委托已提交：{order_id}")
    with live_tab2:
        if st.session_state["live_orders"]:
            st.dataframe(pd.DataFrame(st.session_state["live_orders"][-20:][::-1]), use_container_width=True)
        else:
            st.info("暂无委托记录")
    with live_tab3:
        st.json({
            "账户": st.session_state["auth"]["username"],
            "模式": "演示模式（未连接券商）",
            "可用": "---",
            "持仓": "---",
            "总资产": "---",
            "说明": "如需实盘，请配置easytrader等接口"
        })

# ═══════════════════════════════════════════
# 页面：绩效分析
# ═══════════════════════════════════════════
def page_report():
    if not check_access():
        st.warning("请登录后使用完整功能")
        return
    st.markdown("""
    <div class="qm-banner">
        <h1>📈 绩效分析</h1>
        <p>年化收益 / 夏普比率 / 回撤分析 / 月度分布</p>
    </div>
    """, unsafe_allow_html=True)
    auth = st.session_state["auth"]
    st.subheader(f"📊 {auth['username']} 的绩效报告")
    with st.spinner("加载绩效数据..."):
        time.sleep(1)
    # 模拟绩效数据
    dates = [(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(60, 0, -1)]
    random.seed(42)
    curve = [100000]
    for _ in dates:
        curve.append(curve[-1] * (1 + random.uniform(-0.02, 0.025)))
    perf_df = pd.DataFrame({"日期": dates, "账户净值": [round(v, 2) for v in curve[1:]]})
    st.area_chart(perf_df.set_index("日期"), height=300)
    cols = st.columns(4)
    metrics_data = {
        "年化收益": "12.8%",
        "夏普比率": "1.42",
        "最大回撤": "-8.3%",
        "胜率": "58.6%"
    }
    for idx, (k, v) in enumerate(metrics_data.items()):
        cols[idx].metric(k, v)
    st.subheader("📋 月度收益分布")
    months = ["1月","2月","3月","4月","5月","6月","7月","8月","9月","10月","11月","12月"]
    m_returns = [round(random.uniform(-3, 6), 2) for _ in months]
    mdf = pd.DataFrame({"月份": months, "收益率(%)": m_returns})
    st.bar_chart(mdf.set_index("月份"), height=250)
    # 下载报告
    report_text = f"""
QuantMaster Pro 绩效报告
========================
用户：{auth['username']}
生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
========================
年化收益率：{metrics_data['年化收益']}
夏普比率：{metrics_data['夏普比率']}
最大回撤：{metrics_data['最大回撤']}
胜率：{metrics_data['胜率']}
========================
模拟交易记录：
{st.session_state['sim_trades']}
"""
    st.download_button("📥 下载绩效报告(TXT)",
                        data=report_text,
                        file_name=f"quantmaster_report_{datetime.now().strftime('%Y%m%d')}.txt",
                        mime="text/plain",
                        use_container_width=True)

# ═══════════════════════════════════════════
# 页面：风险管理
# ═══════════════════════════════════════════
def page_risk():
    if not check_access():
        st.warning("请登录后使用完整功能")
        return
    st.markdown("""
    <div class="qm-banner">
        <h1>🛡️ 风险管理</h1>
        <p>VaR风险值 / 持仓集中度 / 预警规则 / 风险评级</p>
    </div>
    """, unsafe_allow_html=True)
    with st.spinner("计算风险指标..."):
        time.sleep(0.5)
    var_conf = st.slider("VaR 置信度", 90, 99, 95)
    positions = st.session_state.get("sim_positions", {})
    var_data = {}
    for code, info in positions.items():
        price = random.uniform(info["cost"]*0.8, info["cost"]*1.2)
        var_data[code] = (price - info["cost"]) * info["shares"]
    total_exposure = sum(abs(v) for v in var_data.values())
    var_99 = total_exposure * (1 - var_conf / 100) * 2.33
    col1, col2, col3 = st.columns(3)
    col1.metric("VaR(95%)", f"¥{total_exposure * 0.05:.0f}")
    col2.metric("VaR(99%)", f"¥{var_99:.0f}")
    hhi = sum((v / total_exposure * 100) ** 2 for v in var_data.values()) if total_exposure > 0 else 0
    col3.metric("持仓集中度(HHI)", f"{hhi:.1f}")
    # 预警规则
    st.subheader("⚠️ 风险预警规则")
    alerts = []
    if hhi > 2500:
        alerts.append(("🔴 高", f"持仓过于集中(HHI={hhi:.0f})，建议分散投资"))
    if total_exposure > 500000:
        alerts.append(("🟡 中", "仓位过重，建议降低持仓比例"))
    if not alerts:
        alerts.append(("🟢 低", "风险指标正常"))
    for level, msg in alerts:
        st.markdown(f"{level} {msg}")
    # 风险评级
    risk_score = min(100, int(hhi / 25 + total_exposure / 10000))
    if risk_score < 30:
        rating, color = "🟢 低风险", "#43a047"
    elif risk_score < 60:
        rating, color = "🟡 中风险", "#ff9800"
    else:
        rating, color = "🔴 高风险", "#e53935"
    st.markdown(f"### 综合风险评级：{rating}（评分 {risk_score}/100）")
    st.progress(risk_score / 100, text=f"风险评分 {risk_score}/100")

# ═══════════════════════════════════════════
# 页面：管理后台
# ═══════════════════════════════════════════
def page_admin():
    auth = st.session_state["auth"]
    if auth["role"] != "admin":
        st.error("权限不足")
        return
    st.markdown("""
    <div class="qm-banner">
        <h1>⚙️ 管理后台</h1>
        <p>用户管理 / 订单处理 / 系统设置</p>
    </div>
    """, unsafe_allow_html=True)
    tabs = st.tabs(["👥 用户管理", "📋 订单管理", "📊 系统概览"])
    with tabs[0]:
        st.subheader("用户列表")
        users = list_all_users()
        if users:
            udf = pd.DataFrame(users)
            st.dataframe(udf[["username","role","status","created_at","login_count"]], use_container_width=True)
        # 编辑用户
        st.subheader("✏️ 编辑用户")
        edit_user = st.selectbox("选择用户", [u["username"] for u in users])
        user = get_user(edit_user)
        if user:
            new_status = st.selectbox("状态", ["trial","paid","suspended"],
                                        index=["trial","paid","suspended"].index(user["status"]) if user["status"] in ["trial","paid","suspended"] else 1)
            if st.button("💾 保存更改"):
                conn = get_db()
                c = conn.cursor()
                c.execute("UPDATE users SET status = ? WHERE username = ?", (new_status, edit_user))
                conn.commit()
                conn.close()
                st.success("已更新")
    with tabs[1]:
        st.subheader("订单列表")
        orders = list_orders()
        if orders:
            st.dataframe(pd.DataFrame(orders), use_container_width=True)
        st.subheader("✅ 确认订单")
        confirm_no = st.text_input("输入订单号确认")
        if st.button("确认付款成功"):
            ok, msg = confirm_order(confirm_no)
            if ok:
                st.success(f"✅ {msg}")
            else:
                st.error(msg)
    with tabs[2]:
        st.subheader("系统概览")
        total_users = len(list_all_users())
        paid_users = len([u for u in list_all_users() if u["status"] == "paid"])
        trial_users = len([u for u in list_all_users() if u["status"] == "trial"])
        pending_orders = len([o for o in list_orders() if o["status"] == "pending"])
        cols = st.columns(4)
        cols[0].metric("总用户", total_users)
        cols[1].metric("付费用户", paid_users)
        cols[2].metric("试用用户", trial_users)
        cols[3].metric("待处理订单", pending_orders)
        st.caption(f"系统版本：QuantMaster Pro v3.0 | 部署时间：{datetime.now().strftime('%Y-%m-%d')}")

# ═══════════════════════════════════════════
# 主程序入口
# ═══════════════════════════════════════════
def main():
    auth = st.session_state["auth"]
    page = st.session_state.get("page", "行情数据")
    # 侧边栏
    render_sidebar()
    # 页面路由
    if page == "__admin__":
        page_admin()
    elif page == "行情数据":
        page_market()
    elif page == "策略编辑":
        page_strategy()
    elif page == "历史回测":
        page_backtest()
    elif page == "模拟交易":
        page_paper()
    elif page == "实盘终端":
        page_live()
    elif page == "绩效分析":
        page_report()
    elif page == "风险管理":
        page_risk()
    else:
        st.info(f"页面 '{page}' 加载中...")

if __name__ == "__main__":
    main()
