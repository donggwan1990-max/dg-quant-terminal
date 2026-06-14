import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# =================================================================
# 🏢 1. WALL STREET MIDNIGHT PREMIUM UI 테마 정의
# =================================================================
st.set_page_config(page_title="DG MULTI-QUANT MASTER TERMINAL", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0A0E17 !important; color: #E2E8F0 !important; }
    .main { background-color: #0A0E17 !important; }
    header[data-testid="stHeader"] { background-color: #0A0E17 !important; }
    h1, h2, h3, h4 { color: #FFFFFF !important; font-weight: 800; letter-spacing: -0.8px; font-family: 'Segoe UI', Roboto, sans-serif; }
    div[data-testid="stMetric"] { background-color: #111625 !important; border: 1px solid #1F293D !important; padding: 24px !important; border-radius: 6px !important; }
    div[data-testid="stMetricLabel"] { color: #8494A8 !important; font-size: 12px !important; text-transform: uppercase; font-weight: 700; letter-spacing: 0.5px; }
    div[data-testid="stMetricValue"] { color: #00E5FF !important; font-size: 26px !important; font-weight: 800; font-family: 'Courier New', Courier, monospace; }
    .stTabs [data-baseweb="tab-list"] { gap: 12px; background-color: #0A0E17; }
    .stTabs [data-baseweb="tab"] { background-color: #111625; border: 1px solid #1F293D; color: #94A3B8; padding: 14px 32px; border-radius: 4px 4px 0px 0px; font-weight: 700; font-size: 14px; }
    .stTabs [data-baseweb="tab"]:hover { color: #00E5FF; background-color: #161F33; }
    .stTabs [aria-selected="true"] { background-color: #1A233A !important; color: #00E5FF !important; border-bottom: 3px solid #00E5FF !important; }
    section[data-testid="stSidebar"] { background-color: #070B12 !important; border-right: 1px solid #1F293D; }
    </style>
""", unsafe_allow_html=True)

st.title("🎛️ DG MULTI-QUANT MASTER TERMINAL")
st.markdown("<p style='color:#4A5568; margin-top:-15px; font-weight:600;'>Institutional Asset Allocation & Real Estate True-ROI Engine</p>", unsafe_allow_html=True)
st.markdown("---")

# =================================================================
# 💾 2. 구글 스프레드시트 클라우드 DB 연결 엔진
# =================================================================
@st.cache_resource
def init_google_sheets():
    creds_info = st.secrets["gcp_service_account"]
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(creds_info, scopes=scope)
    return gspread.authorize(creds)

try:
    gc = init_google_sheets()
    sheet = gc.open("DG_QUANT_DB")
except Exception as e:
    st.error(f"❌ 구글 클라우드 DB 연결 실패: {e}")
    st.stop()

def get_cloud_df(worksheet_name, default_cols):
    try:
        ws = sheet.worksheet(worksheet_name)
        data = ws.get_all_records()
        return pd.DataFrame(data) if data else pd.DataFrame(columns=default_cols)
    except: return pd.DataFrame(columns=default_cols)

def save_cloud_df(worksheet_name, df):
    ws = sheet.worksheet(worksheet_name)
    ws.clear()
    df_filled = df.fillna("")
    ws.update([df_filled.columns.values.tolist()] + df_filled.values.tolist())

df_cash = get_cloud_df("cash", ["투자자", "예치금"])
df_portfolio = get_cloud_df("portfolio", ["투자자", "종목코드", "수량", "평단가", "매입환율"])
df_expenses = get_cloud_df("expenses", ["날짜", "유형", "분류", "내용", "금액"])
df_realestate = get_cloud_df("realestate", ["부동산명", "매입가", "현재평가액", "누적월세수입", "누적납부이자", "누적납부세금", "주택담보대출"])
df_debt = get_cloud_df("debt", ["부채명", "금액", "금리"])

# 3. 사이드바 제어 로직
st.sidebar.header("🕹️ TERMINAL SYSTEM INPUT")
op_category = st.sidebar.selectbox("전산 작업 분류 선택", ["📈 주식 포지션 (투자자 1~4)", "💰 투자 예치금 (투자자 1~4)", "💸 가계부 수입/지출 (공통)", "🏢 부동산 자산 등록 (공통)", "🚨 부채 원장 등록 (공통)"])

if op_category == "📈 주식 포지션 (투자자 1~4)":
    inv_target = st.sidebar.selectbox("🎯 대상 투자자", ["투자자 1", "투자자 2", "투자자 3", "투자자 4"])
    ticker = st.sidebar.text_input("종목 티커 (대문자)", "").upper().strip()
    qty = st.sidebar.number_input("보유 수량", min_value=0.0, step=1.0)
    price = st.sidebar.number_input("매수 평단가 ($)", min_value=0.0, step=0.01)
    fx_rate = st.sidebar.number_input("매입 당시 환율 (원/$)", value=1350.0)
    if st.sidebar.button("주식 포트폴리오 원장 동기화"):
        if ticker:
            mask = (df_portfolio['투자자'] == inv_target) & (df_portfolio['종목코드'] == ticker)
            if mask.any(): df_portfolio.loc[mask, ['수량', '평단가', '매입환율']] = [qty, price, fx_rate]
            else: df_portfolio = pd.concat([df_portfolio, pd.DataFrame([{"투자자": inv_target, "종목코드": ticker, "수량": qty, "평단가": price, "매입환율": fx_rate}])], ignore_index=True)
            save_cloud_df("portfolio", df_portfolio)
            st.rerun()

# 4. 퀀트 엔진
@st.cache_data(ttl=60)
def fetch_live_market_data(tickers):
    prices = {t: 0.0 for t in tickers}
    try:
        for t in tickers: prices[t] = yf.Ticker(t).history(period="1d")['Close'].iloc[-1]
    except: pass
    return prices

unique_tickers = df_portfolio['종목코드'].unique().tolist() if not df_portfolio.empty else []
live_prices = fetch_live_market_data(unique_tickers)

if not df_portfolio.empty:
    df_calc = df_portfolio.copy()
    df_calc['현재가($)'] = df_calc['종목코드'].map(live_prices)
    df_calc['투자원금(원)'] = pd.to_numeric(df_calc['수량']) * pd.to_numeric(df_calc['평단가']) * pd.to_numeric(df_calc['매입환율'])
    df_calc['평가가치(원)'] = pd.to_numeric(df_calc['수량']) * df_calc['현재가($)'] * 1350.0
    df_ticker_agg = df_calc.groupby('종목코드').agg({'수량': 'sum', '평가가치(원)': 'sum'}).reset_index()
else:
    df_ticker_agg = pd.DataFrame()

# 5. 최종 출력부 (에러 구문 완벽 제거)
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🏛️ 관제탑", "💸 가계부", "🏢 부동산", "🚨 부채", "📈 퀀트"])

with tab1:
    st.subheader("📊 TOTAL STOCK POSITION REPORT")
    # 기존 에러 코드인 .style.format({})를 삭제하고 순수 데이터프레임만 출력합니다.
    st.dataframe(df_ticker_agg, use_container_width=True)

with tab2: st.dataframe(df_expenses, use_container_width=True)
with tab3: st.dataframe(df_realestate, use_container_width=True)
with tab4: st.dataframe(df_debt, use_container_width=True)
with tab5: st.dataframe(df_cash, use_container_width=True)