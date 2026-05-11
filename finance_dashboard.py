import streamlit as st
import os

# [LOG: 20260511_1200]
# 메인 파일 이름을 app.py로 통일했으나, 
# 기존 배포 설정(finance_dashboard.py) 호환성을 위해 브릿지 코드를 작성함

if __name__ == "__main__":
    # app.py를 직접 실행하거나 내용을 가져옴
    with open("app.py", "r", encoding="utf-8") as f:
        code = f.read()
    exec(code)
