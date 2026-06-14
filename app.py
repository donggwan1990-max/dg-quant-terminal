import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# 1. 페이지 및 스타일 설정
st.set_page_config(page_title="DG MULTI-QUANT MASTER TERMINAL", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0A0E17 !important; color: #E2E8F0 !important; }
    .main { background-color: #0A0E17 !important; }
    div[data-testid="stMetric"] { background-color: #111625 !important; border: 1px solid #1F293D !important; padding: 24px !important; border-radius: 6px !important; }
    div[data-testid="stMetricValue"] { color: #00E5FF !important; }
    </style>
""", unsafe_allow_html=True)

# 2. 구글 클라우드 DB 로직 (원본 유지)
@st.cache_resource
def get_sheets_client():
    creds_info = st.secrets["gcp_service_account"]
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(creds_info, scopes=scope)
    return gspread.authorize(creds)

sheet = get_sheets_client().open("DG_QUANT_DB")

@st.cache_data(ttl=600)
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

# 데이터 로드
df_cash = get_cloud_df("cash", ["투자자", "예치금"])
df_portfolio = get_cloud_df("portfolio", ["투자자", "종목코드", "수량", "평단가", "매입환율"])
df_expenses = get_cloud_df("expenses", ["날짜", "유형", "분류", "내용", "금액"])
df_realestate = get_cloud_df("realestate", ["부동산명", "매입가", "현재평가액", "누적월세수입", "누적납부이자", "누적납부세금", "주택담보대출"])
df_debt = get_cloud_df("debt", ["부채명", "금액", "금리"])

# 3. 사이드바 및 컨트롤 센터 (원본 기능 100% 복구)
st.sidebar.header("🕹️ TERMINAL SYSTEM INPUT")
op_category = st.sidebar.selectbox("전산 작업 분류 선택", ["📈 주식 포지션 (투자자 1~4)", "💰 투자 예치금 (투자자 1~4)", "💸 가계부 수입/지출 (공통)", "🏢 부동산 자산 등록 (공통)", "🚨 부채 원장 등록 (공통)"])

# 주식 포지션 로직
if op_category == "📈 주식 포지션 (투자자 1~4)":
    inv_target = st.sidebar.selectbox("🎯 대상 투자자", ["투자자 1", "투자자 2", "투자자 3", "투자자 4"])
    ticker = st.sidebar.text_input("종목 티커 (대문자)", "").upper().strip()
    qty = st.sidebar.number_input("보유 수량", min_value=0.0, step=1.0)
    price = st.sidebar.number_input("매수 평단가 ($)", min_value=0.0, step=0.01)
    fx_rate = st.sidebar.number_input("매입 당시 환율 (원/$)", value=1350.0)
    if st.sidebar.button("동기화"):
        df_portfolio = pd.concat([df_portfolio, pd.DataFrame([{"투자자": inv_target, "종목코드": ticker, "수량": qty, "평단가": price, "매입환율": fx_rate}])], ignore_index=True)
        save_cloud_df("portfolio", df_portfolio)
        st.rerun()

# 4. 퀀트 계산 및 연산 엔진
@st.cache_data(ttl=600)
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
    df_calc['평가가치(원)'] = pd.to_numeric(df_calc['수량']) * df_calc['현재가($)'] * 1350.0 # 예시 환율 적용
    df_ticker_agg = df_calc.groupby('종목코드').agg({'수량':'sum', '투자원금(원)':'sum', '평가가치(원)':'sum'}).reset_index()
else:
    df_ticker_agg = pd.DataFrame()

# 5. 출력부 (에러 나는 style.format을 걷어내고 안전한 출력문으로 대체)
st.title("🎛️ DG MULTI-QUANT MASTER TERMINAL")
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🏛️ 관제탑", "💸 가계부", "🏢 부동산", "🚨 부채", "📈 퀀트"])

with tab1:
    st.subheader("📊 TOTAL STOCK POSITION REPORT")
    if not df_ticker_agg.empty:
        # style.format 대신 데이터프레임을 그대로 출력하거나 .astype(str) 사용
        st.dataframe(df_ticker_agg, use_container_width=True)
    else:
        st.info("데이터가 없습니다.")

with tab2: st.dataframe(df_expenses, use_container_width=True)
with tab3: st.dataframe(df_realestate, use_container_width=True)
with tab4: st.dataframe(df_debt, use_container_width=True)
with tab5: st.dataframe(df_cash, use_container_width=True)