import streamlit as st
import yfinance as yf
import pandas as pd
import io

# [LOG: 20260511_0907]
# 영어 항목들을 한국어로 바꾸기 위한 사전 선언
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

# [LOG: 20260511_0915]
# 컬럼 설정(툴팁) 자동 생성
def get_column_config(kr_dict):
    return {kr: st.column_config.Column(help=eng) for eng, kr in kr_dict.items()}

stock_col_config = get_column_config(STOCK_COLUMNS_KR)
fin_col_config = get_column_config(FINANCIALS_KR)

# [LOG: 20260511_0911]
# 티커를 알아보기 쉬운 한국어 기업명으로 변환하기 위한 사전
COMPANY_NAMES_KR = {
    '300750.SZ': 'CATL',
    '1211.HK': 'BYD',
    '373220.KS': 'LG에너지솔루션'
}

# [LOG: 20260511_0916]
def get_company_info(ticker):
    """티커의 기업 정보(섹터, 산업, 사업 요약)를 가져옵니다."""
    tk = yf.Ticker(ticker)
    info = tk.info
    sector = info.get('sector', '정보 없음')
    industry = info.get('industry', '정보 없음')
    summary = info.get('longBusinessSummary', '정보 없음')
    return sector, industry, summary

def get_stock_price(ticker, start_date, end_date):
    """단일 티커의 주가 데이터를 가져옵니다."""
    df = yf.download(ticker, start=start_date, end=end_date, auto_adjust=False, progress=False)
    
    # 주가 데이터의 영어 컬럼명을 한국어로 변경
    try:
        df = df.rename(columns=STOCK_COLUMNS_KR)
        # 최신 yfinance 버전에선 MultiIndex(예: Price, Ticker)를 사용할 수 있음
        if isinstance(df.columns, pd.MultiIndex):
            df = df.rename(columns=STOCK_COLUMNS_KR, level=0)
    except:
        pass
    return df

# [LOG: 20260511_0920]
def get_financial_statements(ticker):
    """단일 티커의 재무제표(재무상태표, 손익계산서, 현금흐름표)를 가져옵니다."""
    tk = yf.Ticker(ticker)
    bs = tk.balance_sheet.T
    inc = tk.financials.T
    cf = tk.cashflow.T
    
    # 1. 딕셔너리에 있는 필수 컬럼(영어)만 남기기
    # 2. 한국어로 이름 바꾸기 (나머지 자잘한 영어가 화면에 나오는 것을 방지)
    if not bs.empty:
        valid_cols = [c for c in bs.columns if c in FINANCIALS_KR]
        bs = bs[valid_cols].rename(columns=FINANCIALS_KR)
    if not inc.empty:
        valid_cols = [c for c in inc.columns if c in FINANCIALS_KR]
        inc = inc[valid_cols].rename(columns=FINANCIALS_KR)
    if not cf.empty:
        valid_cols = [c for c in cf.columns if c in FINANCIALS_KR]
        cf = cf[valid_cols].rename(columns=FINANCIALS_KR)
    
    return bs, inc, cf

# [LOG: 20260511_0905]
def main():
    st.title("주가 & 재무제표 조회 대시보드")
    
    st.sidebar.header("조회 설정")
    tickers_input = st.sidebar.text_input("티커 입력 (쉼표로 구분)", value="300750.SZ, 1211.HK, 373220.KS")
    start_date = st.sidebar.date_input("시작일", value=pd.to_datetime("2023-01-01"))
    end_date = st.sidebar.date_input("종료일", value=pd.to_datetime("2024-04-14"))
    
    # [LOG: 20260511_0923] 버튼 유지 및 조건문 제거하여 즉시 실행
    st.sidebar.button("데이터 조회")
    
    tickers = [t.strip() for t in tickers_input.split(",") if t.strip()]
    if tickers:
        st.header("1. 기업 개요")
        for tkr in tickers:
            company_name = COMPANY_NAMES_KR.get(tkr, tkr)
            display_name = f"{company_name} ({tkr})" if company_name != tkr else tkr
            st.subheader(f"[{display_name}] 기업 정보")
            try:
                # [LOG: 20260511_0916]
                with st.spinner(f"'{display_name}' 기업 정보를 불러오는 중... ⏳"):
                    sector, industry, summary = get_company_info(tkr)
                st.write(f"**섹터(Sector):** {sector}")
                st.write(f"**산업(Industry):** {industry}")
                with st.expander("사업 내용 요약 보기"):
                    st.write(summary)
            except Exception as e:
                st.error(f"{tkr} 기업 정보를 가져오는 중 오류가 발생했습니다: {e}")

        st.header("2. 주가 데이터")
        for tkr in tickers:
            company_name = COMPANY_NAMES_KR.get(tkr, tkr)
            display_name = f"{company_name} ({tkr})" if company_name != tkr else tkr
            st.subheader(f"[{display_name}] 주가")
            try:
                # [LOG: 20260511_0913] 스피너 추가
                with st.spinner(f"'{display_name}' 주가 데이터를 불러오는 중... ⏳"):
                    price_df = get_stock_price(tkr, start_date, end_date)
                st.dataframe(price_df, column_config=stock_col_config)
                
                # CSV 다운로드 버튼
                csv = price_df.to_csv().encode('utf-8-sig')
                st.download_button(
                    label=f"{display_name} 주가 CSV 다운로드",
                    data=csv,
                    file_name=f"price_{tkr}.csv",
                    mime="text/csv"
                )
            except Exception as e:
                st.error(f"{tkr} 주가 데이터를 가져오는 중 오류가 발생했습니다: {e}")

        st.header("3. 재무제표 데이터")
        for tkr in tickers:
            company_name = COMPANY_NAMES_KR.get(tkr, tkr)
            display_name = f"{company_name} ({tkr})" if company_name != tkr else tkr
            st.subheader(f"[{display_name}] 재무제표")
            try:
                # [LOG: 20260511_0913] 스피너 추가
                with st.spinner(f"'{display_name}' 재무제표 데이터를 불러오는 중... ⏳"):
                    bs, inc, cf = get_financial_statements(tkr)
                
                tab1, tab2, tab3 = st.tabs(["재무상태표", "손익계산서", "현금흐름표"])
                with tab1:
                    st.dataframe(bs, column_config=fin_col_config)
                with tab2:
                    st.dataframe(inc, column_config=fin_col_config)
                with tab3:
                    st.dataframe(cf, column_config=fin_col_config)
                    
                # 엑셀 다운로드 버튼
                excel_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                    bs.to_excel(writer, sheet_name="BalanceSheet")
                    inc.to_excel(writer, sheet_name="IncomeStatement")
                    cf.to_excel(writer, sheet_name="CashFlow")
                
                st.download_button(
                    label=f"{display_name} 재무제표 엑셀 다운로드",
                    data=excel_buffer.getvalue(),
                    file_name=f"fs_{tkr}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except Exception as e:
                st.error(f"{tkr} 재무제표 데이터를 가져오는 중 오류가 발생했습니다: {e}")

if __name__ == "__main__":
    main()
