import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# Load the dataset
url = "https://raw.githubusercontent.com/masterworker/repair_dashboard/refs/heads/main/final_data01.csv"

df = pd.read_csv(url, encoding='utf-8-sig', low_memory=False)

# Ensure the correct columns exist
required_columns = ['일자', '총괄국', '우체국', '차량번호', '수리금액', '핵심단어(최종)', '구매일자', '총주행거리', '관리국명']
missing_columns = [col for col in required_columns if col not in df.columns]
if missing_columns:
    st.error(f"데이터 파일에 다음 열이 없습니다: {', '.join(missing_columns)}. 파일을 확인해 주세요.")
else:
    # Streamlit dashboard with selectbox for full screen tabs
    st.title("이륜차 관리 대시보드")
    selected_tab = st.selectbox("대시보드를 선택하세요", ["수리 내역 대시보드", "이륜차 교체대상 선정 대시보드"])

    if selected_tab == "수리 내역 대시보드":
        st.header("수리 내역 분석")

        # Sidebar for user inputs
        st.sidebar.header("필터 선택")

        # Date range selection
        date_range = st.sidebar.slider(
            "기간 선택",
            min_value=pd.to_datetime("2022-01-01").date(),
            max_value=pd.to_datetime("2024-10-31").date(),
            value=(pd.to_datetime("2022-01-01").date(), pd.to_datetime("2024-10-31").date()),
            format="YYYY-MM"
        )

        # Filter data by date range
        df['일자'] = pd.to_datetime(df['일자'], errors='coerce')
        df = df.dropna(subset=['일자'])  # Drop rows where '일자' could not be converted
        df = df[(df['일자'].dt.date >= date_range[0]) & (df['일자'].dt.date <= date_range[1])]

        # 총괄국 selection
        total_office = st.sidebar.selectbox("총괄국 선택", options=["전체"] + sorted(df['총괄국'].dropna().unique().tolist()))
        if total_office != "전체":
            df = df[df['총괄국'] == total_office]

        # 우체국 selection
        post_office_options = ["전체"] + sorted(df['우체국'].dropna().unique().tolist())
        post_office = st.sidebar.selectbox("우체국 선택", options=post_office_options)
        if post_office != "전체":
            df = df[df['우체국'] == post_office]

        # 차량번호 selection
        vehicle_options = ["전체"] + sorted(df['차량번호'].dropna().unique().tolist())
        vehicle = st.sidebar.selectbox("차량번호 선택", options=vehicle_options)
        if vehicle != "전체":
            df = df[df['차량번호'] == vehicle]

        # Analysis button
        if st.sidebar.button("분석하기"):
            # Visualization 1: Monthly repair cost
            df_monthly = df.resample('M', on='일자').sum(numeric_only=True)['수리금액'].reset_index()
            avg_repair_cost = df_monthly['수리금액'].mean()

            fig_bar = px.bar(
                df_monthly,
                x='일자',
                y='수리금액',
                title='월별 수리금액',
                labels={'일자': '월', '수리금액': '수리금액 (원)'}
            )
            fig_bar.add_scatter(
                x=df_monthly['일자'],
                y=[avg_repair_cost] * len(df_monthly),
                mode='lines',
                name='평균 수리금액',
                line=dict(dash='dot', color='red')
            )
            st.plotly_chart(fig_bar)

            # Visualization 2: Pie chart of repair details by count
            repair_counts = df['핵심단어(최종)'].value_counts().reset_index()
            repair_counts.columns = ['핵심단어(최종)', '횟수']

            fig_pie_count = px.pie(
                repair_counts,
                names='핵심단어(최종)',
                values='횟수',
                title='선택된 기간의 수리 내역 비율 (횟수 기준)'
            )
            st.plotly_chart(fig_pie_count)

            # Visualization 3: Pie chart of repair details by cost
            repair_costs = df.groupby('핵심단어(최종)')['수리금액'].sum().reset_index()
            repair_costs.columns = ['핵심단어(최종)', '수리금액']

            fig_pie_cost = px.pie(
                repair_costs,
                names='핵심단어(최종)',
                values='수리금액',
                title='선택된 기간의 수리 내역 비율 (수리금액 기준)'
            )
            st.plotly_chart(fig_pie_cost)

            st.write("분석 결과가 위에 표시됩니다.")

        # 특정 차량번호가 선택되었고 엔진 수리 내역이 있는 경우에만 이미지 표시
        if vehicle != "전체":
            selected_vehicle_data = df[df['차량번호'] == vehicle]
            if not selected_vehicle_data.empty and '엔진수리' in selected_vehicle_data['핵심단어(최종)'].values:
                st.subheader(f"{vehicle} 차량 엔진 수리 관련 참고 자료")

                col1, col2 = st.columns(2)

                with col1:
                    st.image("https://raw.githubusercontent.com/masterworker/repair_dashboard/refs/heads/main/1.png", caption=f"{vehicle} 엔진 수리 가이드 1")

                with col2:
                    st.image("https://raw.githubusercontent.com/masterworker/repair_dashboard/refs/heads/main/2.png", caption=f"{vehicle} 엔진 수리 가이드 2")
            else:
                st.warning(f"{vehicle} 차량에 대한 엔진 수리 내역이 없습니다.")

    elif selected_tab == "이륜차 교체대상 선정 대시보드":
        st.header("이륜차 교체대상 선정 대시보드")

        # Filter out 폐기차량
        df = df[df['관리국명'] != '폐기차량']
        df = df.dropna(subset=['총주행거리'])

        # Remove duplicate vehicle numbers, keeping only the first occurrence
        df = df.drop_duplicates(subset=['차량번호'], keep='first')

        # Calculate '내용년수'
        df['구매일자'] = pd.to_datetime(df['구매일자'], errors='coerce')
        current_date = pd.to_datetime(datetime.now())
        df['내용년수'] = ((current_date - df['구매일자']).dt.days // 30).fillna(0).astype(int)

        # Calculate '교체점수'
        df['총주행거리'] = pd.to_numeric(df['총주행거리'], errors='coerce').fillna(0)
        df['교체점수'] = 0
        df['교체점수'] += (df['내용년수'] - 36).apply(lambda x: x if x > 0 else x * 3)
        df['교체점수'] += ((df['총주행거리'] - 25000) / 1000).apply(lambda x: x if x > 0 else x * 2).astype(int)

        # Sort vehicles by '교체점수' descending
        df = df.sort_values(by='교체점수', ascending=False)

        # Input for number of vehicles to replace
        replace_count = st.number_input("교체 대상 대수 입력", min_value=1, max_value=len(df), value=5, step=1)

        # Display replacement list
        replacement_list = df.head(replace_count)[['총괄국', '우체국', '차량번호', '내용년수', '총주행거리', '교체점수']]
        replacement_list.index = range(1, len(replacement_list) + 1)
        st.write("교체 대상 차량 목록:")
        st.dataframe(replacement_list)
