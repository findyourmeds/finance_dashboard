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

# [LOG: 20260511_1250]
# 통합 금융 대시보드 v3.0 (최종 완결판)
# 특징: 19~35차시 전 과정 기능 통합 + 실전 KIS API 연동 + AI 정밀 전략 분석

# --- 1. 사전 정의 및 유틸리티 ---
STOCK_COLUMNS_KR = {'Open': '시가', 'High': '고가', 'Low': '저가', 'Close': '종가', 'Adj Close': '수정종가', 'Volume': '거래량'}
FINANCIALS_KR = {
    'Total Revenue': '총수익(매출액)', 'Operating Income': '영업이익', 'Net Income': '당기순이익',
    'Total Assets': '총자산', 'Total Liabilities Net Minority Interest': '총부채', 'Stockholders Equity': '자본총계',
    'Operating Cash Flow': '영업활동현금흐름', 'Free Cash Flow': '잉여현금흐름'
}

# --- KIS API 공통 함수 ---
def get_kis_token(app_key, app_secret, base_url):
    url = f"{base_url}/oauth2/tokenP"
    body = {"grant_type": "client_credentials", "appkey": app_key, "appsecret": app_secret}
    try:
        res = requests.post(url, headers={"content-type": "application/json"}, data=json.dumps(body))
        return res.json().get("access_token") if res.status_code == 200 else None
    except: return None

def post_kis_order(app_key, app_secret, token, base_url, acc_no, ticker, side="buy"):
    url = f"{base_url}/uapi/domestic-stock/v1/trading/order-cash"
    is_vts = "vts" in base_url
    tr_id = ("VTTC0012U" if side == "buy" else "VTTC0011U") if is_vts else ("TTTC0012U" if side == "buy" else "TTTC0011U")
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}", "appkey": app_key, "appsecret": app_secret, "tr_id": tr_id, "custtype": "P"}
    body = {"CANO": acc_no[:8], "ACNT_PRDT_CD": acc_no[8:] or "01", "PDNO": ticker.replace(".KS","").replace(".KQ",""), "ORD_DVSN": "01", "ORD_QTY": "1", "ORD_UNPR": "0"}
    try: return requests.post(url, headers=headers, data=json.dumps(body)).json()
    except: return {"msg1": "주문 네트워크 오류"}

# --- 페이지 1: 주가 및 재무제표 (19) ---
def page_stock_info():
    st.header("📈 주가 및 재무제표 조회")
    tkr = st.sidebar.text_input("티커 (예: TSLA, 005930.KS)", "TSLA", key="st_tkr")
    if tkr:
        with st.spinner("데이터 로드 중..."):
            df = yf.download(tkr, period="1y", progress=False)
            if not df.empty:
                st.subheader(f"📊 {tkr} 최근 1년 시세")
                st.line_chart(df['Close'])
                st.dataframe(df.tail(20).rename(columns=STOCK_COLUMNS_KR), width='stretch')
                
                st.subheader("💰 주요 재무 지표")
                tic = yf.Ticker(tkr)
                bs = tic.balance_sheet.T
                if not bs.empty:
                    valid_cols = [c for c in bs.columns if c in FINANCIALS_KR]
                    st.dataframe(bs[valid_cols].rename(columns=FINANCIALS_KR), width='stretch')
                else: st.info("재무 데이터를 찾을 수 없습니다.")

# --- 페이지 2: AI 시장 분석 (21) ---
def page_ai_analysis(api_key, model):
    st.header("🤖 AI 글로벌 시장 브리핑")
    if st.button("실시간 마켓 리포트 생성"):
        if not api_key: st.error("OpenAI API Key가 필요합니다.")
        else:
            with st.spinner("전 세계 시장 데이터 수집 및 분석 중..."):
                # 주요 지수 수집
                indices = {"S&P 500": "^GSPC", "나스닥": "^IXIC", "KOSPI": "^KS11"}
                summary = ""
                for name, tkr in indices.items():
                    data = yf.download(tkr, period="5d", progress=False)
                    last, prev = data['Close'].iloc[-1].item(), data['Close'].iloc[-2].item()
                    summary += f"{name}: {last:.2f} ({(last-prev)/prev*100:+.2f}%)\n"
                
                client = OpenAI(api_key=api_key)
                prompt = f"시장 데이터:\n{summary}\n위 상황을 바탕으로 오늘의 투자 전략을 3줄로 요약해줘."
                res = client.chat.completions.create(model=model, messages=[{"role": "user", "content": prompt}])
                st.success("AI 시장 분석 결과")
                st.write(res.choices[0].message.content)

# --- 페이지 3: 종목 스캐너 (25) ---
def page_scanner():
    st.header("🔍 조건별 종목 스캐너 (S&P 500)")
    keyword = st.text_input("사업 키워드 검색 (예: Cloud, AI, EV)", "AI")
    if st.button("스캐닝 시작 (상위 종목 대상)"):
        with st.spinner("종목 정보를 스캔하는 중..."):
            # 데모를 위해 상위 15개 종목만 스캔
            sample_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "BRK-B", "LLY", "AVGO", "V", "JPM", "TSM", "UNH", "MA"]
            found = []
            for tkr in sample_tickers:
                info = yf.Ticker(tkr).info
                summary = info.get("longBusinessSummary", "").lower()
                if keyword.lower() in summary:
                    found.append({
                        "티커": tkr,
                        "기업명": info.get("shortName"),
                        "섹터": info.get("sector"),
                        "PER": info.get("trailingPE"),
                        "매출성장(%)": f"{info.get('revenueGrowth', 0)*100:.1f}%"
                    })
            if found:
                st.table(pd.DataFrame(found))
            else: st.warning(f"'{keyword}' 관련 종목을 찾지 못했습니다.")

# --- 페이지 4: API 입문 및 명세서 (33) ---
def page_api_edu():
    st.header("📡 API 자동매매 교육 및 명세서")
    t1, t2, t3 = st.tabs(["매매 시뮬레이터", "KIS 실전 테스트", "엑셀 명세서 뷰어"])
    
    with t1:
        st.subheader("📉 감정 배제 원칙 매매 체험")
        c1, c2 = st.columns(2)
        buy_p = c1.number_input("매수 단가", value=100)
        goal = c2.slider("목표 수익률(%)", 1, 50, 10)
        if st.button("시뮬레이션 가동"):
            prices = [buy_p]
            for _ in range(30): prices.append(prices[-1] * (1 + np.random.normal(0, 0.02)))
            st.line_chart(prices)
            res = "성공" if prices[-1] >= buy_p*(1+goal/100) else "보유"
            st.metric("최종 수익률", f"{(prices[-1]-buy_p)/buy_p*100:.2f}%", delta=res)

    with t2:
        st.subheader("🔑 KIS 잔고 실시간 조회")
        ak = st.text_input("KIS App Key", type="password", key="ak33")
        sk = st.text_input("KIS Secret Key", type="password", key="sk33")
        an = st.text_input("계좌번호(10자리)", key="an33")
        if st.button("조회 실행"):
            tok = get_kis_token(ak, sk, "https://openapivts.koreainvestment.com:29443")
            if tok:
                res = requests.get("https://openapivts.koreainvestment.com:29443/uapi/domestic-stock/v1/trading/inquire-balance", 
                                   headers={"Content-Type": "application/json", "Authorization": f"Bearer {tok}", "appkey": ak, "appsecret": sk, "tr_id": "VTTC8434R", "custtype": "P"},
                                   params={"CANO": an[:8], "ACNT_PRDT_CD": an[8:] or "01", "AFHR_FLPR_YN": "N", "ODR_MTHD": "00", "CASH_TP": "1", "CTX_AREA_FK100": "", "CTX_AREA_NK100": ""}).json()
                st.json(res)
            else: st.error("인증 실패")

    with t3:
        st.subheader("📂 33번 폴더 엑셀 명세서 내역")
        if os.path.exists('33_excel_analysis.json'):
            with open('33_excel_analysis.json', 'r', encoding='utf-8') as f:
                specs = json.load(f)
                file_sel = st.selectbox("조회할 파일", list(specs.keys()))
                st.dataframe(pd.DataFrame(specs[file_sel]["sample_data"]), width='stretch')
        else: st.warning("33_analyze_excel.py를 실행하여 데이터를 추출해 주세요.")

# --- 페이지 5: 최종 자동 매매 시스템 (35) ---
def page_trading_system(api_key, model):
    st.header("🚀 AI 맞춤형 자동 매매 (최종)")
    
    if 'history' not in st.session_state: st.session_state['history'] = []
    if 'watchlist' not in st.session_state: st.session_state['watchlist'] = ["005930.KS"]

    tab_setup, tab_exec = st.tabs(["🎯 전략 및 종목", "⚡ 봇 가동 및 이력"])
    
    with tab_setup:
        st.subheader("1. AI 투자 성향 분석")
        report = st.text_area("투자 성향 리포트 입력", "저는 변동성이 큰 시장에서 공격적인 수익을 원합니다.")
        if st.button("AI 정밀 전략 추출"):
            client = OpenAI(api_key=api_key)
            res = client.chat.completions.create(model=model, messages=[{"role": "user", "content": f"리포트: {report}\n익절/손절/비중/주기를 숫자로 제안해줘."}])
            st.info(res.choices[0].message.content)
            
        st.divider()
        st.subheader("2. 매매 대상 종목(Watchlist)")
        new_tkr = st.text_input("티커 추가 (예: NVDA, 000660.KS)")
        if st.button("추가") and new_tkr: st.session_state['watchlist'].append(new_tkr)
        st.write(f"감시 중: {st.session_state['watchlist']}")

    with tab_exec:
        st.subheader("3. 실전 주문 및 기록")
        ak = st.sidebar.text_input("KIS AppKey", type="password", key="ak35")
        sk = st.sidebar.text_input("KIS Secret", type="password", key="sk35")
        an = st.sidebar.text_input("KIS 계좌번호", key="an35")
        
        if st.button("🤖 자동 매매 1회 가동"):
            if not (ak and sk and an): st.error("사이드바에서 KIS 설정을 완료하세요.")
            else:
                tok = get_kis_token(ak, sk, "https://openapivts.koreainvestment.com:29443")
                if tok:
                    for tkr in st.session_state['watchlist']:
                        res = post_kis_order(ak, sk, tok, "https://openapivts.koreainvestment.com:29443", an, tkr)
                        log = {"시간": datetime.now().strftime("%H:%M:%S"), "종목": tkr, "상태": "완료", "서버응답": res.get("msg1")}
                        st.session_state['history'].insert(0, log)
                        st.toast(f"{tkr} 주문 시도 완료")
                    st.rerun()
        
        if st.session_state['history']:
            st.dataframe(pd.DataFrame(st.session_state['history']), width='stretch')
        else: st.info("주문 이력이 없습니다.")

# --- 메인 쉘 ---
def main():
    st.set_page_config(page_title="통합 금융 AI 시스템", layout="wide", page_icon="💰")
    
    st.sidebar.title("💎 금융 AI 대시보드")
    menu = st.sidebar.selectbox("기능 선택", [
        "📈 주가/재무 분석 (19강)", 
        "🤖 AI 시장 분석 (21강)", 
        "🔍 종목 스캐너 (25강)", 
        "📡 API 입문/명세 (33강)", 
        "🚀 자동매매 시스템 (35강)"
    ])
    
    st.sidebar.divider()
    api_key = st.sidebar.text_input("OpenAI API Key", type="password")
    model = st.sidebar.selectbox("GPT 모델", ["gpt-4o", "gpt-4o-mini"])
    
    if "19" in menu: page_stock_info()
    elif "21" in menu: page_ai_analysis(api_key, model)
    elif "25" in menu: page_scanner()
    elif "33" in menu: page_api_edu()
    elif "35" in menu: page_trading_system(api_key, model)

if __name__ == "__main__":
    main()
