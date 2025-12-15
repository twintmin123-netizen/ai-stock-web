# 환경변수 및 공통 세팅 담당

import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# ─────────────────────────────
# 🔑 API KEY 환경변수 로드
# ─────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")

# ─────────────────────────────
# 🧠 Fear & Greed Index (RapidAPI 버전)
# ─────────────────────────────
FGI_API_URL = os.getenv(
    "FGI_API_URL", "https://fear-and-greed-index.p.rapidapi.com/v1/fgi"
)
FGI_API_HOST = os.getenv(
    "FGI_API_HOST", "fear-and-greed-index.p.rapidapi.com"
)
FGI_API_KEY = os.getenv("FGI_API_KEY", RAPIDAPI_KEY)

# ─────────────────────────────
# 💹 한국투자증권 OpenAPI 설정
# ─────────────────────────────
# .env 예시 값들은 이미 존재함:contentReference[oaicite:1]{index=1}
KIS_BASE_URL = os.getenv("KIS_BASE_URL")          # https://openapi.koreainvestment.com:9443
KIS_URL_BASE = os.getenv("KIS_URL_BASE", KIS_BASE_URL)
KIS_APP_KEY = os.getenv("KIS_APP_KEY")
KIS_APP_SECRET = os.getenv("KIS_APP_SECRET")
KIS_CANO = os.getenv("KIS_CANO")                  # 계좌번호 앞 8자리
KIS_ACNT_PRDT_CD = os.getenv("KIS_ACNT_PRDT_CD")  # 계좌 상품코드 (01 등)

# ─────────────────────────────
# 🔧 OpenAI 클라이언트 초기화
# ─────────────────────────────
client = OpenAI()  # OPENAI_API_KEY는 .env에서 자동 인식

# ─────────────────────────────
# 🔍 네이버 검색 API (뉴스 검색용)
# ─────────────────────────────
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

# ─────────────────────────────
# 🌐 DeepL API (번역용)
# ─────────────────────────────
DEEPL_API_KEY = os.getenv("DEEPL_API_KEY")
