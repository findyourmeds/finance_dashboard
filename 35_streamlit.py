import streamlit as st
import pandas as pd
import yfinance as yf
from openai import OpenAI
import requests
import json
import time
from datetime import datetime, timedelta

# [LOG: 20260511_1240]
# 35번 강의 전용 앱: 나의 투자성향 맞춤형 자동 거래 알고리즘 시스템
# 강의 내용 반영: 성향 리포트 분석, 리스크 파라미터 설정, 장중 스케줄링 프로세스

# --- 1. KIS API 유틸리티 (엑셀 명세 기반) ---
def get_kis_token(app_key, app_secret, base_url):
    url = f"{base_url}/oauth2/tokenP"
    body = {"grant_type": "client_credentials", "appkey": app_key, "appsecret": app_secret}
    try:
        res = requests.post(url, headers={"content-type": "application/json"}, data=json.dumps(body))
        return res.json().get("access_token")
    except: return None

def post_kis_order(app_key, app_secret, token, base_url, acc_no, ticker, side="buy", qty=1):
    url = f"{base_url}/uapi/domestic-stock/v1/trading/order-cash"
    is_vts = "vts" in base_url
    tr_id = ("VTTC0012U" if side=="buy" else "VTTC0011U") if is_vts else ("TTTC0012U" if side=="buy" else "TTTC0011U")
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}", "appkey": app_key, "appsecret": app_secret, "tr_id": tr_id, "custtype": "P"}
    body = {"CANO": acc_no[:8], "ACNT_PRDT_CD": acc_no[8:] or "01", "PDNO": ticker.replace(".KS","").replace(".KQ",""), "ORD_DVSN": "01", "ORD_QTY": str(qty), "ORD_UNPR": "0"}
    try: return requests.post(url, headers=headers, data=json.dumps(body)).json()
    except: return {"msg1": "네트워크 주문 오류"}

# --- 2. AI 투자 성향 분석기 ---
def get_ai_strategy_params(api_key, report_text):
    """강의 5절 내용 반영: 투자 성향 리포트를 분석하여 구체적인 매매 파라미터 추출"""
    client = OpenAI(api_key=api_key)
    prompt = f"""
    당신은 전문 자산 관리 AI입니다. 다음 사용자의 '투자 성향 리포트'를 분석하여 자동 매매 봇에 입력할 숫자 파라미터를 결정하세요.
    
    [사용자 리포트]
    {report_text}
    
    [응답 양식 - JSON으로만 답변]
    {{
        "tp_rate": 익절 기준 수익률(%), 
        "sl_rate": 손절 기준 수익률(%), 
        "max_invest_per_stock": 한 종목당 최대 투자 금액(원),
        "monitoring_interval": 매매 판단 주기(분),
        "strategy_summary": 전략 한줄 요약
    }}
    """
    try:
        res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}], response_format={ "type": "json_object" })
        return json.loads(res.choices[0].message.content)
    except: return None

# --- 3. 메인 앱 레이아웃 ---
def main():
    st.set_page_config(page_title="AI 맞춤형 자동 거래 시스템", layout="wide", page_icon="📈")
    st.title("📈 AI 투자 성향 맞춤형 자동 거래 알고리즘")
    st.caption("35차시: 증권사 API와 ChatGPT를 활용한 투자자 성향 맞춤형 봇 운영")

    # 세션 상태 초기화
    if 'history' not in st.session_state: st.session_state['history'] = []
    if 'watchlist' not in st.session_state: st.session_state['watchlist'] = []
    if 'strategy_params' not in st.session_state: st.session_state['strategy_params'] = {}

    # --- 사이드바: KIS 및 Google 설정 ---
    st.sidebar.header("🔑 1. 인프라 설정")
    api_key = st.sidebar.text_input("OpenAI API Key", type="password")
    kis_key = st.sidebar.text_input("KIS App Key", type="password")
    kis_secret = st.sidebar.text_input("KIS Secret Key", type="password")
    acc_no = st.sidebar.text_input("계좌번호(10자리)")
    env = st.sidebar.selectbox("거래 환경", ["모의투자", "실전투자"])
    base_url = "https://openapivts.koreainvestment.com:29443" if env == "모의투자" else "https://openapi.koreainvestment.com:9443"
    
    # 강의 4절: 스프레드시트 연동 개념 반영 (데모용 텍스트)
    sheet_id = st.sidebar.text_input("Google Sheet ID (연동용)", placeholder="1s...ID 입력")

    # --- 메인 탭 구성 ---
    tab_setup, tab_monitor, tab_history = st.tabs(["🎯 전략 수립", "🖥️ 실시간 모니터링", "📜 거래 기록"])

    with tab_setup:
        st.header("1단계: 투자 성향 분석 및 전략 합의")
        report_text = st.text_area("투자 성향 리포트 입력", height=150, placeholder="과거에 생성된 투자 성향 심층 리포트를 여기에 붙여넣으세요.")
        
        if st.button("AI 전략 파라미터 추출"):
            if api_key and report_text:
                with st.spinner("AI가 리포트 분석 중..."):
                    params = get_ai_strategy_params(api_key, report_text)
                    if params:
                        st.session_state['strategy_params'] = params
                        st.success("전략 수립 완료!")
            else: st.error("API Key와 리포트 내용을 입력하세요.")

        if st.session_state['strategy_params']:
            p = st.session_state['strategy_params']
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("익절 기준", f"{p['tp_rate']}%")
            col2.metric("손절 기준", f"{p['sl_rate']}%")
            col3.metric("종목당 금액", f"{p['max_invest_per_stock']:,}원")
            col4.metric("판단 주기", f"{p['monitoring_interval']}분")
            st.info(f"**AI 분석 전략**: {p['strategy_summary']}")

        st.divider()
        st.header("2단계: 종목 풀(Stock Pool) 관리")
        st.write("강의 내용: 대시보드에서 분석된 유망 종목들을 자동 매매 대상으로 등록합니다.")
        new_tkr = st.text_input("티커 추가 (예: 005930.KS)", key="add_tkr")
        if st.button("종목 풀에 추가"):
            if new_tkr and new_tkr not in st.session_state['watchlist']:
                st.session_state['watchlist'].append(new_tkr)
                st.toast(f"{new_tkr} 추가됨")
        st.write(f"현재 등록된 종목: {st.session_state['watchlist']}")

    with tab_monitor:
        st.header("3단계: 장중 자동 매매 프로세스")
        
        # 강의 2절 동작 방식 시각화
        col_step1, col_step2, col_step3 = st.columns(3)
        col_step1.info("**08:30 (장 시작 전)**\n미국 시장 분석 및 종목 선정")
        col_step2.success("**09:00 ~ 14:30 (장중)**\n설정 주기에 따른 자동 매매")
        col_step3.warning("**14:30 (장 마감 전)**\n당일 포지션 전체 청산")

        st.divider()
        
        if st.button("🤖 자동 매매 봇 가동 (테스트 실행)"):
            if not (kis_key and kis_secret and acc_no):
                st.error("증권사 API 설정을 완료해 주세요.")
            elif not st.session_state['watchlist']:
                st.error("종목 풀에 종목을 추가해 주세요.")
            else:
                with st.spinner("AI 봇이 데이터를 분석하고 주문을 전송 중입니다..."):
                    token = get_kis_token(kis_key, kis_secret, base_url)
                    if token:
                        for tkr in st.session_state['watchlist']:
                            # 주문 실행 (시장가 매수)
                            res = post_kis_order(kis_key, kis_secret, token, base_url, acc_no, tkr)
                            # 결과 기록
                            log = {
                                "시간": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "종목": tkr,
                                "구분": "매수(시장가)",
                                "상태": "성공" if res.get("rt_cd") == "0" else "실패",
                                "메시지": res.get("msg1")
                            }
                            st.session_state['history'].append(log)
                            if log["상태"] == "성공": st.success(f"[{tkr}] 주문 성공!")
                            else: st.error(f"[{tkr}] 주문 실패: {log['메시지']}")
                            time.sleep(0.5)
                        st.rerun()
                    else: st.error("토큰 발급 실패. API 키를 확인하세요.")

    with tab_history:
        st.header("4단계: 거래 정보 기록 및 관리")
        st.write("강의 내용: 모든 거래 정보는 실시간으로 기록되어 사후 분석에 활용됩니다.")
        if st.session_state['history']:
            df_history = pd.DataFrame(st.session_state['history'])
            st.dataframe(df_history, width='stretch')
            
            # CSV 다운로드 (스프레드시트 백업용)
            csv = df_history.to_csv(index=False).encode('utf-8-sig')
            st.download_button("거래 내역 CSV 다운로드", data=csv, file_name="trade_log.csv", mime="text/csv")
        else:
            st.info("아직 거래 내역이 없습니다.")

if __name__ == "__main__":
    main()
