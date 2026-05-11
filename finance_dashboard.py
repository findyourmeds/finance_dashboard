import streamlit as st
import yfinance as yf
import pandas as pd
from openai import OpenAI
import io
from datetime import datetime, timedelta
import time

# [LOG: 20260511_1036]
# 통합 금융 대시보드 v1.0
# 기능: 19차시(주가/재무), 21차시(AI분석), 25차시(종목 필터링) 통합

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

# --- 25차시용 유틸리티 ---
@st.cache_data
def get_sp500_symbols():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    table = pd.read_html(url, match="Symbol")[0]
    return table["Symbol"].tolist()

@st.cache_data
def get_nasdaq100_symbols():
    url = "https://en.wikipedia.org/wiki/Nasdaq-100"
    for tbl in pd.read_html(url):
        col_names = [str(c).lower() for c in tbl.columns]
        if any("ticker" in c for c in col_names):
            return tbl[tbl.columns[col_names.index("ticker")]].tolist()
    return []

# --- 페이지 로직 ---
def show_stock_info():
    st.header("📈 주가 및 재무제표 조회")
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
                    df_renamed = df.rename(columns=STOCK_COLUMNS_KR)
                    st.dataframe(df_renamed.tail(20), column_config=stock_col_config, use_container_width=True)
            
            with tab2:
                tk = yf.Ticker(tkr)
                bs, inc, cf = tk.balance_sheet.T, tk.financials.T, tk.cashflow.T
                f_tab1, f_tab2, f_tab3 = st.tabs(["재무상태표", "손익계산서", "현금흐름표"])
                for f_df, f_tab in zip([bs, inc, cf], [f_tab1, f_tab2, f_tab3]):
                    with f_tab:
                        if not f_df.empty:
                            valid_cols = [c for c in f_df.columns if c in FINANCIALS_KR]
                            f_df = f_df[valid_cols].rename(columns=FINANCIALS_KR)
                            st.dataframe(f_df, column_config=fin_col_config)
            st.divider()

def show_ai_analysis(api_key, model):
    st.header("🤖 AI 시장 분석")
    if not api_key:
        st.warning("OpenAI API Key를 입력해 주세요.")
        return

    if st.button("실시간 글로벌 시황 요약"):
        with st.spinner("분석 중..."):
            indices = {"S&P 500": "^GSPC", "KOSPI": "^KS11", "나스닥": "^IXIC"}
            summary = ""
            for name, tkr in indices.items():
                data = yf.download(tkr, period="5d", progress=False)
                last = data['Close'].iloc[-1].item()
                prev = data['Close'].iloc[-2].item()
                change = ((last - prev) / prev) * 100
                summary += f"{name}: {last:.2f} ({change:+.2f}%)\n"
            
            res = get_ai_analysis(api_key, model, f"시장 현황:\n{summary}\n\n위 데이터를 분석하고 투자 조언을 해줘.")
            st.success(res)

def show_screening():
    st.header("🔍 스마트 종목 필터링")
    st.info("S&P 500 및 Nasdaq-100 종목 중 특정 조건을 만족하는 기업을 찾습니다.")
    
    col1, col2 = st.columns(2)
    with col1:
        growth_limit = st.number_input("최소 성장률 (%)", value=20)
        per_limit = st.number_input("최대 PER", value=30)
    with col2:
        peg_limit = st.number_input("최대 PEG", value=1.0)
        keyword = st.text_input("필수 키워드 (예: battery, recycling)", value="battery")

    if st.button("스크리닝 시작"):
        with st.spinner("전체 종목을 스캔 중입니다... (시간이 다소 소요될 수 있습니다)"):
            sp500 = get_sp500_symbols()
            nasdaq100 = get_nasdaq100_symbols()
            universe = sorted(set(sp500 + nasdaq100))[:50] # 시연을 위해 50개로 제한
            
            passed = []
            one_month = datetime.utcnow() - timedelta(days=30)
            
            for tkr in universe:
                try:
                    tic = yf.Ticker(tkr)
                    
                    # 1. QoQ 매출 및 영업이익 성장 (20% 이상)
                    q_is = tic.quarterly_income_stmt
                    if q_is is None or q_is.shape[1] < 2: continue
                    
                    rev_row = next((idx for idx in q_is.index if "revenue" in idx.lower()), None)
                    op_row  = next((idx for idx in q_is.index if "operating" in idx.lower() and "income" in idx.lower()), None)
                    
                    if not rev_row or not op_row: continue
                    
                    rev = q_is.loc[rev_row].iloc[:2]
                    op_inc = q_is.loc[op_row].iloc[:2]
                    
                    rev_g = (rev.iloc[0] - rev.iloc[1]) / abs(rev.iloc[1])
                    op_g = (op_inc.iloc[0] - op_inc.iloc[1]) / abs(op_inc.iloc[1])
                    
                    if rev_g < (growth_limit / 100) or op_g < (growth_limit / 100): continue
                    
                    # 2. 키워드 필터링 (사업 요약에 키워드 포함 여부)
                    info = tic.info
                    summary = (info.get("longBusinessSummary") or "").lower()
                    if keyword.lower() not in summary: continue
                    
                    # 3. 투자 지표 필터링 (PER, PEG)
                    pe = info.get("trailingPE")
                    peg = info.get("pegRatio")
                    if pe is None or peg is None or pe > per_limit or peg > peg_limit: continue
                    
                    # 4. 최근 뉴스 개수 필터링 (최근 30일 뉴스 3개 이상)
                    news_items = tic.news or []
                    recent_news = [n for n in news_items if datetime.utcfromtimestamp(n.get("providerPublishTime", 0)) >= one_month]
                    if len(recent_news) < 3: continue
                    
                    passed.append({
                        "Ticker": tkr, 
                        "매출 성장(%)": round(rev_g*100, 1), 
                        "영업익 성장(%)": round(op_g*100, 1),
                        "PER": pe, 
                        "PEG": peg,
                        "뉴스(30일)": len(recent_news)
                    })
                    time.sleep(0.1)
                except: continue
            
            if passed:
                st.write(f"✅ {len(passed)}개의 종목이 발견되었습니다.")
                st.table(pd.DataFrame(passed))
            else:
                st.warning("조건을 만족하는 종목이 없습니다.")

# --- 메인 렌더링 ---
def main():
    st.set_page_config(page_title="통합 금융 대시보드", layout="wide")
    
    st.sidebar.title("📁 메뉴")
    menu = st.sidebar.radio("이동할 페이지", ["주가/재무제표", "AI 시장 분석", "종목 필터링"])
    
    st.sidebar.divider()
    st.sidebar.header("🔑 API 설정")
    api_key = st.sidebar.text_input("OpenAI API Key", type="password")
    model = st.sidebar.selectbox("모델", ["gpt-4o", "gpt-3.5-turbo"])
    
    if menu == "주가/재무제표":
        show_stock_info()
    elif menu == "AI 시장 분석":
        show_ai_analysis(api_key, model)
    elif menu == "종목 필터링":
        show_screening()

if __name__ == "__main__":
    main()
