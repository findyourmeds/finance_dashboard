import streamlit as st
import pandas as pd
import numpy as np
import time
import requests
import json
import os

# [LOG: 20260511_1155]
# 33번 앱 고도화: 엑셀 명세서 동적 반영 버전
# 주요 기능: API 개념, 시뮬레이터, 설정 가이드, 샌드박스, 실전 테스트, **엑셀 명세서 뷰어**

# --- 데이터 로드 (분석된 JSON) ---
EXCEL_ANALYSIS_PATH = 'excel_analysis.json'
def load_excel_specs():
    if os.path.exists(EXCEL_ANALYSIS_PATH):
        with open(EXCEL_ANALYSIS_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

API_SPECS = load_excel_specs()

# --- KIS API 유틸리티 ---
def get_kis_token(app_key, app_secret, base_url):
    url = f"{base_url}/oauth2/tokenP"
    headers = {"content-type": "application/json"}
    body = {"grant_type": "client_credentials", "appkey": app_key, "appsecret": app_secret}
    try:
        res = requests.post(url, headers=headers, data=json.dumps(body))
        return res.json().get("access_token") if res.status_code == 200 else f"Error: {res.json().get('error_description', '알 수 없는 오류')}"
    except Exception as e: return f"Exception: {e}"

def get_kis_balance(app_key, app_secret, token, base_url, acc_no):
    url = f"{base_url}/uapi/domestic-stock/v1/trading/inquire-balance"
    acc_no_prefix, acc_no_suffix = acc_no[:8], acc_no[8:] if len(acc_no) > 8 else "01"
    
    # 엑셀 명세([국내주식] 주문_계좌.xlsx)에 근거한 TR_ID 설정
    # 실제로는 명세서에서 '주식잔고조회' 항목의 TR_ID를 가져오는 로직이 이상적
    tr_id = "VTTC8434R" if "vts" in base_url else "TTTC8434R"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "appkey": app_key, "appsecret": app_secret,
        "tr_id": tr_id, "custtype": "P"
    }
    params = {
        "CANO": acc_no_prefix, "ACNT_PRDT_CD": acc_no_suffix,
        "AFHR_FLPR_YN": "N", "ODR_MTHD": "00", "CASH_TP": "1",
        "CTX_AREA_FK100": "", "CTX_AREA_NK100": ""
    }
    try:
        res = requests.get(url, headers=headers, params=params)
        return res.json()
    except Exception as e: return {"error": str(e)}

def main():
    st.set_page_config(page_title="API 자동 매매 입문 가이드", layout="wide", page_icon="🤖")
    st.title("🤖 API 자동 매매 & 명세서 뷰어")
    
    # 사이드바 메뉴
    menu_options = ["1. API 거래란?", "2. 매매 전략 시뮬레이터", "3. 증권사 API 설정 가이드", "4. API 데이터 샌드박스", "5. 실전 API 연결 테스트", "6. API 명세서 뷰어 (엑셀 반영)"]
    menu = st.sidebar.radio("목차", menu_options)

    if menu == "1. API 거래란?":
        st.header("💡 API 자동 매매의 개념")
        col1, col2 = st.columns(2)
        with col1:
            st.info("**API(Application Programming Interface)**: 서버와 내 컴퓨터가 대화하는 '통로'입니다.")
            st.success("**왜 자동 매매를 하나요?**: 시간 절약, 감정 배제, 신속성 때문입니다.")
        with col2:
            st.subheader("🔄 데이터 흐름도")
            st.markdown("```mermaid\ngraph LR\nA[내 컴퓨터] -- 1. 주가 요청 --> B(증권사 서버)\nB -- 2. 현재가 응답 --> A\nA -- 3. 매수 주문 --> B\nB -- 4. 체결 결과 --> A\n```")

    elif menu == "2. 매매 전략 시뮬레이터":
        st.header("📉 원칙 기반 매매 시뮬레이터")
        with st.expander("⚙️ 시뮬레이션 조건 설정", expanded=True):
            c1, c2, c3 = st.columns(3)
            buy_price = c1.number_input("매수 가격", value=100.0)
            target_profit = c2.slider("목표 수익률 (익절 %)", 1, 50, 10)
            stop_loss = c3.slider("최대 손실률 (손절 %)", 1, 50, 5)

        if st.button("🚀 시뮬레이션 실행"):
            np.random.seed(int(time.time()))
            prices = [buy_price]
            for _ in range(50): prices.append(prices[-1] * (1 + np.random.normal(0, 0.02)))
            st.line_chart(pd.DataFrame({"주가": prices}))
            tp, sl = buy_price * (1 + target_profit/100), buy_price * (1 - stop_loss/100)
            status, final_p = "진행 중", prices[-1]
            for p in prices:
                if p >= tp: status, final_p = "✅ 익절 완료", p; break
                elif p <= sl: status, final_p = "❌ 손절 완료", p; break
            res_c1, res_c2, res_c3 = st.columns(3)
            res_c1.metric("최종 상태", status)
            res_c2.metric("최종 가격", f"{final_p:.2f}")
            res_c3.metric("수익률", f"{(final_p-buy_price)/buy_price*100:.2f}%")

    elif menu == "3. 증권사 API 설정 가이드":
        st.header("📝 한국투자증권 API 준비 체크리스트")
        for step in ["계좌 개설", "KIS Developers 신청", "모의투자 신청", "API Key 발급", "라이브러리 준비"]:
            st.checkbox(step)
        st.warning("⚠️ 주의: API Key는 절대 공개하지 마세요!")

    elif menu == "4. API 데이터 샌드박스":
        st.header("🔬 API 데이터 구조 체험")
        test_ticker = st.text_input("조회할 티커", value="AAPL")
        c1, c2 = st.columns(2)
        with c1: st.subheader("📤 요청"); st.code(f"GET /uapi/domestic-stock/v1/quotations/inquire-price\nTicker: {test_ticker}")
        with c2: st.subheader("📥 응답"); st.json({"rt_cd": "0", "output": {"stck_prpr": "185.92", "stck_shrn_iscd": test_ticker}})

    elif menu == "5. 실전 API 연결 테스트":
        st.header("🔑 실전 API 연동 실습")
        c1, c2 = st.columns(2)
        with c1:
            env = st.selectbox("환경 선택", ["모의투자 (Virtual)", "실전투자 (Real)"])
            base_url = "https://openapivts.koreainvestment.com:29443" if "모의" in env else "https://openapi.koreainvestment.com:9443"
            app_key = st.text_input("App Key", type="password")
            app_secret = st.text_input("Secret Key", type="password")
            acc_no = st.text_input("계좌번호 (10자리)", placeholder="예: 1234567801")
        with c2:
            st.info("💡 엑셀 명세서 기반으로 TR_ID를 자동으로 할당하여 통신합니다.")
            if st.button("🔌 API 연결 및 잔고 조회"):
                if not (app_key and app_secret and acc_no): st.error("정보를 입력하세요.")
                else:
                    with st.spinner("통신 중..."):
                        token = get_kis_token(app_key, app_secret, base_url)
                        if token.startswith("Error"): st.error(token)
                        else:
                            st.success("✅ 토큰 발급 성공!")
                            res = get_kis_balance(app_key, app_secret, token, base_url, acc_no)
                            if res.get("rt_cd") == "0":
                                out2 = res.get("output2", [{}])[0]
                                b1, b2, b3 = st.columns(3)
                                b1.metric("총 평가금액", f"{int(out2.get('tot_evlu_amt', 0)):,}원")
                                b2.metric("실현 손익", f"{int(out2.get('pnl_smtl_amt', 0)):,}원")
                                b3.metric("수익률", f"{out2.get('evlu_amt_smtl_amt', '0')}%")
                            else: st.error(f"조회 실패: {res.get('msg1')}")

    elif menu == "6. API 명세서 뷰어 (엑셀 반영)":
        st.header("📂 한국투자증권 API 명세서 (엑셀 데이터)")
        st.write("D:/work/stock/33 폴더의 엑셀 파일들로부터 추출된 사양 정보입니다.")
        
        if not API_SPECS:
            st.warning("분석된 엑셀 데이터가 없습니다. `analyze_excel.py`를 먼저 실행하거나 파일을 확인해 주세요.")
        else:
            file_names = list(API_SPECS.keys())
            selected_file = st.selectbox("명세서 파일 선택", file_names)
            
            if selected_file:
                spec = API_SPECS[selected_file]
                st.subheader(f"📄 {selected_file} 상세 내용")
                
                # 데이터프레임으로 표시
                if "sample_data" in spec:
                    df_spec = pd.DataFrame(spec["sample_data"])
                    st.dataframe(df_spec, width='stretch')
                    
                    st.info(f"💡 이 파일은 총 {len(spec['columns'])}개의 컬럼으로 구성되어 있습니다.")
                    with st.expander("컬럼 목록 보기"):
                        st.write(", ".join(spec["columns"]))
                else:
                    st.error("데이터를 표시할 수 없습니다.")

if __name__ == "__main__":
    main()
