# ============================
# KOBIS 어제 박스오피스 앱
# Streamlit Cloud 배포용
# ============================

import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo  # 한국 시간 계산용

# -----------------------------
# 페이지 기본 설정
# -----------------------------
st.set_page_config(
    page_title="어제의 박스오피스",
    page_icon="🎬",
    layout="wide"
)

st.title("🎬 어제의 박스오피스")
st.caption("영화진흥위원회(KOBIS) 일일 박스오피스 기준")

# -----------------------------
# 한국 시간 기준 '어제' 계산
# -----------------------------
korea_now = datetime.now(ZoneInfo("Asia/Seoul"))
yesterday = korea_now - timedelta(days=1)

# API에서 사용하는 날짜 형식 (yyyymmdd)
target_date = yesterday.strftime("%Y%m%d")

# 화면에 보여줄 날짜 형식
display_date = yesterday.strftime("%Y년 %m월 %d일")

st.subheader(f"📅 조회 날짜 : {display_date}")

# -----------------------------
# secrets에서 인증키 읽기
# -----------------------------
try:
    API_KEY = st.secrets["KOBIS_KEY"]
except Exception:
    st.error("""
    🔑 KOBIS 인증키가 등록되지 않았습니다.

    Streamlit Cloud → **Settings → Secrets** 에 아래처럼 추가하세요.

    ```
    KOBIS_KEY = "발급받은_인증키"
    ```
    """)
    st.stop()


# -----------------------------
# API 호출 (1시간 캐시)
# 같은 날짜는 다시 요청하지 않음
# -----------------------------
@st.cache_data(ttl=3600)
def load_boxoffice(date):
    """KOBIS API에서 일일 박스오피스 데이터를 가져오는 함수"""

    url = (
        "https://www.kobis.or.kr/kobisopenapi/webservice/rest/"
        "boxoffice/searchDailyBoxOfficeList.json"
    )

    params = {
        "key": API_KEY,
        "targetDt": date
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

    except requests.exceptions.RequestException:
        return None, "네트워크 요청 실패"

    except Exception:
        return None, "응답을 읽을 수 없음"

    # 인증키 오류는 상태코드가 200이어도 faultInfo가 옴
    if "faultInfo" in data:
        message = data["faultInfo"].get("message", "인증 오류")
        return None, f"API 오류 : {message}"

    result = data.get("boxOfficeResult", {})
    movies = result.get("dailyBoxOfficeList", [])

    if len(movies) == 0:
        return None, "영화 목록이 비어 있음"

    return movies, None


movies, error = load_boxoffice(target_date)

# -----------------------------
# 오류 안내
# -----------------------------
if error:
    st.error("❌ 박스오피스 정보를 가져오지 못했습니다.")

    st.markdown("""
    ### 확인해 보세요.

    - **KOBIS 인증키(KOBIS_KEY)** 가 올바른지 확인하세요.
    - 조회 날짜가 맞는지 확인하세요. (오늘 데이터는 아직 집계되지 않습니다.)
    - 인터넷 또는 KOBIS Open API 서비스 상태를 확인하세요.
    - 잠시 후 다시 새로고침해 보세요.
    """)

    st.caption(f"오류 내용 : {error}")
    st.stop()

# -----------------------------
# 데이터프레임 만들기
# -----------------------------
df = pd.DataFrame(movies)

# 숫자 문자열 → 숫자로 변환
number_columns = ["rank", "audiCnt", "audiAcc", "scrnCnt", "showCnt", "rankInten"]

for col in number_columns:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# 순위 기준 정렬
df = df.sort_values("rank")

# 화면용 컬럼 이름 변경
table_df = df.rename(columns={
    "rank": "순위",
    "movieNm": "영화명",
    "openDt": "개봉일",
    "audiCnt": "관객수",
    "audiAcc": "누적관객",
    "scrnCnt": "스크린수"
})

# -----------------------------
# 1위 영화 카드
# -----------------------------
top_movie = df.iloc[0]

st.markdown("---")
st.header("🏆 오늘의 1위 영화")

st.subheader(f"🥇 {top_movie['movieNm']}")

col1, col2, col3 = st.columns(3)

col1.metric(
    "👥 어제 관객수",
    f"{top_movie['audiCnt']:,}명"
)

col2.metric(
    "🎟️ 누적 관객수",
    f"{top_movie['audiAcc']:,}명"
)

col3.metric(
    "🎬 스크린 수",
    f"{top_movie['scrnCnt']:,}개"
)

# -----------------------------
# 박스오피스 표
# -----------------------------
st.markdown("---")
st.header("📋 어제 박스오피스 순위")

st.dataframe(
    table_df[["순위", "영화명", "개봉일", "관객수", "누적관객", "스크린수"]],
    use_container_width=True,
    hide_index=True
)

# -----------------------------
# 관객수 TOP5 그래프
# -----------------------------
st.markdown("---")
st.header("📊 관객수 상위 5편")

top5 = df.nlargest(5, "audiCnt").sort_values("audiCnt")

fig = px.bar(
    top5,
    x="audiCnt",
    y="movieNm",
    orientation="h",
    text="audiCnt",
    labels={
        "movieNm": "영화",
        "audiCnt": "관객수"
    },
    title="어제 관객수 TOP5"
)

fig.update_traces(
    texttemplate="%{text:,}",
    textposition="outside"
)

fig.update_layout(
    yaxis_title="",
    xaxis_title="관객수(명)",
    height=450
)

st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# 전체 통계
# -----------------------------
st.markdown("---")
st.header("📈 전체 통계")

c1, c2, c3 = st.columns(3)

c1.metric(
    "총 영화 수",
    len(df)
)

c2.metric(
    "총 관객수",
    f"{df['audiCnt'].sum():,}명"
)

c3.metric(
    "총 스크린 수",
    f"{df['scrnCnt'].sum():,}개"
)

# -----------------------------
# 하단 안내
# -----------------------------
st.markdown("---")
st.caption(
    "출처 : 영화진흥위원회(KOBIS) Open API · "
    "조회 결과는 1시간 동안 캐시됩니다."
)
