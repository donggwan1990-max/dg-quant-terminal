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
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    # secrets.toml 또는 클라우드 Secrets에서 인증 정보 로드
    creds_info = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_info, scopes=scope)
    return gspread.authorize(creds)

try:
    gc = init_google_sheets()
    # 생성하신 구글 시트 파일 이름과 정확히 일치해야 합니다.
    sheet = gc.open("DG_QUANT_DB")
except Exception as e:
    st.error(f"❌ 구글 클라우드 DB 연결 실패: secrets.toml 설정 또는 시트 공유 설정을 확인하세요. 에러내용: {e}")
    st.stop()

# 클라우드 데이터 읽기/쓰기 헬퍼 함수
def get_cloud_df(worksheet_name, default_cols):
    try:
        ws = sheet.worksheet(worksheet_name)
        data = ws.get_all_records()
        if not data:
            return pd.DataFrame(columns=default_cols)
        return pd.DataFrame(data)
    except gspread.exceptions.WorksheetNotFound:
        ws = sheet.add_worksheet(title=worksheet_name, rows="1000", cols="20")
        ws.append_row(default_cols)
        return pd.DataFrame(columns=default_cols)

def save_cloud_df(worksheet_name, df):
    ws = sheet.worksheet(worksheet_name)
    ws.clear()
    # 널값 체킹 및 문자열 변환 처리
    df_filled = df.fillna("")
    ws.update([df_filled.columns.values.tolist()] + df_filled.values.tolist())

# 실시간 클라우드 동기화 테이블 로드
df_cash = get_cloud_df("cash", ["투자자", "예치금"])
df_portfolio = get_cloud_df("portfolio", ["투자자", "종목코드", "수량", "평단가", "매입환율"])
df_expenses = get_cloud_df("expenses", ["날짜", "유형", "분류", "내용", "금액"])
df_realestate = get_cloud_df("realestate", ["부동산명", "매입가", "현재평가액", "누적월세수입", "누적납부이자", "누적납부세금", "주택담보대출"])
df_debt = get_cloud_df("debt", ["부채명", "금액", "금리"])

# 초기 예치금 데이터가 아예 없을 때 기본값 생성
if df_cash.empty:
    df_cash = pd.DataFrame([{"투자자": f"투자자 {i}", "예치금": 10000000} for i in range(1, 5)])
    save_cloud_df("cash", df_cash)

# =================================================================
# 📥 3. CONTROL CENTER PANEL (사이드바 메뉴)
# =================================================================
st.sidebar.header("🕹️ TERMINAL SYSTEM INPUT")
op_category = st.sidebar.selectbox("전산 작업 분류 선택", [
    "📈 주식 포지션 (투자자 1~4)", 
    "💰 투자 예치금 (투자자 1~4)", 
    "💸 가계부 수입/지출 (공통)", 
    "🏢 부동산 자산 등록 (공통)", 
    "🚨 부채 원장 등록 (공통)"
])

if op_category == "📈 주식 포지션 (투자자 1~4)":
    inv_target = st.sidebar.selectbox("🎯 대상 투자자", ["투자자 1", "투자자 2", "투자자 3", "투자자 4"])
    st.sidebar.subheader(f"[{inv_target}] 포지션 관리")
    ticker = st.sidebar.text_input("종목 티커 (대문자)", "").upper().strip()
    qty = st.sidebar.number_input("보유 수량", min_value=0.0, step=1.0)
    price = st.sidebar.number_input("매수 평단가 ($)", min_value=0.0, step=0.01)
    fx_rate = st.sidebar.number_input("매입 당시 환율 (원/$)", min_value=0.0, value=1350.0, step=1.0)
    
    if st.sidebar.button("주식 포트폴리오 원장 동기화"):
        if ticker:
            mask = (df_portfolio['투자자'] == inv_target) & (df_portfolio['종목코드'] == ticker)
            if mask.any(): df_portfolio.loc[mask, ['수량', '평단가', '매입환율']] = [qty, price, fx_rate]
            else: df_portfolio = pd.concat([df_portfolio, pd.DataFrame([{"투자자": inv_target, "종목코드": ticker, "수량": qty, "평단가": price, "매입환율": fx_rate}])], ignore_index=True)
            save_cloud_df("portfolio", df_portfolio)
            st.rerun()
            
    st.sidebar.markdown("---")
    active_stocks = df_portfolio[df_portfolio['투자자'] == inv_target]['종목코드'].tolist() if not df_portfolio.empty else []
    if active_stocks:
        del_ticker = st.sidebar.selectbox("청산(삭제) 종목 선택", active_stocks)
        if st.sidebar.button("포지션 완전히 삭제"):
            df_portfolio = df_portfolio[~((df_portfolio['투자자'] == inv_target) & (df_portfolio['종목코드'] == del_ticker))]
            save_cloud_df("portfolio", df_portfolio)
            st.rerun()

elif op_category == "💰 투자 예치금 (투자자 1~4)":
    inv_target = st.sidebar.selectbox("🎯 대상 투자자", ["투자자 1", "투자자 2", "투자자 3", "투자자 4"])
    st.sidebar.subheader(f"[{inv_target}] 예치금 제어")
    idx = df_cash[df_cash['투자자'] == inv_target].index[0]
    cash_type = st.sidebar.radio("원장 작업", ["예치금 증액(입금)", "예치금 인출", "잔액 강제 세팅"])
    cash_val = st.sidebar.number_input("변동 금액 (원)", min_value=0, step=50000)
    
    if st.sidebar.button("예치금 밸런스 업데이트"):
        if cash_type == "예치금 증액(입금)": df_cash.loc[idx, '예치금'] += cash_val
        elif cash_type == "예치금 인출": df_cash.loc[idx, '예치금'] = max(0, df_cash.loc[idx, '예치금'] - cash_val)
        else: df_cash.loc[idx, '예치금'] = cash_val
        save_cloud_df("cash", df_cash)
        st.rerun()

elif op_category == "💸 가계부 수입/지출 (공통)":
    st.sidebar.subheader("통합 자금 가계부 기록")
    io_type = st.sidebar.radio("자금 흐름", ["지출", "수입"])
    io_date = st.sidebar.date_input("날짜", datetime.now()).strftime('%Y-%m-%d')
    io_cat = st.sidebar.selectbox("분류", ["식비", "교통비", "고정비", "주거비", "차량유지비", "문화생활", "기타지출"] if io_type == "지출" else ["월급", "투자수익", "배당금", "기타수입"])
    io_desc = st.sidebar.text_input("상세 적요 내용", "")
    io_amt = st.sidebar.number_input("금액 (원)", min_value=0, step=1000)
    
    if st.sidebar.button("중앙 가계부 원장 입고"):
        if io_amt > 0:
            df_expenses = pd.concat([df_expenses, pd.DataFrame([{"날짜": io_date, "유형": io_type, "분류": io_cat, "내용": io_desc, "금액": io_amt}])], ignore_index=True)
            save_cloud_df("expenses", df_expenses)
            st.rerun()

elif op_category == "🏢 부동산 자산 등록 (공통)":
    st.sidebar.subheader("부동산 포트폴리오 관리")
    re_name = st.sidebar.text_input("부동산 자산 명칭", "예: 실거주 아파트, 오피스텔")
    re_buy_price = st.sidebar.number_input("최초 매입 가격 (원)", min_value=0, step=10000000)
    re_value = st.sidebar.number_input("현재 시세 평가액 (원)", min_value=0, step=10000000)
    re_mortgage = st.sidebar.number_input("연동 주택담보대출 잔액 (원)", min_value=0, step=1000000)
    st.sidebar.markdown("---")
    st.sidebar.caption("💡 수익/비용 내역 (누적액)")
    re_rent = st.sidebar.number_input("누적 월세 수입금액 (원)", min_value=0, step=100000)
    re_interest = st.sidebar.number_input("누적 납부 이자 (원)", min_value=0, step=100000)
    re_tax = st.sidebar.number_input("누적 납부 세금 (원)", min_value=0, step=100000)
    
    if st.sidebar.button("부동산 자산 대장에 기록"):
        if re_name and re_value > 0:
            if not df_realestate.empty and re_name in df_realestate['부동산명'].values: 
                df_realestate.loc[df_realestate['부동산명'] == re_name, ['매입가', '현재평가액', '누적월세수입', '누적납부이자', '누적납부세금', '주택담보대출']] = [re_buy_price, re_value, re_rent, re_interest, re_tax, re_mortgage]
            else: 
                new_re = pd.DataFrame([{"부동산명": re_name, "매입가": re_buy_price, "현재평가액": re_value, "누적월세수입": re_rent, "누적납부이자": re_interest, "누적납부세금": re_tax, "주택담보대출": re_mortgage}])
                df_realestate = pd.concat([df_realestate, new_re], ignore_index=True)
            save_cloud_df("realestate", df_realestate)
            st.rerun()
            
    st.sidebar.markdown("---")
    if not df_realestate.empty:
        del_re = st.sidebar.selectbox("매각(삭제) 부동산 선택", df_realestate['부동산명'].tolist())
        if st.sidebar.button("부동산 자산 대장에서 지우기"):
            df_realestate = df_realestate[df_realestate['부동산명'] != del_re]
            save_cloud_df("realestate", df_realestate)
            st.rerun()

elif op_category == "🚨 부채 원장 등록 (공통)":
    st.sidebar.subheader("여신 채무 리스크 등록")
    d_name = st.sidebar.text_input("부채/대출 이름 명칭", "")
    d_amt = st.sidebar.number_input("대출 잔액 원금 (원)", min_value=0, step=100000)
    d_rate = st.sidebar.number_input("계약 금리 (%)", min_value=0.0, max_value=100.0, step=0.1)
    
    if st.sidebar.button("부채 원장 파일 동기화"):
        if d_name and d_amt > 0:
            if not df_debt.empty and d_name in df_debt['부채명'].values: df_debt.loc[df_debt['부채명'] == d_name, ['금액', '금리']] = [d_amt, d_rate]
            else: df_debt = pd.concat([df_debt, pd.DataFrame([{"부채명": d_name, "금액": d_amt, "금리": d_rate}])], ignore_index=True)
            save_cloud_df("debt", df_debt)
            st.rerun()
            
    st.sidebar.markdown("---")
    if not df_debt.empty:
        del_debt = st.sidebar.selectbox("상환 완료 부채 계정 선택", df_debt['부채명'].tolist())
        if st.sidebar.button("부채 계정 삭제"):
            df_debt = df_debt[df_debt['부채명'] != del_debt]
            save_cloud_df("debt", df_debt)
            st.rerun()

# =================================================================
# 📈 4. QUANT CALCULATOR ENGINE
# =================================================================
@st.cache_data(ttl=60)
def fetch_live_market_data(tickers):
    prices = {}
    for t in tickers:
        try: prices[t] = yf.Ticker(t).history(period="1d")['Close'].iloc[-1]
        except: prices[t] = 0.0
    try: usd_krw = yf.Ticker("KRW=X").history(period="1d")['Close'].iloc[-1]
    except: usd_krw = 1350.0
    return prices, usd_krw

unique_tickers = df_portfolio['종목코드'].unique().tolist() if not df_portfolio.empty else []
live_prices, current_exchange_rate = fetch_live_market_data(unique_tickers)

if not df_portfolio.empty:
    df_calc = df_portfolio.copy()
    df_calc['현재환율'] = current_exchange_rate
    df_calc['현재가($)'] = df_calc['종목코드'].map(live_prices)
    
    df_calc['투자원금($)'] = pd.to_numeric(df_calc['수량']) * pd.to_numeric(df_calc['평단가'])
    df_calc['평가가치($)'] = pd.to_numeric(df_calc['수량']) * df_calc['현재가($)']
    df_calc['매매손익($)'] = df_calc['평가가치($)'] - df_calc['투자원금($)']
    
    df_calc['투자원금(원)'] = df_calc['투자원금($)'] * pd.to_numeric(df_calc['매입환율'])
    df_calc['평가가치(원)'] = df_calc['평가가치($)'] * df_calc['현재환율']
    
    df_calc['총평가손익(원)'] = df_calc['평가가치(원)'] - df_calc['투자원금(원)']
    df_calc['순수매매손익(원)'] = df_calc['매매손익($)'] * df_calc['현재환율']
    df_calc['환차손익(원)'] = df_calc['총평가손익(원)'] - df_calc['순수매매손익(원)']
    df_calc['수익률(%)'] = (df_calc['총평가손익(원)'] / df_calc['투자원금(원)'] * 100).round(2)
    
    df_ticker_agg = df_calc.groupby('종목코드').agg({
        '수량': 'sum', '투자원금(원)': 'sum', '평가가치(원)': 'sum',
        '총평가손익(원)': 'sum', '순수매매손익(원)': 'sum', '환차손익(원)': 'sum'
    }).reset_index()
    df_ticker_agg['종합수익률(%)'] = (df_ticker_agg['총평가손익(원)'] / df_ticker_agg['투자원금(원)'] * 100).round(2)
else:
    df_calc = pd.DataFrame()
    df_ticker_agg = pd.DataFrame()

grand_cash = pd.to_numeric(df_cash['예치금']).sum()
grand_stock = df_calc['평가가치(원)'].sum() if not df_calc.empty else 0
grand_realestate = pd.to_numeric(df_realestate['현재평가액']).sum() if not df_realestate.empty else 0

total_re_mortgage = pd.to_numeric(df_realestate['주택담보대출']).sum() if not df_realestate.empty else 0
grand_debt = (pd.to_numeric(df_debt['금액']).sum() if not df_debt.empty else 0) + total_re_mortgage

grand_assets = grand_cash + grand_stock + grand_realestate
grand_net_worth = grand_assets - grand_debt

grand_income = pd.to_numeric(df_expenses[df_expenses['유형'] == '수입']['금액']).sum() if not df_expenses.empty else 0
grand_spent = pd.to_numeric(df_expenses[df_expenses['유형'] == '지출']['금액']).sum() if not df_expenses.empty else 0

grand_invested_krw = df_calc['투자원금(원)'].sum() if not df_calc.empty else 0
grand_stock_profit_krw = df_calc['총평가손익(원)'].sum() if not df_calc.empty else 0

# =================================================================
# 🎛️ 5-TABS ADVANCED MANAGEMENT ARCHITECTURE
# =================================================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🏛️ 1. 종합 관제탑 (Master Terminal)", 
    "💸 2. 월별 수입·지출 가계부 시트", 
    "🏢 3. 부동산 자산 센터", 
    "🚨 4. 리스크 부채 제어 센터", 
    "📈 5. 글로벌 퀀트 총괄 분석"
])

# -----------------------------------------------------------------
# 🏛️ [Tab 1] 종합 관제탑 (Master Terminal)
# -----------------------------------------------------------------
with tab1:
    st.subheader("🏛️ CENTRAL CAPITAL REAL-TIME MONITOR")
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("🎯 NET WORTH (진짜 순자산)", f"{grand_net_worth:,.0f} 원")
    m2.metric("💳 TOTAL ASSETS (총 자산 가치)", f"{grand_assets:,.0f} 원")
    m3.metric("🚨 TOTAL DEBT (전체 부채 규모)", f"{grand_debt:,.0f} 원")
    m4.metric("⚖️ MON-CASHFLOW (당월 수입/지출)", f"{grand_income - grand_spent:+,.0f} 원", f"수입 {grand_income:,.0f} / 지출 {grand_spent:,.0f}")
    st.markdown("---")
    
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("💰 통합 운용 예치금 총액", f"{grand_cash:,.0f} 원")
    s2.metric("📈 통합 글로벌 주식 평가액", f"{grand_stock:,.0f} 원", f"{grand_stock_profit_krw:+,.0f} 원")
    s3.metric("🏢 부동산 포트폴리오 총액", f"{grand_realestate:,.0f} 원")
    s4.metric("📊 총 주식 투자 원금", f"{grand_invested_krw:,.0f} 원")
    st.markdown("---")
    
    st.markdown("### 📊 TOTAL STOCK POSITION REPORT (전체 계좌 통합 종목별 손익 실적현황)")
    if not df_ticker_agg.empty:
        st.dataframe(df_ticker_agg.style.format({
            '수량': '{:,.1f}', '투자원금(원)': '{:,.0f} 원', '평가가치(원)': '{:,.0f} 원',
            '총평가손익(원)': '{:+,.0f} 원', '순수매매손익(원)': '{:+,.0f} 원', '환차손익(원)': '{:+,.0f} 원',
            '종합수익률(%)': '{:+.2f}%'
        }), use_container_width=True)
    else:
        st.info("사이드바를 통해 주식 포지션을 등록하시면 통합 수익 분석표가 표기됩니다.")
    st.markdown("---")

    c_left, c_right = st.columns(2)
    with c_left:
        st.markdown("#### 💎 TOTAL PORTFOLIO ALLOCATION (전체 자산 자본 배분 비중)")
        mix_df = pd.DataFrame([
            {"자산군": "가용 예치금", "금액": grand_cash},
            {"자산군": "글로벌 주식 자산", "금액": grand_stock},
            {"자산군": "부동산 자산", "금액": grand_realestate}
        ])
        fig_m_pie = px.pie(mix_df, values='금액', names='자산군', hole=0.5, color_discrete_sequence=['#00E5FF', '#0072FF', '#7F00FF'])
        fig_m_pie.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='#FFF')
        st.plotly_chart(fig_m_pie, use_container_width=True)
        
    with c_right:
        st.markdown("#### 💱 MACRO INDEX & LEVERAGE SPEED")
        st.info(f"💵 **실시간 야후 파이낸스 기준 환율:** 현재 매칭 시장가는 `{current_exchange_rate:,.2f} 원/$` 입니다.")
        leverage_ratio = (grand_debt / grand_assets * 100) if grand_assets > 0 else 0
        st.markdown(f"""
        * **전체 자산 대비 금융 대출(레버리지) 비중:** `{leverage_ratio:.2f} %`
        * **전체 자산 중 글로벌 주식 자산 포지션 비중:** `{grand_stock / grand_assets * 100 if grand_assets > 0 else 0:.1f} %`
        * **전체 자산 중 리얼 에스테이트(부동산) 비중:** `{grand_realestate / grand_assets * 100 if grand_assets > 0 else 0:.1f} %`
        """)

# -----------------------------------------------------------------
# 💸 [Tab 2] 월별 수입·지출 가계부 시트
# -----------------------------------------------------------------
with tab2:
    st.subheader("💸 CASH FLOW GRID SHEET SYSTEM")
    f_left, f_right = st.columns([1, 1])
    with f_left:
        st.markdown("#### 📊 당월 수입 vs 지출 대차 밸런스")
        if not df_expenses.empty:
            summary_df = df_expenses.groupby("유형")["금액"].sum().reset_index()
            fig_f_bar = px.bar(summary_df, x="유형", y="금액", color="유형", color_discrete_map={"수입": "#00E676", "지출": "#FF1744"}, text_auto=',.0f')
            fig_f_bar.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#FFF')
            st.plotly_chart(fig_f_bar, use_container_width=True)
    with f_right:
        st.markdown("#### 🛍️ 카테고리별 누적 지출 비중 분석")
        if not df_expenses.empty:
            df_spent_only = df_expenses[df_expenses['유형'] == '지출']
            if not df_spent_only.empty:
                cat_df = df_spent_only.groupby("분류")["금액"].sum().reset_index()
                fig_cat_pie = px.pie(cat_df, values='금액', names='분류', color_discrete_sequence=px.colors.sequential.YlOrRd_r)
                fig_cat_pie.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='#FFF')
                st.plotly_chart(fig_cat_pie, use_container_width=True)
    st.markdown("#### 📋 CENTRAL LEDGER MATRIX (통합 가계 재무 원장 격자 시트)")
    if not df_expenses.empty:
        st.dataframe(df_expenses.sort_values(by="날짜", ascending=False), use_container_width=True)

# -----------------------------------------------------------------
# 🏢 [Tab 3] 부동산 자산 센터
# -----------------------------------------------------------------
with tab3:
    st.subheader("🏢 REAL ESTATE TRUE-ROI & MORTGAGE WATCH")
    
    if not df_realestate.empty:
        df_re_calc = df_realestate.copy()
        df_re_calc['매입가'] = pd.to_numeric(df_re_calc['매입가'])
        df_re_calc['현재평가액'] = pd.to_numeric(df_re_calc['현재평가액'])
        df_re_calc['주택담보대출'] = pd.to_numeric(df_re_calc['주택담보대출'])
        df_re_calc['누적월세수입'] = pd.to_numeric(df_re_calc['누적월세수입'])
        df_re_calc['누적납부이자'] = pd.to_numeric(df_re_calc['누적납부이자'])
        df_re_calc['누적납부세금'] = pd.to_numeric(df_re_calc['누적납부세금'])
        
        df_re_calc['자본차익(시세차익)'] = df_re_calc['현재평가액'] - df_re_calc['매입가']
        df_re_calc['종합순수익'] = df_re_calc['자본차익(시세차익)'] + df_re_calc['누적월세수입'] - df_re_calc['누적납부이자'] - df_re_calc['누적납부세금']
        df_re_calc['종합수익률(%)'] = df_re_calc.apply(lambda row: (row['종합순수익'] / row['매입가'] * 100) if row['매입가'] > 0 else 0, axis=1).round(2)
        df_re_calc['순자산지분(원)'] = df_re_calc['현재평가액'] - df_re_calc['주택담보대출']
        
        re_total_buy = df_re_calc['매입가'].sum()
        re_total_eval = df_re_calc['현재평가액'].sum()
        re_total_mortgage = df_re_calc['주택담보대출'].sum()
        re_total_profit = df_re_calc['종합순수익'].sum()
        re_total_yield = (re_total_profit / re_total_buy * 100) if re_total_buy > 0 else 0
        
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("총 부동산 시세 평가액", f"{re_total_eval:,.0f} 원")
        r2.metric("총 주택담보대출 잔액", f"{re_total_mortgage:,.0f} 원", delta=f"실제 순지분: {re_total_eval - re_total_mortgage:,.0f} 원")
        r3.metric("🏢 부동산 포트폴리오 종합 순수익", f"{re_total_profit:+,.0f} 원", f"종합 ROI: {re_total_yield:+.2f}%")
        r4.metric("누적 순 현금흐름 (월세-이자-세금)", f"{(df_re_calc['누적월세수입'].sum() - df_re_calc['누적납부이자'].sum() - df_re_calc['누적납부세금'].sum()):+,.0f} 원")
        
        st.markdown("---")
        r_left, r_right = st.columns([1, 2])
        with r_left:
            st.markdown("#### 📊 부동산 물권별 실제 순자산 지분 규모")
            fig_re_bar = px.bar(df_re_calc, x="부동산명", y="순자산지분(원)", text_auto=',.0f', color="부동산명", color_discrete_sequence=px.colors.sequential.Agsunset)
            fig_re_bar.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#FFF')
            st.plotly_chart(fig_re_bar, use_container_width=True)
            
        with r_right:
            st.markdown("#### 📋 보유 자산 및 주택담보대출 정밀 ROI 투자 대장")
            st.dataframe(df_re_calc.style.format({
                '매입가': '{:,.0f} 원', '현재평가액': '{:,.0f} 원', '주택담보대출': '{:,.0f} 원',
                '순자산지분(원)': '{:,.0f} 원', '누적월세수입': '{:+,.0f} 원', '누적납부이자': '{:,.0f} 원',
                '누적납부세금': '{:,.0f} 원', '자본차익(시세차익)': '{:+,.0f} 원', '종합순수익': '{:+,.0f} 원', '종합수익률(%)': '{:+.2f}%'
            }), use_container_width=True)

# -----------------------------------------------------------------
# 🚨 [Tab 4] 리스크 부채 제어 센터
# -----------------------------------------------------------------
with tab4:
    st.subheader("🚨 REGULATORY LIABILITY RISK MANAGEMENT")
    
    d1, d2, d3 = st.columns(3)
    d1.metric("통합 총 부채액 (전체 레버리지)", f"{grand_debt:,.0f} 원")
    d1_general = pd.to_numeric(df_debt['금액']).sum() if not df_debt.empty else 0
    d2.metric("개인 신용 및 일반 대출 총액", f"{d1_general:,.0f} 원")
    d3.metric("부동산 주택담보대출 총액", f"{total_re_mortgage:,.0f} 원")
    st.markdown("---")

    if not df_debt.empty:
        d_left, d_right = st.columns(2)
        with d_left:
            st.markdown("#### 📉 신용/일반 금융권 여신 부채 익스포저 규모")
            fig_debt_bar = px.bar(df_debt, x="부채명", y="금액", text_auto=',.0f', color="부채명", color_discrete_sequence=px.colors.sequential.Purples_r)
            fig_debt_bar.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#FFF')
            st.plotly_chart(fig_debt_bar, use_container_width=True)
        with d_right:
            st.markdown("#### 📋 일반 금융 채무 약정 원장 상세")
            st.dataframe(df_debt.style.format({'금액': '{:,.0f} 원', '금리': '{:.2f} %'}), use_container_width=True)
            weighted_rate = ((pd.to_numeric(df_debt['금액']) * pd.to_numeric(df_debt['금리'])).sum() / d1_general).round(2) if d1_general > 0 else 0
            st.metric("📊 신용/일반 대출 가중 평균 금리 (WACC)", f"{weighted_rate} %")

# -----------------------------------------------------------------
# 📈 [Tab 5] 글로벌 퀀트 총괄 분석
# -----------------------------------------------------------------
with tab5:
    st.subheader("📈 GLOBAL SEGREGATED QUANT PORTFOLIO ANALYTICS")
    
    st.markdown("### 💰 INVESTOR CASH LIQUIDITY (4인 투자자 가용 예치금 통합 현황)")
    c_left_cash, c_right_cash = st.columns([1, 1])
    
    with c_left_cash:
        fig_cash_bar = px.bar(df_cash, x='예치금', y='투자자', orientation='h', text_auto=',.0f', color='투자자', color_discrete_sequence=['#00E5FF', '#0072FF', '#7F00FF', '#FF007F'])
        fig_cash_bar.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#FFF', xaxis_title="예치금 잔액 (원)", yaxis_title="")
        st.plotly_chart(fig_cash_bar, use_container_width=True)
        
    with c_right_cash:
        st.dataframe(df_cash.style.format({'예치금': '{:,.0f} 원'}), use_container_width=True)
    
    st.markdown("---")
    st.markdown("### 🔎 INDIVIDUAL PORTFOLIO ANALYSIS")
    view_inv = st.radio("포지션 정밀 관제 대상 선택", ["투자자 1", "투자자 2", "투자자 3", "투자자 4"], horizontal=True)
    st.markdown("---")
    
    inv_cash_val = int(df_cash[df_cash['투자자'] == view_inv]['예치금'].iloc[0])
    df_inv_stock = df_calc[df_calc['투자자'] == view_inv] if not df_calc.empty else pd.DataFrame()
    inv_stock_val = df_inv_stock['평가가치(원)'].sum() if not df_inv_stock.empty else 0
    
    i1, i2, i3 = st.columns(3)
    i1.metric(f"👤 [{view_inv}] 총 개인 운용 한도", f"{inv_cash_val + inv_stock_val:,.0f} 원")
    i2.metric("💵 배정 주식 가용 예치금", f"{inv_cash_val:,.0f} 원")
    i3.metric("📈 개인 보유 주식 평가액 총계", f"{inv_stock_val:,.0f} 원")
    st.markdown("---")
    
    st.markdown(f"#### 💻 [{view_inv}] 개인 계정별 매입/현재 환율 맵 및 3대 정밀 손익 원장")
    if not df_inv_stock.empty:
        df_inv_view = df_inv_stock[["종목코드", "수량", "평단가", "현재가($)", "매입환율", "현재환율", "투자원금(원)", "평가가치(원)", "순수매매손익(원)", "환차손익(원)", "총평가손익(원)", "수익률(%)"]]
        st.dataframe(df_inv_view.style.format({
            '수량': '{:,.1f}', '평단가': '${:,.2f}', '현재가($)': '${:,.2f}', '매입환율': '{:,.1f}원', '현재환율': '{:,.1f}원',
            '투자원금(원)': '{:,.0f} 원', '평가가치(원)': '{:,.0f} 원', '순수매매손익(원)': '{:+,.0f} 원', '환차손익(원)': '{:+,.0f} 원', '총평가손익(원)': '{:+,.0f} 원', '수익률(%)': '{:+.2f}%'
        }), use_container_width=True)
        
        st.markdown("#### 📊 개인 포지션별 손익 요인 다차원 바 다이어그램")
        df_melted = df_inv_stock.melt(id_vars=['종목코드'], value_vars=['순수매매손익(원)', '환차손익(원)'], var_name='손익구분', value_name='금액')
        fig_factor = px.bar(df_melted, x='종목코드', y='금액', color='손익구분', barmode='group', color_discrete_map={'순수매매손익(원)': '#00E5FF', '환차손익(원)': '#FF007F'})
        fig_factor.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='#FFF')
        st.plotly_chart(fig_factor, use_container_width=True)