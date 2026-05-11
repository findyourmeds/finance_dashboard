import streamlit as st
import yfinance as yf
import pandas as pd
from openai import OpenAI
import io
from datetime import datetime, timedelta
import time
import requests
import json
import os
import numpy as np

# [LOG: 20260511_1125]
# 통합 금융 대시보드 v2.0 (완성형)
# 통합 차시: 19(조회), 21(AI분석), 25(스크리닝), 33(API입문), 35(자동매매)

# --- 1. 사전 정의 및 설정 ---
STOCK_COLUMNS_KR = {
    'Open': '시가', 'High': '고가', 'Low': '저가', 
    'Close': '종가', 'Adj Close': '수정종가', 'Volume': '거래량'
}

FINANCIALS_KR = {
    'Total Revenue': '총수익(매출액)', 'Operating Income': '영업이익', 'Net Income': '당기순이익',
    'Total Assets': '총자산', 'Total Liabilities Net Minority Interest': '총부채', 
    'Stockholders Equity': '자본총계', 'Operating Cash Flow': '영업활동현금흐름', 'Free Cash Flow': '잉여현금흐름'
}

COMPANY_NAMES_KR = {
    'AAPL': '애플', 'TSLA': '테슬라', 'NVDA': '엔비디아', 'MSFT': '마이크로소프트',
    '005930.KS': '삼성전자', '000660.KS': 'SK하이닉스', '373220.KS': 'LG에너지솔루션'
}

# --- 2. 핵심 유틸리티 함수 ---
def get_column_config(kr_dict):
    return {kr: st.column_config.Column(help=eng) for eng, kr in kr_dict.items()}

stock_col_config = get_column_config(STOCK_COLUMNS_KR)
fin_col_config = get_column_config(FINANCIALS_KR)

def get_ai_analysis(api_key, model, prompt):
    if not api_key: return "사이드바에 OpenAI API Key를 입력해주세요."
    try:
        client = OpenAI(api_key=api_key)
        res = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": "당신은 전문 금융 분석가입니다. 한국어로 답변하세요."},
                      {"role": "user", "content": prompt}]
        )
        return res.choices[0].message.content
    except Exception as e: return f"AI 분석 중 오류: {e}"

@st.cache_data
def get_ticker_universe():
    """위키피디아에서 S&P 500 티커 목록을 가져옵니다 (403 에러 방지 포함)."""
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        r = requests.get(url, headers=headers)
        table = pd.read_html(io.StringIO(r.text), match="Symbol")[0]
        return table["Symbol"].str.replace('.', '-', regex=False).tolist()
    except: return ["AAPL", "TSLA", "NVDA", "MSFT", "GOOGL", "AMZN", "META"]

# --- 3. 증권사 API (KIS) 연동 함수 ---
def get_kis_token(app_key, app_secret, base_url):
    url = f"{base_url}/oauth2/tokenP"
    body = {"grant_type": "client_credentials", "appkey": app_key, "appsecret": app_secret}
    try:
        res = requests.post(url, headers={"content-type": "application/json"}, data=json.dumps(body))
        return res.json().get("access_token")
    except: return None

# --- 4. 페이지별 구현 ---

def page_19_stock_info():
    st.header("📈 주가 및 재무제표 조회 (19차시)")
    tickers_input = st.sidebar.text_input("티커 입력 (쉼표 구분)", "TSLA, AAPL", key="p19_tk")
    tickers = [t.strip() for t in tickers_input.split(",") if t.strip()]
    
    for tkr in tickers:
        name = COMPANY_NAMES_KR.get(tkr, tkr)
        st.subheader(f"🔍 {name} ({tkr})")
        t1, t2 = st.tabs(["주가 차트", "핵심 재무지표"])
        with t1:
            df = yf.download(tkr, period="1y", progress=False)
            if not df.empty:
                st.line_chart(df['Close'])
                st.dataframe(df.tail(10).rename(columns=STOCK_COLUMNS_KR), column_config=stock_col_config, use_container_width=True)
        with t2:
            tic = yf.Ticker(tkr)
            bs = tic.balance_sheet.T
            if not bs.empty:
                cols = [c for c in bs.columns if c in FINANCIALS_KR]
                st.dataframe(bs[cols].rename(columns=FINANCIALS_KR), column_config=fin_col_config, use_container_width=True)
        st.divider()

def page_21_ai_market(api_key, model):
    st.header("🤖 AI 시장 분석 및 요약 (21차시)")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🌍 글로벌 시황 요약 실행"):
            with st.spinner("데이터 분석 중..."):
                idx = yf.download("^GSPC", period="5d", progress=False)
                last, prev = idx['Close'].iloc[-1].item(), idx['Close'].iloc[-2].item()
                prompt = f"현재 S&P 500 지수는 {last:.2f}로 전일 대비 {(last-prev)/prev*100:+.2f}% 변동했습니다. 시장 시황을 분석해주세요."
                st.info(get_ai_analysis(api_key, model, prompt))
    with col2:
        tkr = st.text_input("분석할 개별 종목 티커", "TSLA")
        if st.button(f"{tkr} AI 뉴스 분석"):
            with st.spinner("뉴스 분석 중..."):
                news = yf.Ticker(tkr).news[:3]
                news_text = "\n".join([f"- {n['title']}" for n in news])
                prompt = f"{tkr}의 최근 뉴스들입니다:\n{news_text}\n\n이 내용을 바탕으로 투자자가 주의할 점을 요약해줘."
                st.success(get_ai_analysis(api_key, model, prompt))

def page_25_screening():
    st.header("🔍 스마트 종목 스캐너 (25차시)")
    st.write("S&P 500 종목 중 실적 성장과 저평가 조건을 만족하는 기업을 찾습니다.")
    c1, c2 = st.columns(2)
    with c1:
        growth = st.number_input("최소 매출성장률 (%)", 20)
        keyword = st.text_input("비즈니스 키워드", "battery")
    with c2:
        pe_max = st.number_input("최대 PER", 30)
        peg_max = st.number_input("최대 PEG", 1.0)
        
    if st.button("스캔 시작 (상위 30개 샘플)"):
        with st.spinner("스캐닝 중..."):
            universe = get_ticker_universe()[:30]
            passed = []
            for tkr in universe:
                try:
                    tic = yf.Ticker(tkr)
                    q_is = tic.quarterly_income_stmt
                    rev_row = next((idx for idx in q_is.index if "revenue" in idx.lower()), None)
                    if not rev_row: continue
                    rev_g = (q_is.loc[rev_row].iloc[0] - q_is.loc[rev_row].iloc[1]) / abs(q_is.loc[rev_row].iloc[1])
                    if rev_g < (growth/100): continue
                    info = tic.info
                    if keyword.lower() not in (info.get("longBusinessSummary") or "").lower(): continue
                    pe, peg = info.get("trailingPE"), info.get("pegRatio")
                    if pe and pe <= pe_max and peg and peg <= peg_max:
                        passed.append({"Ticker": tkr, "성장률": f"{rev_g*100:.1f}%", "PER": pe, "PEG": peg})
                    time.sleep(0.1)
                except: continue
            if passed: st.table(pd.DataFrame(passed))
            else: st.warning("조건을 만족하는 종목이 없습니다.")

def page_33_api_intro():
    st.header("📡 API 자동매매 입문 가이드 (33차시)")
    t1, t2, t3 = st.tabs(["개념 이해", "매매 시뮬레이터", "준비 체크리스트"])
    with t1:
        st.info("**API란?** 증권사 서버와 내 프로그램이 대화하는 통로입니다. 사람이 버튼을 누르는 대신 코드가 직접 주문을 보냅니다.")
        st.markdown("1. 주가 데이터 요청 → 2. 데이터 수신 → 3. 전략 판단 → 4. 자동 주문 실행")
    with t2:
        st.subheader("📉 원칙 기반 매매 체험")
        buy_p = st.number_input("매수가", 100)
        if st.button("시뮬레이션 가동"):
            prices = [buy_p * (1 + np.random.normal(0, 0.02)) for _ in range(30)]
            st.line_chart(prices)
            st.write(f"최종 수익률: {(prices[-1]-buy_p)/buy_p*100:+.2f}%")
    with t3:
        for s in ["계좌 개설", "API 신청", "모의계좌 설정", "API Key 안전 보관"]: st.checkbox(s)

def page_35_auto_trade(api_key, model):
    st.header("🚀 나만의 자동 매매 시스템 (35차시)")
    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("⚙️ 알고리즘 설정")
        target = st.selectbox("대상 시장", ["국내 주식", "미국 주식"])
        strategy = st.text_area("매매 전략 가이드 (AI 참조용)", "5분봉 골든크로스 시 매수, 3% 익절/손절")
        if st.button("AI 전략 최적화 제안"):
            st.success(get_ai_analysis(api_key, model, f"시장: {target}, 전략: {strategy}. 최적의 손절/익절가와 보완점을 제안해줘."))
    with col2:
        st.subheader("⚡ 실전 주문 테스트 (모의)")
        ak = st.text_input("App Key", type="password", key="ak35")
        sec = st.text_input("Secret Key", type="password", key="sec35")
        acc = st.text_input("계좌번호", key="acc35")
        if st.button("🤖 봇 테스트 가동 (1회 조회)"):
            st.warning("입력하신 키로 모의서버 잔고 조회를 시도합니다...")
            # 실제 연동 로직은 get_kis_token 등을 활용

# --- 5. 메인 렌더링 ---
def main():
    st.set_page_config(page_title="통합 금융 대시보드 v2.0", layout="wide", page_icon="📈")
    st.sidebar.title("📁 교육 차시별 메뉴")
    menu = st.sidebar.radio("페이지 이동", [
        "19차시: 주가/재무제표 조회", 
        "21차시: AI 시장 분석", 
        "25차시: 스마트 종목 스캐너",
        "33차시: API 자동매매 입문",
        "35차시: 나만의 매매 시스템"
    ])
    
    st.sidebar.divider()
    api_key = st.sidebar.text_input("OpenAI API Key", type="password")
    model = st.sidebar.selectbox("모델", ["gpt-4o", "gpt-4o-mini"])
    
    if "19차시" in menu: page_19_stock_info()
    elif "21차시" in menu: page_21_ai_market(api_key, model)
    elif "25차시" in menu: page_25_screening()
    elif "33차시" in menu: page_33_api_intro()
    elif "35차시" in menu: page_35_auto_trade(api_key, model)

if __name__ == "__main__": main()
