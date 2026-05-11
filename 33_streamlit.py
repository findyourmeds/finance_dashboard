import streamlit as st
import pandas as pd
import numpy as np
import time

# [LOG: 20260511_1110]
# 33번 앱: API 자동 매매 입문 가이드 및 시뮬레이터
# 주요 기능: API 개념 교육, 매매 로직 시뮬레이션, API 설정 가이드

def main():
    st.set_page_config(page_title="API 자동 매매 입문 가이드", layout="wide", page_icon="🤖")
    
    st.title("🤖 API 자동 매매 입문 가이드")
    st.write("자동 매매 투자봇의 원리를 이해하고, 나만의 전략을 시뮬레이션해 보세요.")

    # 사이드바 메뉴
    menu = st.sidebar.radio("목차", ["1. API 거래란?", "2. 매매 전략 시뮬레이터", "3. 증권사 API 설정 가이드", "4. API 데이터 샌드박스"])

    if menu == "1. API 거래란?":
        st.header("💡 API 자동 매매의 개념")
        col1, col2 = st.columns(2)
        with col1:
            st.info("""
            **API(Application Programming Interface)**
            증권사 서버와 내 컴퓨터가 대화하는 '통로'입니다. 
            사람이 HTS/MTS 창을 누르는 대신, 코드가 직접 주문을 보냅니다.
            """)
            st.success("""
            **왜 자동 매매를 하나요?**
            1. **시간 절약**: 미국 주식 등 밤새 변하는 시장에 자동 대응
            2. **감정 배제**: 정해진 원칙(익절/손절)에 따른 기계적 매매
            3. **신속성**: 급변하는 주가에 수동보다 빠르게 대응
            """)
        with col2:
            st.image("https://img1.daumcdn.net/thumb/R1280x0/?scode=mtistory2&fname=https%3A%2F%2Fblog.kakaocdn.net%2Fdn%2FbcM9Kx%2FbtrM6y5J0zS%2FKXf6Z9YkY3K9XkZkYkYkYk%2Fimg.png", caption="API 통신 개념도 (예시)")

    elif menu == "2. 매매 전략 시뮬레이터":
        st.header("📉 원칙 기반 매매 시뮬레이터")
        st.write("내가 설정한 '손절/익절' 원칙이 실제 주가 변동에서 어떻게 작동하는지 체험해 보세요.")

        # 시뮬레이션 설정
        with st.expander("⚙️ 시뮬레이션 조건 설정", expanded=True):
            col_s1, col_s2, col_s3 = st.columns(3)
            with col_s1:
                buy_price = st.number_input("매수 가격", value=100.0)
            with col_s2:
                target_profit = st.slider("목표 수익률 (익절 %)", 1, 50, 10)
            with col_s3:
                stop_loss = st.slider("최대 손실률 (손절 %)", 1, 50, 5)

        if st.button("🚀 시뮬레이션 실행"):
            # 랜덤 주가 생성
            np.random.seed(int(time.time()))
            steps = 50
            price_changes = np.random.normal(0, 0.02, steps) # 평균 0, 표준편차 2% 변동
            prices = [buy_price]
            for change in price_changes:
                prices.append(prices[-1] * (1 + change))
            
            df_prices = pd.DataFrame({"주가": prices})
            
            # 익절/손절선 계산
            take_profit_price = buy_price * (1 + target_profit / 100)
            stop_loss_price = buy_price * (1 - stop_loss / 100)
            
            # 차트 시각화
            st.line_chart(df_prices)
            
            # 결과 분석
            status = "진행 중"
            final_price = prices[-1]
            trigger_point = None
            
            for i, p in enumerate(prices):
                if p >= take_profit_price:
                    status = "✅ 익절 완료"
                    trigger_point = i
                    final_price = p
                    break
                elif p <= stop_loss_price:
                    status = "❌ 손절 완료"
                    trigger_point = i
                    final_price = p
                    break
            
            # 리포트 출력
            st.divider()
            res_col1, res_col2, res_col3 = st.columns(3)
            res_col1.metric("최종 상태", status)
            res_col2.metric("최종 가격", f"{final_price:.2f}")
            profit_rate = (final_price - buy_price) / buy_price * 100
            res_col3.metric("수익률", f"{profit_rate:.2f}%")
            
            if trigger_point:
                st.write(f"💡 **분석**: 주가 변화 {trigger_point}단계에서 설정한 원칙에 따라 자동으로 매매가 처리되었습니다.")
            else:
                st.write("💡 **분석**: 시뮬레이션 기간 동안 익절/손절선에 도달하지 않았습니다. 포지션을 유지합니다.")

    elif menu == "3. 증권사 API 설정 가이드":
        st.header("📝 한국투자증권 API 준비 체크리스트")
        st.write("자동 매매를 시작하기 위해 반드시 필요한 단계입니다.")
        
        steps = [
            "한국투자증권 종합 계좌 개설 (MTS/홈페이지)",
            "KIS Developers 서비스 신청 (API 전용 사이트)",
            "모의 투자 계좌 신청 (연습용)",
            "API Key 및 Secret Key 발급 및 안전하게 저장",
            "파이썬 설치 및 필수 라이브러리(pandas, requests 등) 준비"
        ]
        
        for i, step in enumerate(steps):
            st.checkbox(f"단계 {i+1}: {step}", key=f"step_{i}")
            
        st.warning("⚠️ 주의: API Key는 절대로 타인에게 공개하거나 GitHub에 올리면 안 됩니다!")

    elif menu == "4. API 데이터 샌드박스":
        st.header("🔬 API 데이터 구조 체험")
        st.write("API가 서버와 주고받는 실제 데이터(JSON) 형식을 확인해 보세요.")
        
        test_ticker = st.text_input("조회할 티커", value="AAPL")
        
        col_req, col_res = st.columns(2)
        
        with col_req:
            st.subheader("📤 요청 (Request)")
            st.code(f"""
GET /uapi/domestic-stock/v1/quotations/inquire-price
Host: openapi.koreainvestment.com
Content-Type: application/json
Authorization: Bearer [ACCESS_TOKEN]
appkey: [YOUR_APP_KEY]
appsecret: [YOUR_APP_SECRET]
            """, language="http")
            st.caption("서버에게 '이 종목 가격 좀 알려줘'라고 보내는 데이터입니다.")
            
        with col_res:
            st.subheader("📥 응답 (Response)")
            st.json({
                "rt_cd": "0",
                "msg_cd": "MCA00000",
                "msg1": "성공",
                "output": {
                    "stck_prpr": "185.92",
                    "prdy_vrss": "1.24",
                    "prdy_ctrt": "0.67",
                    "acml_vol": "4567890",
                    "stck_shrn_iscd": test_ticker
                }
            })
            st.caption("서버가 보내준 실제 주가 정보 데이터입니다. 코드는 여기서 가격(stck_prpr)을 추출해 사용합니다.")

if __name__ == "__main__":
    main()
