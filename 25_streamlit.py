import streamlit as st
import yfinance as yf
import pandas as pd
from openai import OpenAI
import time

# [LOG: 20260511_1030]
# 25번 앱: 투자 목표별 AI 종목 스캐너
# 주요 기능: 특정 지수(S&P 500 등) 내 조건부 필터링 + AI 추천 사유 분석

import requests

def get_sp500_tickers():
    """위키피디아에서 S&P 500 티커 목록을 가져옵니다. (403 에러 방지 헤더 추가)"""
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers)
        table = pd.read_html(response.text)
        df = table[0]
        tickers = df['Symbol'].str.replace('.', '-', regex=False).tolist()
        return tickers
    except:
        return ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]

def get_kospi200_tickers():
    """위키피디아에서 KOSPI 200 티커 목록을 가져옵니다."""
    url = 'https://en.wikipedia.org/wiki/KOSPI_200'
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers)
        tables = pd.read_html(response.text)
        # KOSPI 200 테이블 위치 찾기 (보통 종목 코드가 있는 테이블)
        for df in tables:
            if 'Ticker' in df.columns or 'Code' in df.columns:
                col = 'Ticker' if 'Ticker' in df.columns else 'Code'
                # 한국 주식은 티커 뒤에 .KS를 붙여야 yfinance에서 인식함
                tickers = [f"{str(code).zfill(6)}.KS" for code in df[col].tolist()]
                return tickers
        return ["005930.KS", "000660.KS", "035420.KS"] # 기본 샘플
    except:
        return ["005930.KS", "000660.KS", "035420.KS"]

def get_ai_analysis(api_key, model, prompt):
    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "당신은 전문 투자 전략가입니다. 필터링된 종목들의 잠재력을 분석하여 한국어로 보고서를 작성하세요."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"AI 분석 중 오류 발생: {e}"

def main():
    st.set_page_config(page_title="AI 종목 스캐너 v25", layout="wide")
    st.title("🔍 AI 투자 목표별 종목 스캐너")
    
    # 사이드바 설정
    st.sidebar.header("🔑 기본 설정")
    api_key = st.sidebar.text_input("OpenAI API Key", type="password")
    model_option = st.sidebar.selectbox("GPT 모델", ["gpt-4o", "gpt-4o-mini"])
    
    # [LOG: 20260511_1050] 국가 선택 추가
    market_choice = st.sidebar.radio("분석 시장 선택", ["미국 (S&P 500)", "한국 (KOSPI 200)"])
    
    st.sidebar.divider()
    st.sidebar.header("🎯 필터링 조건 설정")
    
    max_count = st.sidebar.slider("분석할 최대 종목 수", 5, 50, 20)
    min_growth = st.sidebar.number_input("최소 매출 성장률 (%)", value=5) # 한국 시장 고려 하향 조정
    max_per = st.sidebar.number_input("최대 PER (주가수익비율)", value=30)
    min_news = st.sidebar.slider("최근 뉴스 최소 개수", 0, 10, 1) # 한국 뉴스는 영문 기준이라 적을 수 있음
    keyword = st.sidebar.text_input("사업 키워드 (영문 권장)", value="")

    if st.button("🚀 종목 스캔 및 AI 분석 시작"):
        if not api_key:
            st.error("AI 분석을 위해 API Key가 필요합니다.")
            return

        with st.spinner(f"{market_choice} 티커 목록을 불러오는 중..."):
            if "미국" in market_choice:
                all_tickers = get_sp500_tickers()
            else:
                all_tickers = get_kospi200_tickers()
            
            test_tickers = all_tickers[:max_count]
        
        st.info(f"{market_choice} 상위 {max_count}개 종목 검증 시작...")
        
        filtered_results = []
        progress_bar = st.progress(0)
        
        for i, tkr in enumerate(test_tickers):
            try:
                # [LOG: 20260511_1035] yfinance 데이터 수집
                tk = yf.Ticker(tkr)
                info = tk.info
                
                # 조건 1: PER 체크
                per = info.get('forwardPE') or info.get('trailingPE')
                if per and per > max_per: continue
                
                # 조건 2: 키워드 체크
                summary = info.get('longBusinessSummary', '')
                if keyword and keyword.lower() not in summary.lower(): continue
                
                # 조건 3: 뉴스 개수 체크
                news_count = len(tk.news)
                if news_count < min_news: continue
                
                # 조건 4: 성장성 (매출 성장률)
                growth = info.get('revenueGrowth', 0) * 100
                if growth < min_growth: continue
                
                # 모든 조건 통과 시 리스트 추가
                filtered_results.append({
                    '티커': tkr,
                    '기업명': info.get('shortName', tkr),
                    '현재가': info.get('currentPrice'),
                    'PER': per,
                    '성장률(%)': f"{growth:.1f}%",
                    '뉴스수': news_count,
                    '사업요약': summary[:200] + "..."
                })
            except:
                pass
            
            progress_bar.progress((i + 1) / len(test_tickers))
            time.sleep(0.1) # API 부하 방지용 짧은 휴식

        if filtered_results:
            st.success(f"조건에 맞는 종목 {len(filtered_results)}개를 찾았습니다!")
            res_df = pd.DataFrame(filtered_results)
            st.dataframe(res_df, width='stretch')
            
            # AI 종합 분석
            st.divider()
            st.header("💡 AI 종목 추천 및 전략 리포트")
            with st.spinner("AI가 필터링된 종목들을 심층 분석 중..."):
                ticker_list = ", ".join([r['티커'] for r in filtered_results])
                prompt = f"""
                다음 조건으로 필터링된 미국 주식 종목들입니다: {ticker_list}
                조건: PER {max_per} 이하, 성장률 {min_growth}% 이상, 키워드 '{keyword}' 포함.
                
                각 종목의 데이터 요약: {filtered_results}
                
                위 종목들 중 가장 투자 매력도가 높은 상위 2개를 선정하고, 그 이유를 '비즈니스 모델'과 '재무 건전성' 관점에서 설명해줘. 
                마지막에는 이 포트폴리오의 위험 요소도 한 줄 언급해줘.
                """
                report = get_ai_analysis(api_key, model_option, prompt)
                st.markdown(report)
        else:
            st.warning("조건에 맞는 종목이 없습니다. 필터링 조건을 완화해 보세요.")

if __name__ == "__main__":
    main()
