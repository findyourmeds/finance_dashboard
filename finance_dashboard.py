import streamlit as st
import yfinance as yf
import pandas as pd
from openai import OpenAI
import io
from datetime import datetime, timedelta
import time
import requests
import numpy as np

# [LOG: 20260511_1115]
# 통합 금융 대시보드 v1.1
# 업데이트: 메뉴 이름에 강의 번호 추가 및 33, 35차시 통합

# --- 사전 정의 (번역 및 설정) ---
STOCK_COLUMNS_KR = {
    'Open': '시가', 'High': '고가', 'Low': '저가', 
    'Close': '종가', 'Adj Close': '수정종가', 'Volume': '거래량', 'Price': '가격'
}

FINANCIALS_KR = {
    'Total Revenue': '총수익(매출액)', 'Operating Revenue': '영업수익(매출액)', 'Cost Of Revenue': '매출원가',
    'Gross Profit': '매출총이익', 'Operating Expense': '영업비용', 'Operating Income': '영업이익',
    'Net Income': '당기순이익', 'EBIT': 'EBIT(세전영업이익)', 'EBITDA': 'EBITDA(상각전영업이익)',
    'Research And Development': '연구개발비', 'Selling General And Administration': '판매비와관리비',
    'Total Expenses': '총비용', 'Interest Expense': '이자비용', 'Interest Income': '이자수익',
    'Tax Provision': '법인세비용', 'Pretax Income': '세전이익', 'Net Income Common Stockholders': '보통주당기순이익',
    'Basic EPS': '기본주당순이익(EPS)', 'Diluted EPS': '희석주당순이익(EPS)',
    'Total Assets': '총자산', 'Current Assets': '유동자산', 'Total Non Current Assets': '비유동자산',
    'Cash And Cash Equivalents': '현금및현금성자산', 'Inventory': '재고자산',
    'Total Liabilities Net Minority Interest': '총부채', 'Current Liabilities': '유동부채',
    'Total Non Current Liabilities Net Minority Interest': '비유동부채',
    'Total Equity Gross Minority Interest': '총자본', 'Stockholders Equity': '자본총계',
    'Operating Cash Flow': '영업활동현금흐름', 'Investing Cash Flow': '투자활동현금흐름',
    'Financing Cash Flow': '재무활동현금흐름', 'Free Cash Flow': '잉여현금흐름',
    'Capital Expenditure': '자본적지출(CAPEX)'
}

COMPANY_NAMES_KR = {
    '300750.SZ': 'CATL', '1211.HK': 'BYD', '373220.KS': 'LG에너지솔루션',
    'AAPL': '애플', 'TSLA': '테슬라', 'GOOGL': '구글', 'MSFT': '마이크로소프트', 'NVDA': '엔비디아'
}

# --- 공통 함수 ---
def get_column_config(kr_dict):
    return {kr: st.column_config.Column(help=eng) for eng, kr in kr_dict.items()}

stock_col_config = get_column_config(STOCK_COLUMNS_KR)
fin_col_config = get_column_config(FINANCIALS_KR)

def get_ai_analysis(api_key, model, prompt):
    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "당신은 전문 금융 분석가입니다. 한국어로 답변하세요."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"AI 분석 중 오류 발생: {e}"

# --- 유틸리티 ---
@st.cache_data
def get_sp500_symbols():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    headers = {'User-Agent': 'Mozilla/5.0'}
    r = requests.get(url, headers=headers)
    table = pd.read_html(io.StringIO(r.text), match="Symbol")[0]
    return table["Symbol"].str.replace('.', '-', regex=False).tolist()

@st.cache_data
def get_nasdaq100_symbols():
    url = "https://en.wikipedia.org/wiki/Nasdaq-100"
    headers = {'User-Agent': 'Mozilla/5.0'}
    r = requests.get(url, headers=headers)
    for tbl in pd.read_html(io.StringIO(r.text)):
        col_names = [str(c).lower() for c in tbl.columns]
        if any("ticker" in c for c in col_names):
            target_col = tbl.columns[col_names.index([c for c in col_names if "ticker" in c][0])]
            return tbl[target_col].str.replace('.', '-', regex=False).tolist()
    return []

# --- 페이지 로직 ---
def show_stock_info():
    st.header("📈 주가 및 재무제표 조회 (19차시)")
    tickers_input = st.sidebar.text_input("티커 입력 (쉼표 구분)", value="TSLA, AAPL", key="tk_input")
    start_date = st.sidebar.date_input("시작일", value=datetime.now() - timedelta(days=365), key="s_date")
    end_date = st.sidebar.date_input("종료일", value=datetime.now(), key="e_date")
    
    tickers = [t.strip() for t in tickers_input.split(",") if t.strip()]
    if tickers:
        for tkr in tickers:
            company_name = COMPANY_NAMES_KR.get(tkr, tkr)
            st.subheader(f"🔍 {company_name} ({tkr})")
            tab1, tab2 = st.tabs(["주가 데이터", "재무제표"])
            with tab1:
                df = yf.download(tkr, start=start_date, end=end_date, progress=False)
                if not df.empty:
                    st.line_chart(df['Close'])
                    st.dataframe(df.rename(columns=STOCK_COLUMNS_KR).tail(20), column_config=stock_col_config, use_container_width=True)
            with tab2:
                tk = yf.Ticker(tkr)
                bs, inc, cf = tk.balance_sheet.T, tk.financials.T, tk.cashflow.T
                f_tab1, f_tab2, f_tab3 = st.tabs(["재무상태표", "손익계산서", "현금흐름표"])
                for f_df, f_tab in zip([bs, inc, cf], [f_tab1, f_tab2, f_tab3]):
                    with f_tab:
                        if not f_df.empty:
                            valid_cols = [c for c in f_df.columns if c in FINANCIALS_KR]
                            st.dataframe(f_df[valid_cols].rename(columns=FINANCIALS_KR), column_config=fin_col_config)
            st.divider()

def show_ai_analysis(api_key, model):
    st.header("🤖 AI 시장 분석 (21차시)")
    if not api_key: st.warning("API Key를 입력해 주세요."); return
    if st.button("실시간 글로벌 시황 요약"):
        with st.spinner("분석 중..."):
            indices = {"S&P 500": "^GSPC", "KOSPI": "^KS11", "나스닥": "^IXIC"}
            summary = ""
            for name, tkr in indices.items():
                data = yf.download(tkr, period="5d", progress=False)
                last, prev = data['Close'].iloc[-1].item(), data['Close'].iloc[-2].item()
                summary += f"{name}: {last:.2f} ({(last-prev)/prev*100:+.2f}%)\n"
            st.success(get_ai_analysis(api_key, model, f"시장 현황:\n{summary}\n\n위 데이터를 분석하고 투자 조언을 해줘."))

def show_screening():
    st.header("🔍 스마트 종목 필터링 (25차시)")
    col1, col2 = st.columns(2)
    with col1:
        growth_limit = st.number_input("최소 성장률 (%)", value=20)
        per_limit = st.number_input("최대 PER", value=30)
    with col2:
        peg_limit = st.number_input("최대 PEG", value=1.0)
        keyword = st.text_input("필수 키워드", value="battery")

    if st.button("스크리닝 시작"):
        with st.spinner("스캔 중..."):
            universe = sorted(set(get_sp500_symbols() + get_nasdaq100_symbols()))[:30]
            passed = []
            one_month = datetime.utcnow() - timedelta(days=30)
            for tkr in universe:
                try:
                    tic = yf.Ticker(tkr)
                    q_is = tic.quarterly_income_stmt
                    rev_row = next((idx for idx in q_is.index if "revenue" in idx.lower()), None)
                    op_row = next((idx for idx in q_is.index if "operating" in idx.lower() and "income" in idx.lower()), None)
                    if not rev_row or not op_row: continue
                    rev_g = (q_is.loc[rev_row].iloc[0] - q_is.loc[rev_row].iloc[1]) / abs(q_is.loc[rev_row].iloc[1])
                    op_g = (q_is.loc[op_row].iloc[0] - q_is.loc[op_row].iloc[1]) / abs(q_is.loc[op_row].iloc[1])
                    if rev_g < (growth_limit/100) or op_g < (growth_limit/100): continue
                    info = tic.info
                    if keyword.lower() not in (info.get("longBusinessSummary") or "").lower(): continue
                    pe, peg = info.get("trailingPE"), info.get("pegRatio")
                    if pe is None or peg is None or pe > per_limit or peg > peg_limit: continue
                    news = [n for n in (tic.news or []) if datetime.utcfromtimestamp(n.get("providerPublishTime", 0)) >= one_month]
                    if len(news) < 3: continue
                    passed.append({"Ticker": tkr, "매출성장": f"{rev_g*100:.1f}%", "PER": pe, "뉴스": len(news)})
                except: continue
            if passed: st.table(pd.DataFrame(passed))
            else: st.warning("조건 만족 종목 없음")

def show_api_intro():
    st.header("📡 API 자동매매 입문 (33차시)")
    tab1, tab2, tab3 = st.tabs(["개념 이해", "매매 시뮬레이터", "준비 체크리스트"])
    with tab1:
        st.info("**API 거래란?** 사람이 화면을 보고 주문하는 대신, 코드가 직접 증권사 서버와 데이터를 주고받으며 매매하는 방식입니다.")
        st.code("내 컴퓨터 --(주가요청)--> 증권사 서버\n내 컴퓨터 <--(현재가)---- 증권사 서버\n내 컴퓨터 --(매수주문)--> 증권사 서버", language="text")
    with tab2:
        buy_p = st.number_input("매수가", value=100.0)
        tp = st.slider("익절(%)", 1, 30, 10)
        sl = st.slider("손절(%)", 1, 30, 5)
        if st.button("시뮬레이션 실행"):
            prices = [buy_p * (1 + np.random.normal(0, 0.02)) for _ in range(20)]
            st.line_chart(prices)
            final = prices[-1]
            st.write(f"최종가: {final:.2f} | 결과: {'✅ 익절' if final >= buy_p*(1+tp/100) else '❌ 손절' if final <= buy_p*(1-sl/100) else '⌛ 유지'}")
    with tab3:
        for s in ["계좌 개설", "API 서비스 신청", "모의계좌 발급", "API Key 저장"]: st.checkbox(s)

def show_trading_algo():
    st.header("⚙️ 나만의 매매 알고리즘 (35차시)")
    st.write("투자 성향에 맞춘 자동 매매 봇의 파라미터를 설정합니다.")
    with st.expander("🛠️ 알고리즘 파라미터 설정", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.selectbox("대상 시장", ["국내 주식 (KOSPI/KOSDAQ)", "미국 주식 (NYSE/NASDAQ)"])
            st.number_input("종목당 최대 투자 금액 (원/$)", value=1000000)
        with col2:
            st.slider("익절 기준 (%)", 1, 50, 5)
            st.slider("손절 기준 (%)", 1, 50, 3)
        st.text_area("GPT에게 전달할 투자 전략 가이드", value="5분봉 기준 골든크로스 발생 시 매수, 장 종료 30분 전 전량 매도")
    st.info("💡 위 설정값들은 Google 스프레드시트와 연동되어 자동 매매 봇이 실시간으로 참조하게 됩니다.")

def main():
    st.set_page_config(page_title="통합 금융 대시보드", layout="wide")
    st.sidebar.title("📁 강의별 메뉴")
    menu = st.sidebar.radio("이동할 페이지", [
        "📈 주가 및 재무제표 (19차시)", 
        "🤖 AI 시장 분석 (21차시)", 
        "🔍 종목 필터링 (25차시)",
        "📡 API 자동매매 입문 (33차시)",
        "⚙️ 나만의 매매 알고리즘 (35차시)"
    ])
    st.sidebar.divider()
    api_key = st.sidebar.text_input("OpenAI API Key", type="password")
    model = st.sidebar.selectbox("모델", ["gpt-4o", "gpt-3.5-turbo"])
    
    if "19차시" in menu: show_stock_info()
    elif "21차시" in menu: show_ai_analysis(api_key, model)
    elif "25차시" in menu: show_screening()
    elif "33차시" in menu: show_api_intro()
    elif "35차시" in menu: show_trading_algo()

if __name__ == "__main__": main()
