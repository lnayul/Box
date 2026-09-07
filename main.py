# ============================================================
# 🎬 일일 박스오피스 조회 앱
# 영화진흥위원회(KOBIS) Open API
# ============================================================

import streamlit as st
import pandas as pd
import requests
import plotly.express as px

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


# ============================================================
# 1. 페이지 설정
# ============================================================

st.set_page_config(
    page_title="일일 박스오피스",
    page_icon="🎬",
    layout="wide"
)


# ============================================================
# 2. 제목
# ============================================================

st.title("🎬 일일 박스오피스")
st.caption("영화진흥위원회(KOBIS) 일일 박스오피스")


# ============================================================
# 3. 한국 시간 기준 날짜 계산
# ============================================================
# Streamlit Cloud 서버의 시간이 한국 시간과 다를 수 있기 때문에
# 한국 시간(Asia/Seoul)을 기준으로 날짜를 계산합니다.

korea_now = datetime.now(
    ZoneInfo("Asia/Seoul")
)

today = korea_now.date()

# 오늘은 아직 집계가 끝나지 않았을 수 있으므로
# 선택 가능한 가장 최근 날짜를 어제로 설정합니다.

max_date = today - timedelta(days=1)

# 선택 가능한 가장 오래된 날짜

min_date = datetime(
    2000,
    1,
    1
).date()


# ============================================================
# 4. KOBIS 인증키 가져오기
# ============================================================
# 인증키를 코드에 직접 적지 않습니다.
#
# Streamlit Cloud
# → Settings
# → Secrets
#
# 다음과 같이 입력해야 합니다.
#
# KOBIS_KEY = "본인의_KOBIS_인증키"
# ============================================================

try:

    API_KEY = st.secrets["KOBIS_KEY"]

except Exception:

    st.error("🔑 KOBIS 인증키를 찾을 수 없습니다.")

    st.info(
        """
        ### KOBIS 인증키 설정 방법

        Streamlit Cloud의

        **Settings → Secrets**

        에 아래 내용을 입력하세요.

        `KOBIS_KEY = "본인의_KOBIS_인증키"`

        인증키는 `main.py`에 직접 입력하지 않습니다.
        """
    )

    st.stop()


# ============================================================
# 5. 날짜 선택
# ============================================================

st.subheader("📅 조회할 날짜를 선택하세요")

selected_date = st.date_input(
    "박스오피스 날짜",
    value=max_date,
    min_value=min_date,
    max_value=max_date,
    help="오늘은 아직 집계 전이므로 어제까지 선택할 수 있습니다."
)

# KOBIS API용 날짜
# 예: 2026-09-06 → 20260906

target_date = selected_date.strftime(
    "%Y%m%d"
)

# 화면에 표시할 날짜

display_date = selected_date.strftime(
    "%Y년 %m월 %d일"
)

st.write(
    f"선택한 날짜: **{display_date}**"
)


# ============================================================
# 6. KOBIS API 호출 함수
# ============================================================
# 같은 날짜를 반복해서 조회할 경우
# 1시간 동안 캐시된 데이터를 사용합니다.

@st.cache_data(ttl=3600)
def get_boxoffice(target_date, api_key):

    # KOBIS 일일 박스오피스 API 주소

    url = (
        "https://www.kobis.or.kr/"
        "kobisopenapi/webservice/rest/boxoffice/"
        "searchDailyBoxOfficeList.json"
    )

    # API에 전달할 값

    params = {
        "key": api_key,
        "targetDt": target_date
    }

    # --------------------------------------------------------
    # API 요청
    # --------------------------------------------------------

    try:

        response = requests.get(
            url,
            params=params,
            timeout=10
        )

    except requests.exceptions.Timeout:

        return None, "KOBIS API 요청 시간이 초과되었습니다."

    except requests.exceptions.ConnectionError:

        return None, "KOBIS 서버에 연결하지 못했습니다."

    except requests.exceptions.RequestException as e:

        return None, (
            f"API 요청 중 오류가 발생했습니다: {e}"
        )


    # --------------------------------------------------------
    # HTTP 상태 코드 확인
    # --------------------------------------------------------

    if response.status_code != 200:

        return None, (
            f"KOBIS 서버에서 HTTP "
            f"{response.status_code} 응답을 반환했습니다."
        )


    # --------------------------------------------------------
    # JSON 데이터로 변환
    # --------------------------------------------------------

    try:

        data = response.json()

    except ValueError:

        return None, (
            "KOBIS에서 JSON 형식의 데이터를 "
            "받지 못했습니다."
        )


    # --------------------------------------------------------
    # API 오류 확인
    # --------------------------------------------------------
    # KOBIS는 인증키가 잘못된 경우에도
    # HTTP 200을 반환하면서 faultInfo를 보내는 경우가 있습니다.

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
            f"KOBIS API 오류\n\n"
            f"오류 코드: {error_code}\n\n"
            f"오류 내용: {error_message}"
        )


    # --------------------------------------------------------
    # boxOfficeResult 확인
    # --------------------------------------------------------

    if "boxOfficeResult" not in data:

        return None, (
            "KOBIS 응답에 boxOfficeResult가 없습니다."
        )


    boxoffice = data["boxOfficeResult"]


    # --------------------------------------------------------
    # 영화 목록 가져오기
    # --------------------------------------------------------

    movies = boxoffice.get(
        "dailyBoxOfficeList",
        []
    )


    # 영화 목록이 없는 경우

    if not movies:

        return None, "EMPTY"


    return movies, None


# ============================================================
# 7. API 실행
# ============================================================

movies, error = get_boxoffice(
    target_date,
    API_KEY
)


# ============================================================
# 8. 영화 목록이 없는 경우
# ============================================================

if error == "EMPTY":

    st.warning(
        "📭 그날은 아직 집계 전입니다."
    )

    st.info(
        """
        선택한 날짜에는 박스오피스 데이터가 없습니다.

        다른 날짜를 선택해 보세요.
        """
    )

    st.stop()


# ============================================================
# 9. API 오류가 발생한 경우
# ============================================================

if error:

    st.error(
        "❌ 박스오피스 정보를 가져오지 못했습니다."
    )

    st.warning(
        f"""
        **API 오류 내용**

        {error}
        """
    )

    st.markdown("### 🔎 확인해 보세요")

    st.markdown(
        """
        - KOBIS 인증키가 올바른지 확인하세요.
        - Streamlit Cloud의 **Settings → Secrets**를 확인하세요.
        - `KOBIS_KEY`가 정확하게 입력되어 있는지 확인하세요.
        - 잠시 후 다시 시도해 보세요.
        """
    )

    st.stop()


# ============================================================
# 10. DataFrame으로 변환
# ============================================================

df = pd.DataFrame(
    movies
)


# ============================================================
# 11. 숫자 데이터 변환
# ============================================================
# KOBIS API에서는 숫자도 문자열 형태로 전달됩니다.
#
# 예:
# "12345" → 12345
#
# 숫자로 변환해야 정렬과 그래프에 사용할 수 있습니다.

number_columns = [
    "rank",
    "rankInten",
    "audiCnt",
    "audiAcc",
    "scrnCnt",
    "showCnt"
]

for column in number_columns:

    if column in df.columns:

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )


# ============================================================
# 12. KOBIS 공식 순위 기준으로 정렬
# ============================================================
# 가장 중요한 부분입니다.
#
# rank가
# 1 → 2 → 3 → 4 → 5
# 순서가 되도록 정렬합니다.

df = (
    df
    .sort_values(
        by="rank",
        ascending=True
    )
    .reset_index(drop=True)
)


# ============================================================
# 13. 영화명에 트로피 표시
# ============================================================
# 누적 관객수가 100만 명 이상이면 🏆를 붙입니다.

df["display_movie_name"] = df.apply(
    lambda row:
        f"{row['movieNm']} 🏆"
        if row["audiAcc"] >= 1_000_000
        else row["movieNm"],
    axis=1
)


# ============================================================
# 14. 순위 변동 표시
# ============================================================
#
# 양수 → 순위 상승 → 🔴 ↑
# 음수 → 순위 하락 → 🔵 ↓
# 0    → 변동 없음 → —
#
# 예:
# +2 → 🔴 ↑ 2
# -1 → 🔵 ↓ 1


def make_rank_change(value):

    if pd.isna(value):

        return "-"

    value = int(value)

    if value > 0:

        return f"🔴 ↑ {value}"

    elif value < 0:

        return f"🔵 ↓ {abs(value)}"

    else:

        return "—"


df["순위변동"] = df[
    "rankInten"
].apply(
    make_rank_change
)


# ============================================================
# 15. 1위 영화
# ============================================================
# 위에서 이미 rank 기준으로 정렬했기 때문에
# 첫 번째 행이 공식 박스오피스 1위입니다.

first_movie = df.iloc[0]


st.markdown("---")

st.header("🏆 1위 영화")

st.subheader(
    f"🥇 {first_movie['display_movie_name']}"
)


# ============================================================
# 16. 1위 영화 정보 카드
# ============================================================

col1, col2, col3 = st.columns(3)


with col1:

    st.metric(
        label="👥 해당일 관객수",
        value=f"{int(first_movie['audiCnt']):,}명"
    )


with col2:

    st.metric(
        label="🎟️ 누적 관객수",
        value=f"{int(first_movie['audiAcc']):,}명"
    )


with col3:

    st.metric(
        label="🖥️ 스크린 수",
        value=f"{int(first_movie['scrnCnt']):,}개"
    )


# ============================================================
# 17. 전체 박스오피스 표
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


# 열 이름을 한국어로 변경

table_df.columns = [
    "순위",
    "순위 변동",
    "영화명",
    "개봉일",
    "관객수",
    "누적관객",
    "스크린수"
]


# ============================================================
# 18. 표 출력
# ============================================================

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
# 19. 관객수 TOP 5 그래프
# ============================================================

st.markdown("---")

st.header("📊 관객수 TOP 5")


# ============================================================
# 20. KOBIS 순위 1~5위만 가져오기
# ============================================================
#
# 여기서는 절대로 audiCnt로 정렬하지 않습니다.
#
# 반드시
#
# 1위 → 2위 → 3위 → 4위 → 5위
#
# 순서 그대로 사용합니다.

top5 = (
    df
    .sort_values(
        by="rank",
        ascending=True
    )
    .head(5)
    .copy()
)


# ============================================================
# 21. 그래프용 데이터 만들기
# ============================================================

chart_df = top5[
    [
        "rank",
        "display_movie_name",
        "audiCnt"
    ]
].copy()


chart_df.columns = [
    "순위",
    "영화",
    "관객수"
]


# ============================================================
# 22. 순위 표시용 영화 이름
# ============================================================
# 그래프에서 영화명이 길면 알아보기 어렵기 때문에
# 순위를 함께 표시합니다.
#
# 예:
# 1위 오디세이
# 2위 영화B
# 3위 영화C
# ...

chart_df["표시이름"] = chart_df.apply(
    lambda row:
        f"{int(row['순위'])}위 {row['영화']}",
    axis=1
)


# ============================================================
# 23. 그래프에 표시될 순서를 직접 지정
# ============================================================
# Plotly는 category_orders를 이용하면
# x축의 순서를 원하는 대로 고정할 수 있습니다.
#
# 따라서 영화 이름을 가나다순으로 바꾸거나
# 관객수 크기순으로 다시 바꾸지 않습니다.

rank_order = chart_df[
    "표시이름"
].tolist()


# ============================================================
# 24. 관객수 막대그래프
# ============================================================

fig = px.bar(
    chart_df,

    x="표시이름",

    y="관객수",

    text="관객수",

    category_orders={
        "표시이름": rank_order
    },

    labels={
        "표시이름": "영화",
        "관객수": "관객수(명)"
    },

    title="관객수 TOP 5"
)


# ============================================================
# 25. 그래프 숫자 표시
# ============================================================

fig.update_traces(
    texttemplate="%{text:,}명",
    textposition="outside"
)


# y축 숫자를 천 단위로 표시

fig.update_yaxes(
    tickformat=","
)


# 그래프 크기

fig.update_layout(
    height=500,

    xaxis={
        "categoryorder": "array",
        "categoryarray": rank_order
    }
)


# ============================================================
# 26. 그래프 출력
# ============================================================

st.plotly_chart(
    fig,
    use_container_width=True
)


# ============================================================
# 27. TOP 5 관객수 숫자로도 표시
# ============================================================

st.markdown("#### 🎬 순위별 관객수")


for _, movie in top5.iterrows():

    st.write(
        f"**{int(movie['rank'])}위 "
        f"{movie['display_movie_name']}** "
        f"— {int(movie['audiCnt']):,}명"
    )


# ============================================================
# 28. 하단 안내
# ============================================================

st.markdown("---")

st.caption(
    f"📅 조회 날짜: {display_date}"
)

st.caption(
    "🏆 누적관객 100만 명 이상 영화에 트로피를 표시했습니다."
)

st.caption(
    "🔴 ↑ 순위 상승  |  🔵 ↓ 순위 하락  |  — 변동 없음"
)

st.caption(
    "KOBIS Open API 데이터를 이용하며, "
    "같은 날짜의 결과는 약 1시간 동안 캐시됩니다."
)
