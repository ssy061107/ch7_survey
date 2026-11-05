import streamlit as st
import pandas as pd
import re
import io

st.set_page_config(page_title="데이터 정제", page_icon="🧹", layout="wide")

st.title("🧹 설문 데이터 정제")

# -----------------
# 1. 사이드바 설정
# -----------------
st.sidebar.header("⚙️ 정제 옵션 설정")
max_time = st.sidebar.slider("AI 사용 시간 이상치 허용 범위 (최대 분)", min_value=0, max_value=600, value=300, step=10)
missing_action = st.sidebar.radio("빈칸(결측치) 처리 방법", ["그대로 두기", "행 삭제"])

# -----------------
# 2. 데이터 업로드
# -----------------
uploaded_file = st.file_uploader("구글 설문지 CSV 파일(survey_raw.csv)을 업로드하세요.", type=['csv'])

if uploaded_file is not None:
    # 원본 데이터 로드
    df_raw = pd.read_csv(uploaded_file)

    st.subheader("원본 데이터 확인")
    st.write(f"**총 응답자 수:** {len(df_raw)}명")
    st.dataframe(df_raw, use_container_width=True)

    # -----------------
    # 3. 데이터 정제 로직
    # -----------------
    df_clean = df_raw.copy()

    # 정제 과정 기록용 딕셔너리
    log_data = {"단계": [], "설명": [], "남은 데이터 수": []}
    log_data["단계"].append("0. 원본 로드")
    log_data["설명"].append("업로드된 초기 데이터")
    log_data["남은 데이터 수"].append(len(df_clean))

    # [조건 1] 열 제목 줄이기
    # 설문 문항 순서에 맞춰 열 이름 변경 (타임스탬프 제외 11개 문항 기준)
    new_cols = ["타임스탬프", "성별", "학년", "소속단과대학", "AI사용시간", "Q1(활용)", "Q2(신뢰)", "Q3(학업정직성)", "Q4(개인정보)", "Q5(자율성)", "Q6(정직성역)", "서술형"]
    # 실제 데이터 열 개수에 맞춰 슬라이싱하여 적용
    df_clean.columns = new_cols[:len(df_clean.columns)]

    # [조건 2] 중복 응답 제거 (타임스탬프 제외한 모든 열 기준)
    check_cols = df_clean.columns.difference(['타임스탬프'])
    df_clean = df_clean.drop_duplicates(subset=check_cols, keep='first')
    log_data["단계"].append("1. 중복 제거")
    log_data["설명"].append("타임스탬프 제외 내용 완전 동일 행 첫 행만 유지")
    log_data["남은 데이터 수"].append(len(df_clean))


    # [조건 3] 학년 표기 통일
    def parse_grade(val):
        val_str = str(val).replace('일', '1').replace('이', '2').replace('삼', '3').replace('사', '4')
        num = re.sub(r'\D', '', val_str)  # 숫자만 추출
        return int(num) if num else None


    df_clean['학년'] = df_clean['학년'].apply(parse_grade)


    # [조건 4] 단과대학 표기 통일
    def parse_college(val):
        val_str = str(val)
        if '인문' in val_str:
            return '인문대학'
        elif '사과' in val_str or '사회' in val_str:
            return '사회과학대학'
        elif '경통' in val_str or '경제' in val_str:
            return '경제통상대학'
        elif '경영' in val_str:
            return '경영대학'
        elif '사범' in val_str:
            return '사범대학'
        else:
            return '기타'


    df_clean['소속단과대학'] = df_clean['소속단과대학'].apply(parse_college)


    # [조건 5] 이상치 (AI사용시간 분 단위 통일 및 허용범위 필터링)
    def parse_time(val):
        val_str = str(val).replace(' ', '')
        hours, mins = 0, 0
        h_match = re.search(r'(\d+)시간', val_str)
        if h_match: hours = int(h_match.group(1))
        m_match = re.search(r'(\d+)분', val_str)
        if m_match: mins = int(m_match.group(1))

        if not h_match and not m_match:  # '시간', '분' 글자가 없는 경우 숫자만 추출
            num = re.sub(r'\D', '', val_str)
            return int(num) if num else 0
        return hours * 60 + mins


    df_clean['AI사용시간'] = df_clean['AI사용시간'].apply(parse_time)
    df_clean = df_clean[df_clean['AI사용시간'] <= max_time]  # 사이드바 필터 적용

    log_data["단계"].append("2. 이상치 처리")
    log_data["설명"].append(f"AI 사용 시간 {max_time}분 초과 행 제거")
    log_data["남은 데이터 수"].append(len(df_clean))

    # [조건 6] 결측치 처리
    st.sidebar.markdown("---")
    st.sidebar.write("🔍 **열별 빈칸(결측치) 수**")
    st.sidebar.dataframe(df_clean.isnull().sum().rename("결측치 개수"))

    if missing_action == "행 삭제":
        df_clean = df_clean.dropna()
        log_data["단계"].append("3. 결측치 처리")
        log_data["설명"].append("결측치가 포함된 행 모두 삭제")
        log_data["남은 데이터 수"].append(len(df_clean))

    # [조건 7] 역문항 점수 재계산 (Q6R = 6 - Q6)
    if 'Q6' in df_clean.columns:
        df_clean['Q6'] = pd.to_numeric(df_clean['Q6'], errors='coerce')
        df_clean['Q6R'] = 6 - df_clean['Q6']
        # 보기 편하게 Q6 바로 뒤에 Q6R 배치
        cols = list(df_clean.columns)
        q6_idx = cols.index('Q6')
        cols.insert(q6_idx + 1, cols.pop(cols.index('Q6R')))
        df_clean = df_clean[cols]

    # -----------------
    # 4. 정제 결과 출력
    # -----------------
    st.markdown("---")
    st.subheader("✨ 데이터 정제 결과")

    # 카드 형태로 요약 정보 표시
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("원본 데이터 수", f"{len(df_raw)} 건")
    with col2:
        st.metric("최종 데이터 수", f"{len(df_clean)} 건")
    with col3:
        st.metric("삭제된 데이터 수", f"{len(df_raw) - len(df_clean)} 건")

    # 정제 기록 표 표시
    log_df = pd.DataFrame(log_data)
    st.write("📝 **정제 단계별 기록**")
    st.dataframe(log_df, use_container_width=True)

    st.write("📊 **최종 정제 데이터**")
    st.dataframe(df_clean, use_container_width=True)

    # -----------------
    # 5. 세션 저장 및 다운로드
    # -----------------
    # 세션 상태(session_state)에 저장하여 다른 페이지(탐색적 분석 등)에서 재사용 가능하게 함
    st.session_state["clean_df"] = df_clean

    # CSV 다운로드 버튼
    csv = df_clean.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 정제된 데이터 CSV로 다운로드",
        data=csv,
        file_name="survey_cleaned.csv",
        mime="text/csv",
    )