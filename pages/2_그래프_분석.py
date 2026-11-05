import streamlit as st
import pandas as pd


# 분석 및 시각화를 담당하는 클래스 정의
class SurveyAnalyzer:
    def __init__(self, df_clean, df_raw=None):
        self.df_clean = df_clean.copy()
        self.df_raw = df_raw.copy() if df_raw is not None else None
        self._calculate_scores()

    # AI 윤리의식 점수 산출 로직
    def _calculate_scores(self):
        # Q6(역문항 원본)을 제외하고, 정제 페이지에서 생성된 Q6R 등을 포함한 모든 Q문항 추출
        q_cols = [col for col in self.df_clean.columns if str(col).startswith('Q') and col != 'Q6']

        # Q문항들이 존재할 경우 평균을 내어 'AI윤리의식' 열 생성
        if q_cols:
            # pd.to_numeric을 통해 문자를 숫자로 변환 후 평균 계산
            for col in q_cols:
                self.df_clean[col] = pd.to_numeric(self.df_clean[col], errors='coerce')
            self.df_clean['AI윤리의식'] = self.df_clean[q_cols].mean(axis=1)
        else:
            self.df_clean['AI윤리의식'] = 0

    # 1. 요약 지표 출력 함수
    def render_summary(self):
        st.subheader("1. 요약 지표")
        col1, col2, col3 = st.columns(3)

        valid_count = len(self.df_clean)
        avg_time = self.df_clean['AI사용시간'].mean() if 'AI사용시간' in self.df_clean.columns else 0
        avg_score = self.df_clean['AI윤리의식'].mean()

        col1.metric("유효 응답", f"{valid_count}명")
        col2.metric("평균 AI 사용 시간", f"{avg_time:.1f}분")
        col3.metric("AI윤리의식 평균", f"{avg_score:.2f}점")

    # 2. 정제 전후 비교 차트 출력 함수
    def render_comparison(self):
        st.subheader("2. 정제 전후 비교 (단과대학별 응답자 수)")

        # 원본 데이터가 존재할 경우에만 비교 차트 생성
        if self.df_raw is not None and '소속단과대학' in self.df_raw.columns:
            # 동일한 기준으로 단과대학 분류 (정제 페이지의 로직 약식 적용)
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

            self.df_raw['소속단과대학_정제'] = self.df_raw['소속단과대학'].apply(parse_college)

            # 정제 전/후 빈도수 집계
            raw_counts = self.df_raw['소속단과대학_정제'].value_counts().rename("정제 전")
            clean_counts = self.df_clean['소속단과대학'].value_counts().rename("정제 후")

            # 두 데이터를 병합하여 차트용 데이터프레임 생성
            comp_df = pd.concat([raw_counts, clean_counts], axis=1).fillna(0)

            # 한글 텍스트 가독성을 위해 가로 막대 차트로 나란히 표시
            st.bar_chart(comp_df, horizontal=True)
        else:
            st.info("왼쪽 사이드바에서 원본 데이터를 업로드하시면 정제 전후 비교 차트를 확인하실 수 있습니다.")

    # 3. 4개의 분석 탭 출력 함수
    def render_tabs(self):
        st.subheader("3. 상세 분석")
        tab1, tab2, tab3, tab4 = st.tabs(["응답자 구성", "문항별 평균", "집단 비교", "사용 시간과 점수"])

        # [탭 1] 응답자 구성 (가로 막대 및 세로 막대)
        with tab1:
            st.write("단과대학별 응답자 수")
            college_counts = self.df_clean['소속단과대학'].value_counts()
            st.bar_chart(college_counts, horizontal=True)

            st.write("학년별 응답자 수")
            grade_counts = self.df_clean['학년'].value_counts().sort_index()
            st.bar_chart(grade_counts)

        # [탭 2] 문항별 평균 (가로 막대)
        with tab2:
            st.write("문항별 평균 점수")
            q_cols = [col for col in self.df_clean.columns if str(col).startswith('Q') and col != 'Q6']
            if q_cols:
                q_means = self.df_clean[q_cols].mean()
                st.bar_chart(q_means, horizontal=True)
            else:
                st.write("분석할 문항(Q1~Q6R)이 존재하지 않습니다.")

        # [탭 3] 집단 비교 (데이터프레임 표 출력)
        with tab3:
            st.write("학년별 AI윤리의식 비교")
            # 학년별 그룹화 후 인원수와 평균점수 산출
            grade_group = self.df_clean.groupby('학년')['AI윤리의식'].agg(['count', 'mean']).rename(
                columns={'count': '인원 수', 'mean': '평균 점수'})
            grade_group['평균 점수'] = grade_group['평균 점수'].round(2)  # 소수점 둘째 자리 반올림
            st.dataframe(grade_group, use_container_width=True)

            st.write("단과대학별 AI윤리의식 비교")
            # 단과대학별 그룹화 후 인원수와 평균점수 산출
            college_group = self.df_clean.groupby('소속단과대학')['AI윤리의식'].agg(['count', 'mean']).rename(
                columns={'count': '인원 수', 'mean': '평균 점수'})
            college_group['평균 점수'] = college_group['평균 점수'].round(2)  # 소수점 둘째 자리 반올림
            st.dataframe(college_group, use_container_width=True)

        # [탭 4] 사용 시간과 점수 (산점도 차트)
        with tab4:
            st.write("AI 사용 시간과 AI윤리의식 점수의 관계 (산점도)")
            if 'AI사용시간' in self.df_clean.columns:
                st.scatter_chart(data=self.df_clean, x='AI사용시간', y='AI윤리의식')
            else:
                st.write("AI사용시간 데이터가 없습니다.")


# 앱 메인 실행 함수
def main():
    st.set_page_config(page_title="그래프 분석", layout="wide")
    st.title("설문 데이터 그래프 분석")

    # 세션 상태에서 정제된 데이터 가져오기
    df_clean = st.session_state.get("clean_df", None)
    df_raw = None

    # 사이드바: 1페이지에서 원본을 세션에 넣지 않으므로, 정제 전후 비교를 원할 경우 업로드하도록 안내
    st.sidebar.write("정제 전후 비교용 데이터")
    raw_file = st.sidebar.file_uploader("원본 CSV 파일 업로드 (선택)", type=['csv'])
    if raw_file:
        df_raw = pd.read_csv(raw_file)

    # 데이터가 세션에 없는 경우 안내 및 파일 업로드 제공
    if df_clean is None:
        st.warning("정제된 데이터가 없습니다. 먼저 '1_데이터_정제' 페이지를 실행하거나 아래에 정제된 CSV를 업로드해주세요.")
        clean_file = st.file_uploader("정제된 CSV 파일 업로드", type=['csv'])
        if clean_file:
            df_clean = pd.read_csv(clean_file)
        else:
            st.stop()  # 데이터가 없으면 앱 실행 중단

    # 데이터가 존재할 경우 클래스 인스턴스화 및 분석 화면 렌더링
    if df_clean is not None:
        analyzer = SurveyAnalyzer(df_clean, df_raw)

        analyzer.render_summary()
        st.divider()

        analyzer.render_comparison()
        st.divider()

        analyzer.render_tabs()


if __name__ == "__main__":
    main()