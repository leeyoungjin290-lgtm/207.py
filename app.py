
# ──────────────────────────────────────────────
# 과거 날짜별 상승/하락 추세 계산
# ──────────────────────────────────────────────
def add_historical_trends(df: pd.DataFrame) -> pd.DataFrame:
    """각 거래일 당시 확인할 수 있었던 정보만으로 추세 점수를 계산."""
    df = df.copy()

    conditions = [
        df["Close"] > df["MA20"],
        df["Close"] > df["MA60"],
        df["Close"] > df["MA120"],
        df["MA20"] > df["MA60"],
        df["MA60"] > df["MA120"],
        df["MA60"] > df["MA60"].shift(20),
    ]

    df["TrendScore"] = sum(
        condition.fillna(False).astype(int)
        for condition in conditions
    )

    labels = {
        0: "하락장",
        1: "하락장",
        2: "약한 하락",
        3: "횡보 / 혼조",
        4: "약한 상승",
        5: "상승장",
        6: "상승장",
    }

    df["TrendLabel"] = df["TrendScore"].map(labels)

    return df


def show_historical_trends(df: pd.DataFrame, key: str):
    """과거 추세 차트, 날짜별 판정, 과거 판단 근거 표시."""
    history = add_historical_trends(add_indicators(df))
    history = history.dropna(subset=["MA120"]).copy()

    if history.empty:
        st.warning("과거 추세를 계산할 데이터가 부족합니다.")
        return

    st.subheader("📅 과거 상승장·하락장 확인")

    min_date = history.index[0].date()
    max_date = history.index[-1].date()

    selected_date = st.date_input(
        "확인할 날짜",
        value=max_date,
        min_value=min_date,
        max_value=max_date,
        key=f"{key}_history_date",
    )

    # 선택한 날짜 또는 그 이전의 가장 가까운 거래일을 사용
    selected = history.loc[
        history.index.date <= selected_date
    ]

    if selected.empty:
        st.warning("선택한 날짜의 분석 데이터가 없습니다.")
        return

    current = selected.iloc[-1]
    actual_date = selected.index[-1]

    label, icon, color = label_from_score(
        int(current["TrendScore"])
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("판정 날짜", actual_date.strftime("%Y-%m-%d"))
    c2.metric("당시 종가", f"{current['Close']:,.0f}")
    c3.metric(
        "당시 추세 점수",
        f"{int(current['TrendScore'])} / 6",
        label,
    )

    st.markdown(
        f"""
        <div style="
            padding:16px;
            border:2px solid {color};
            border-radius:12px;
            text-align:center;
            background:{color}15;
        ">
            <div style="font-size:28px;font-weight:800;color:{color}">
                {icon} 당시 판정: {label}
            </div>
            <div>선택한 날짜까지의 데이터만으로 계산한 결과</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 날짜별 추세 점수 그래프
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=history.index,
            y=history["TrendScore"],
            mode="lines",
            name="추세 점수",
            line=dict(color="#2563eb", width=2),
            hovertemplate=(
                "날짜: %{x|%Y-%m-%d}<br>"
                "점수: %{y}/6<extra></extra>"
            ),
        )
    )

    fig.add_hline(y=4.5, line_dash="dash", line_color="#16a34a")
    fig.add_hline(y=3.5, line_dash="dot", line_color="#65a30d")
    fig.add_hline(y=2.5, line_dash="dash", line_color="#ca8a04")
    fig.add_hline(y=1.5, line_dash="dot", line_color="#dc2626")

    fig.add_vline(
        x=actual_date,
        line_dash="dash",
        line_color="#7c3aed",
    )

    fig.update_layout(
        title="날짜별 추세 점수 변화",
        xaxis_title="날짜",
        yaxis_title="추세 점수 (6점 만점)",
        yaxis=dict(range=[-0.2, 6.2], dtick=1),
        height=380,
        margin=dict(l=10, r=10, t=50, b=10),
        hovermode="x unified",
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        key=f"{key}_history_chart",
    )

    with st.expander("📋 최근 거래일별 추세 기록"):
        table = history.tail(60).copy()
        table.index = table.index.strftime("%Y-%m-%d")
        table.index.name = "날짜"

        table = table.rename(
            columns={
                "Close": "종가",
                "TrendScore": "추세 점수",
                "TrendLabel": "추세 판정",
            }
        )

        st.dataframe(
            table[["종가", "추세 점수", "추세 판정"]].sort_index(
                ascending=False
            ),
            use_container_width=True,
        )

    with st.expander("🔎 선택한 날짜의 판정 근거"):
        checks = [
            (current["Close"] > current["MA20"], "종가가 20일선 위"),
            (current["Close"] > current["MA60"], "종가가 60일선 위"),
            (current["Close"] > current["MA120"], "종가가 120일선 위"),
            (current["MA20"] > current["MA60"], "20일선이 60일선 위"),
            (current["MA60"] > current["MA120"], "60일선이 120일선 위"),
            (
                current["MA60"] > history["MA60"].shift(20).loc[actual_date]
                if actual_date in history.index
                and pd.notna(history["MA60"].shift(20).loc[actual_date])
                else False,
                "60일선이 20거래일 전보다 상승",
            ),
        ]

        for ok, description in checks:
            st.write(("✅ " if ok else "❌ ") + description)
