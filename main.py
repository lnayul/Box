import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


# ============================================================
# 페이지 설정
# ============================================================

st.set_page_config(
    page_title="일일 박스오피스",
    page_icon="🎬",
    layout="wide"
)

st.title("🎬 일일 박스오피스")
st.caption("영화진흥위원회(KOBIS) 일일 박스오피스")


# ============================================================
# 한국 시간 기준 날짜
# ============================================================

korea_now = datetime.now(ZoneInfo("Asia/Seoul"))

today = korea_now.date()

# 오늘은 집계 전이므로 어제까지만 선택
max_date = today - timedelta(days=1)

# 날짜 선택 시작
min_date = datetime(2000, 1, 1).date()


# ============================================================
# KOBIS 인증키
# ============================================================

try:
    API_KEY = st.secrets["KOBIS_KEY"]

except Exception:
    st.error("🔑 KOBIS 인증키가 없습니다.")

    st.info(
        """
        Streamlit Cloud에서

        **Settings → Secrets**

        에 다음과 같이 입력하세요.

        `KOBIS_KEY = "본인의 인증키"`
        """
    )

    st.stop()


# ============================================================
# 날짜 선택
# ============================================================

st.subheader("📅 조회할 날짜")

selected_date = st.date_input(
    "박스오피스 날짜",
    value=max_date,
    min_value=min_date,
    max_value=max_date
)

target_date = selected_date.strftime("%Y%m%d")

display_date = selected_date.strftime(
    "%Y년 %m월 %d일"
)

st.write(f"선택한 날짜: **{display_date}**")


# ============================================================
# KOBIS API 가져오기
# ============================================================

@st.cache_data(ttl=3600)
def get_boxoffice(target_date, api_key):

    url = (
        "https://www.kobis.or.kr/"
        "kobisopenapi/webservice/rest/boxoffice/"
        "searchDailyBoxOfficeList.json"
    )

    params = {
        "key": api_key,
        "targetDt": target_date
    }

    try:
        response = requests.get(
            url,
            params=params,
            timeout=10
        )

    except requests.exceptions.Timeout:
        return None, "API 요청 시간이 초과되었습니다."

    except requests.exceptions.ConnectionError:
        return None, "KOBIS 서버에 연결하지 못했습니다."

    except requests.exceptions.RequestException as e:
        return None, f"API 요청 오류: {e}"

    if response.status_code != 200:
        return None, (
            f"서버 오류가 발생했습니다. "
            f"(HTTP {response.status_code})"
        )

    try:
        data = response.json()

    except ValueError:
        return None, "KOBIS에서 올바른 데이터를 받지 못했습니다."

    # API 오류 확인
    if "faultInfo" in data:

        fault = data["faultInfo"]

        error_code = fault.get(
            "errorCode",
            "알 수 없음"
        )

        error_message = fault.get(
            "message",
            "오류 메시지가 없습니다."
        )

        return None, (
            f"오류 코드: {error_code}\n\n"
            f"오류 내용: {error_message}"
        )

    # boxOfficeResult 확인
    if "boxOfficeResult" not in data:
        return None, "박스오피스 결과가 없습니다."

    movies = data["boxOfficeResult"].get(
        "dailyBoxOfficeList",
        []
    )

    # 영화 데이터가 없는 경우
    if not movies:
        return None, "EMPTY"

    return movies, None


# ============================================================
# API 실행
# ============================================================

movies, error = get_boxoffice(
    target_date,
    API_KEY
)


# ============================================================
# 데이터가 없는 경우
# ============================================================

if error == "EMPTY":

    st.warning("📭 그날은 아직 집계 전입니다.")

    st.info(
        "다른 날짜를 선택해 주세요."
    )

    st.stop()


# ============================================================
# API 오류
# ============================================================

if error:

    st.error("❌ 박스오피스 정보를 가져오지 못했습니다.")

    st.warning(error)

    st.stop()


# ============================================================
# DataFrame 생성
# ============================================================

df = pd.DataFrame(movies)


# ============================================================
# 숫자로 변환
# ============================================================

number_columns = [
    "rank",
    "rankInten",
    "audiCnt",
    "audiAcc",
    "scrnCnt",
    "showCnt"
]

for column in number_columns:

    df[column] = pd.to_numeric(
        df[column],
        errors="coerce"
    )


# ============================================================
# 공식 순위 기준 정렬
# ============================================================

df = df.sort_values(
    "rank",
    ascending=True
).reset_index(drop=True)


# ============================================================
# 영화 이름 만들기
# ============================================================

df["display_movie_name"] = df.apply(
    lambda row:
        f"{row['movieNm']} 🏆"
        if row["audiAcc"] >= 1_000_000
        else row["movieNm"],
    axis=1
)


# ============================================================
# 순위 변동 표시
# ============================================================

def make_rank_change(value):

    if pd.isna(value):
        return "-"

    value = int(value)

    if value > 0:
        return f"🔴 ↑ {value}"

    if value < 0:
        return f"🔵 ↓ {abs(value)}"

    return "—"


df["순위변동"] = df["rankInten"].apply(
    make_rank_change
)


# ============================================================
# 1위 영화
# ============================================================

first_movie = df.iloc[0]

st.markdown("---")

st.header("🏆 1위 영화")

st.subheader(
    f"🥇 {first_movie['display_movie_name']}"
)


# ============================================================
# 1위 영화 정보
# ============================================================

col1, col2, col3 = st.columns(3)


with col1:

    st.metric(
        "👥 해당일 관객수",
        f"{int(first_movie['audiCnt']):,}명"
    )


with col2:

    st.metric(
        "🎟️ 누적 관객수",
        f"{int(first_movie['audiAcc']):,}명"
    )


with col3:

    st.metric(
        "🖥️ 스크린 수",
        f"{int(first_movie['scrnCnt']):,}개"
    )


# ============================================================
# 전체 박스오피스
# ============================================================

st.markdown("---")

st.header("📋 박스오피스 순위")


table_df = df[
    [
        "rank",
        "순위변동",
        "display_movie_name",
        "openDt",
        "audiCnt",
        "audiAcc",
        "scrnCnt"
    ]
].copy()


table_df.columns = [
    "순위",
    "순위 변동",
    "영화명",
    "개봉일",
    "관객수",
    "누적관객",
    "스크린수"
]


st.dataframe(
    table_df.style.format(
        {
            "순위": "{:.0f}",
            "관객수": "{:,.0f}",
            "누적관객": "{:,.0f}",
            "스크린수": "{:,.0f}"
        }
    ),
    use_container_width=True,
    hide_index=True
)


# ============================================================
# ⭐ 관객수 TOP 5
# ============================================================

st.markdown("---")

st.header("📊 관객수 TOP 5")


# ------------------------------------------------------------
# 여기!!! 가장 중요한 부분
#
# rank가 아니라 audiCnt를 기준으로 내림차순 정렬합니다.
#
# 즉 실제 관객수가 많은 순서:
#
# 1. 오디세이
# 2. 두 번째 영화
# 3. 세 번째 영화
# 4. 네 번째 영화
# 5. 다섯 번째 영화
#
# 순서로 그래프를 만듭니다.
# ------------------------------------------------------------

top5 = (
    df
    .sort_values(
        "audiCnt",
        ascending=False
    )
    .head(5)
    .copy()
)


# ============================================================
# 그래프용 데이터
# ============================================================

chart_df = top5[
    [
        "display_movie_name",
        "audiCnt"
    ]
].copy()


chart_df.columns = [
    "영화",
    "관객수"
]


# ============================================================
# 중요!!!
# 순서를 직접 번호로 고정
# ============================================================

chart_df.insert(
    0,
    "관객순위",
    range(1, len(chart_df) + 1)
)


# ============================================================
# 그래프
# ============================================================
#
# x축:
# 관객수 1위 → 2위 → 3위 → 4위 → 5위
#
# y축:
# 실제 관객수
#
# 따라서 오디세이가 관객수 1위라면
# 무조건 가장 왼쪽에 오디세이가 나옵니다.
# ============================================================

graph_df = chart_df[
    [
        "관객순위",
        "관객수"
    ]
].copy()


graph_df["관객순위"] = graph_df[
    "관객순위"
].astype(str).apply(
    lambda x: f"{x}위"
)


graph_df = graph_df.set_index(
    "관객순위"
)


st.bar_chart(
    graph_df,
    y="관객수",
    x_label="관객수 순위",
    y_label="관객수(명)"
)


# ============================================================
# 그래프 아래 영화 이름 표시
# ============================================================

st.markdown("#### 🎬 관객수 순위")


for i, (_, movie) in enumerate(
    top5.iterrows(),
    start=1
):

    st.write(
        f"**{i}위 · {movie['display_movie_name']}** "
        f"— {int(movie['audiCnt']):,}명"
    )


# ============================================================
# 하단 안내
# ============================================================

st.markdown("---")

st.caption(
    f"📅 조회 날짜: {display_date}"
)

st.caption(
    "🏆 누적 관객수 100만 명 이상 영화에 트로피를 표시합니다."
)

st.caption(
    "🔴 ↑ 순위 상승  |  🔵 ↓ 순위 하락  |  — 변동 없음"
)

st.caption(
    "KOBIS Open API 데이터를 사용하며 "
    "같은 날짜의 결과는 1시간 동안 캐시됩니다."
)
