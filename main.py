# ============================================================
# 🎬 어제의 박스오피스
# 영화진흥위원회(KOBIS) Open API를 이용한 Streamlit 앱
# ============================================================

import streamlit as st
import pandas as pd
import requests

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


# ------------------------------------------------------------
# 1. Streamlit 페이지 설정
# ------------------------------------------------------------

st.set_page_config(
    page_title="어제의 박스오피스",
    page_icon="🎬",
    layout="wide"
)


# ------------------------------------------------------------
# 2. 제목
# ------------------------------------------------------------

st.title("🎬 어제의 박스오피스")
st.caption("영화진흥위원회(KOBIS) 일일 박스오피스")


# ------------------------------------------------------------
# 3. 한국 시간 기준으로 '어제' 계산
# ------------------------------------------------------------
# Streamlit Cloud 서버는 한국 시간이 아닐 수 있기 때문에
# 반드시 Asia/Seoul을 기준으로 날짜를 계산합니다.

korea_now = datetime.now(ZoneInfo("Asia/Seoul"))

yesterday = korea_now - timedelta(days=1)

# KOBIS API가 요구하는 날짜 형식: YYYYMMDD
target_date = yesterday.strftime("%Y%m%d")

# 화면에 보여줄 날짜
display_date = yesterday.strftime("%Y년 %m월 %d일")

st.subheader(f"📅 {display_date} 박스오피스")


# ------------------------------------------------------------
# 4. Secrets에서 KOBIS 인증키 가져오기
# ------------------------------------------------------------
# 실제 인증키를 코드에 직접 작성하지 않습니다.
#
# Streamlit Cloud
# → Settings
# → Secrets
#
# 에서 다음과 같이 입력합니다.
#
# KOBIS_KEY = "본인의_인증키"
# ------------------------------------------------------------

try:
    API_KEY = st.secrets["KOBIS_KEY"]

except Exception:
    st.error("🔑 KOBIS 인증키를 찾을 수 없습니다.")

    st.info(
        """
        **Streamlit Cloud에서 다음을 확인하세요.**

        `Settings → Secrets`

        아래와 같은 형식으로 입력되어 있어야 합니다.

        `KOBIS_KEY = "본인의 KOBIS 인증키"`

        인증키를 코드에 직접 넣을 필요는 없습니다.
        """
    )

    st.stop()


# ------------------------------------------------------------
# 5. KOBIS API 호출 함수
# ------------------------------------------------------------
# ttl=3600
# → 같은 날짜의 결과를 1시간 동안 기억합니다.
# → 1시간 안에 같은 날짜를 다시 요청하면 API를 다시 호출하지 않습니다.
# ------------------------------------------------------------

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
        return None, f"API 요청 중 오류가 발생했습니다: {e}"

    # --------------------------------------------------------
    # HTTP 상태 확인
    # --------------------------------------------------------

    if response.status_code != 200:
        return None, (
            f"KOBIS 서버에서 HTTP {response.status_code} "
            "응답을 반환했습니다."
        )

    # --------------------------------------------------------
    # JSON 변환
    # --------------------------------------------------------

    try:
        data = response.json()

    except ValueError:
        return None, (
            "KOBIS에서 JSON 형식의 데이터를 받지 못했습니다."
        )

    # --------------------------------------------------------
    # 중요!
    # 인증키가 틀려도 HTTP 상태코드는 200일 수 있습니다.
    # 이 경우 faultInfo가 들어옵니다.
    # --------------------------------------------------------

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
    # boxOfficeResult가 있는지 확인
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

    if not movies:

        return None, (
            "조회된 영화 목록이 없습니다."
        )

    return movies, None


# ------------------------------------------------------------
# 6. API 실행
# ------------------------------------------------------------

movies, error = get_boxoffice(
    target_date,
    API_KEY
)


# ------------------------------------------------------------
# 7. 오류가 발생했을 때
# ------------------------------------------------------------

if error:

    st.error("❌ 박스오피스 정보를 가져오지 못했습니다.")

    st.warning(
        f"""
        **API 오류 내용**

        {error}
        """
    )

    st.markdown("### 🔎 확인해 보세요")

    st.markdown(
        """
        **① KOBIS 인증키 확인**

        Streamlit Cloud의  
        `Settings → Secrets`에서

        `KOBIS_KEY = "인증키"`

        형식으로 등록되어 있는지 확인하세요.


        **② 인증키가 정확한지 확인**

        KOBIS에서 발급받은 인증키를 다시 확인하세요.


        **③ 조회 날짜 확인**

        현재 앱은 한국 시간 기준으로 **어제** 날짜를 자동으로 조회합니다.


        **④ 잠시 후 다시 시도**

        KOBIS API 서버의 일시적인 문제일 수도 있습니다.
        """
    )

    st.caption(
        f"현재 한국 시간 기준 조회 날짜: {target_date}"
    )

    st.stop()


# ------------------------------------------------------------
# 8. DataFrame으로 변환
# ------------------------------------------------------------

df = pd.DataFrame(movies)


# ------------------------------------------------------------
# 9. 숫자 데이터를 숫자로 변환
# ------------------------------------------------------------
# KOBIS API에서는 숫자도 문자열로 전달됩니다.
#
# 예:
# "12345" → 12345
#
# 이렇게 변환해야 정렬과 그래프에서 제대로 사용할 수 있습니다.
# ------------------------------------------------------------

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


# ------------------------------------------------------------
# 10. 순위순으로 정렬
# ------------------------------------------------------------

df = df.sort_values(
    by="rank"
).reset_index(drop=True)


# ------------------------------------------------------------
# 11. 1위 영화
# ------------------------------------------------------------

first_movie = df.iloc[0]

first_movie_name = first_movie["movieNm"]

st.markdown("---")

st.header("🏆 어제의 1위")

st.subheader(
    f"🥇 {first_movie_name}"
)


# ------------------------------------------------------------
# 12. 1위 영화 지표 카드 3개
# ------------------------------------------------------------

col1, col2, col3 = st.columns(3)


with col1:

    st.metric(
        label="👥 어제 관객수",
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


# ------------------------------------------------------------
# 13. 전체 박스오피스 표
# ------------------------------------------------------------

st.markdown("---")

st.header("📋 전체 박스오피스")


# 필요한 열만 선택
table_df = df[
    [
        "rank",
        "movieNm",
        "openDt",
        "audiCnt",
        "audiAcc",
        "scrnCnt"
    ]
].copy()


# 표에서 보기 좋은 이름으로 변경
table_df.columns = [
    "순위",
    "영화명",
    "개봉일",
    "관객수",
    "누적관객",
    "스크린수"
]


# 숫자를 보기 좋게 표시하기 위한 포맷
# 실제 DataFrame의 데이터는 숫자로 유지됩니다.

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


# ------------------------------------------------------------
# 14. 관객수 TOP 5
# ------------------------------------------------------------

st.markdown("---")

st.header("📊 관객수 TOP 5")


# 관객수가 많은 순서로 5편 선택
top5 = (
    df
    .nlargest(5, "audiCnt")
    .copy()
)


# 그래프에서 영화명이 위쪽부터 보이도록
top5 = top5.sort_values(
    "audiCnt",
    ascending=True
)


# ------------------------------------------------------------
# 15. Streamlit 기본 막대그래프
# ------------------------------------------------------------
# 별도의 그래프 라이브러리를 사용하지 않고
# Streamlit의 기본 그래프를 사용합니다.

chart_df = top5[
    ["movieNm", "audiCnt"]
].set_index("movieNm")


st.bar_chart(
    chart_df,
    x_label="영화",
    y_label="관객수(명)"
)


# ------------------------------------------------------------
# 16. TOP 5 숫자도 함께 표시
# ------------------------------------------------------------

st.markdown("#### TOP 5 관객수")

for _, movie in top5.sort_values(
    "audiCnt",
    ascending=False
).iterrows():

    st.write(
        f"**{int(movie['rank'])}위 {movie['movieNm']}** "
        f"— {int(movie['audiCnt']):,}명"
    )


# ------------------------------------------------------------
# 17. 안내
# ------------------------------------------------------------

st.markdown("---")

st.caption(
    f"📌 한국 시간 기준 조회 날짜: {display_date}"
)

st.caption(
    "KOBIS Open API 데이터를 이용하며, "
    "같은 날짜의 데이터는 약 1시간 동안 캐시됩니다."
)
