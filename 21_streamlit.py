import streamlit as st
import yfinance as yf
import pandas as pd
from openai import OpenAI
import io

# [LOG: 20260511_0948]
# 21번 앱: GPT API를 활용한 프리미엄 투자 분석 대시보드
# 주요 기능: 주가 + 재무제표 + GPT API 뉴스/시황 요약 (한국어 로컬라이징 반영)

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
    '300750.SZ': 'CATL',
    '1211.HK': 'BYD',
    '373220.KS': 'LG에너지솔루션',
    'AAPL': '애플',
    'TSLA': '테슬라',
    'GOOGL': '구글',
    'MSFT': '마이크로소프트',
    'NVDA': '엔비디아'
}

def get_column_config(kr_dict):
    return {kr: st.column_config.Column(help=eng) for eng, kr in kr_dict.items()}

stock_col_config = get_column_config(STOCK_COLUMNS_KR)
fin_col_config = get_column_config(FINANCIALS_KR)

# --- 기능 함수 ---
def get_ai_analysis(api_key, model, prompt):
    """OpenAI API를 사용하여 분석/요약을 수행합니다."""
    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "당신은 전문 금융 분석가입니다. 데이터와 뉴스를 바탕으로 한국어로 통찰력 있는 요약을 제공하세요."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"AI 분석 중 오류 발생: {e}"

def get_company_info(ticker):
    tk = yf.Ticker(ticker)
    info = tk.info
    return {
        'sector': info.get('sector', '정보 없음'),
        'industry': info.get('industry', '정보 없음'),
        'summary': info.get('longBusinessSummary', '정보 없음')
    }

def get_stock_price(ticker, period="1y"):
    df = yf.download(ticker, period=period, auto_adjust=False, progress=False)
    try:
        df = df.rename(columns=STOCK_COLUMNS_KR)
        if isinstance(df.columns, pd.MultiIndex):
            df = df.rename(columns=STOCK_COLUMNS_KR, level=0)
    except: pass
    return df

def get_financial_statements(ticker):
    tk = yf.Ticker(ticker)
    bs, inc, cf = tk.balance_sheet.T, tk.financials.T, tk.cashflow.T
    for df in [bs, inc, cf]:
        if not df.empty:
            valid_cols = [c for c in df.columns if c in FINANCIALS_KR]
            # 인덱싱으로 새로운 DF를 만들어서 할당하는 것이 안전함
            df = df[valid_cols].rename(columns=FINANCIALS_KR)
    # 위 for문 내의 df 할당은 로컬 변수이므로 직접 수정 필요
    if not bs.empty: bs = bs[[c for c in bs.columns if c in FINANCIALS_KR]].rename(columns=FINANCIALS_KR)
    if not inc.empty: inc = inc[[c for c in inc.columns if c in FINANCIALS_KR]].rename(columns=FINANCIALS_KR)
    if not cf.empty: cf = cf[[c for c in cf.columns if c in FINANCIALS_KR]].rename(columns=FINANCIALS_KR)
    return bs, inc, cf

# --- 메인 앱 ---
def main():
    st.set_page_config(page_title="AI 투자 분석 대시보드 v2.1", layout="wide")
    st.title("🚀 프리미엄 AI 투자 분석 & 시장 요약")

    # 사이드바
    st.sidebar.header("🔑 AI & 조회 설정")
    api_key = st.sidebar.text_input("OpenAI API Key", type="password")
    model_option = st.sidebar.selectbox("GPT 모델", ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"])
    
    st.sidebar.divider()
    tickers_input = st.sidebar.text_input("티커 입력 (쉼표 구분)", value="TSLA, AAPL, NVDA")
    period = st.sidebar.selectbox("주가 기간", ["1mo", "3mo", "6mo", "1y", "5y"], index=3)

    if not api_key:
        st.sidebar.warning("API Key를 입력하면 AI 분석 기능을 사용할 수 있습니다.")

    # 자동 실행 버튼 효과 (기본 실행)
    st.sidebar.button("데이터 동기화/새로고침")

    tickers = [t.strip() for t in tickers_input.split(",") if t.strip()]

    if tickers:
        # 1. 글로벌 시장 시황 (AI 요약)
        st.header("🌍 글로벌 시장 시황 요약 (AI)")
        if st.button("실시간 시장 요약 실행") and api_key:
            with st.spinner("글로벌 시장 상황 분석 중..."):
                indices = {"S&P 500": "^GSPC", "KOSPI": "^KS11", "나스닥": "^IXIC", "환율(USD/KRW)": "USDKRW=X"}
                summary_info = ""
                for name, tkr in indices.items():
                    idx_data = yf.download(tkr, period="5d", progress=False)
                    if not idx_data.empty:
                        last_close = idx_data['Close'].iloc[-1].item()
                        prev_close = idx_data['Close'].iloc[-2].item()
                        change = ((last_close - prev_close) / prev_close) * 100
                        summary_info += f"{name}: {last_close:.2f} ({change:+.2f}%)\n"
                
                market_prompt = f"현재 주요 지수 및 환율 현황입니다:\n{summary_info}\n\n위 데이터를 바탕으로 현재 글로벌 증시의 분위기를 분석하고, 개인 투자자를 위한 간단한 대응 전략을 조언해줘."
                market_result = get_ai_analysis(api_key, model_option, market_prompt)
                st.success(market_result)
        elif not api_key:
            st.info("시황 요약을 보려면 API Key가 필요합니다.")

        st.divider()

        # 2. 개별 종목 상세 분석
        for tkr in tickers:
            company_name = COMPANY_NAMES_KR.get(tkr, tkr)
            display_name = f"{company_name} ({tkr})" if company_name != tkr else tkr
            
            st.subheader(f"🔍 {display_name} 상세 분석")
            
            # 기업 개요 & AI 분석
            col_info, col_ai = st.columns([1, 1])
            
            with col_info:
                try:
                    info = get_company_info(tkr)
                    st.write(f"**섹터:** {info['sector']} | **산업:** {info['industry']}")
                    with st.expander("사업 내용 요약 보기"):
                        st.write(info['summary'])
                except: st.error(f"{tkr} 정보를 가져올 수 없습니다.")

            with col_ai:
                if st.button(f"{company_name} AI 이슈 분석") and api_key:
                    with st.spinner("AI가 최신 뉴스를 분석 중..."):
                        tk = yf.Ticker(tkr)
                        news = tk.news[:3]
                        news_text = "\n".join([f"- {n['title']}" for n in news])
                        prompt = f"{display_name} 종목의 최근 뉴스입니다:\n{news_text}\n\n이 뉴스들을 종합하여 주요 이슈를 3줄로 요약하고, 투자 심리에 미칠 영향을 평가해줘."
                        analysis_result = get_ai_analysis(api_key, model_option, prompt)
                        st.info(analysis_result)

            # 주가 & 재무제표
            tab_price, tab_fin = st.tabs(["주가 차트", "재무제표"])
            
            with tab_price:
                price_df = get_stock_price(tkr, period)
                st.line_chart(price_df['종가'])
                st.dataframe(price_df.tail(20), column_config=stock_col_config, use_container_width=True)

            with tab_fin:
                bs, inc, cf = get_financial_statements(tkr)
                f_tab1, f_tab2, f_tab3 = st.tabs(["재무상태표", "손익계산서", "현금흐름표"])
                with f_tab1: st.dataframe(bs, column_config=fin_col_config)
                with f_tab2: st.dataframe(inc, column_config=fin_col_config)
                with f_tab3: st.dataframe(cf, column_config=fin_col_config)
            
            st.divider()

if __name__ == "__main__":
    main()
