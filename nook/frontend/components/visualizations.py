"""
データ視覚化コンポーネント。
ダッシュボード用の各種チャートやグラフを提供します。
"""

import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, List, Any
import random

def render_topic_chart(items: List[Dict[str, Any]]):
    """
    トピック分布の円グラフを表示します。
    
    Parameters
    ----------
    items : List[Dict[str, Any]]
        コンテンツアイテムのリスト
    """
    st.subheader("トピック分布")
    
    # 実際のデータがない場合はダミーデータを生成
    topics = ["テクノロジー", "AI", "プログラミング", "データサイエンス", "ビジネス"]
    counts = [random.randint(1, 10) for _ in range(len(topics))]
    
    # データフレームの作成
    df = pd.DataFrame({
        "トピック": topics,
        "件数": counts
    })
    
    # Plotlyで円グラフを作成
    fig = px.pie(
        df, 
        values="件数", 
        names="トピック",
        color_discrete_sequence=px.colors.sequential.Blues_r,
        hole=0.4
    )
    
    fig.update_layout(
        margin=dict(l=20, r=20, t=30, b=20),
        height=300,
        legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5)
    )
    
    st.plotly_chart(fig, use_container_width=True)

def render_sentiment_gauge(items: List[Dict[str, Any]]):
    """
    感情分析のゲージチャートを表示します。
    
    Parameters
    ----------
    items : List[Dict[str, Any]]
        コンテンツアイテムのリスト
    """
    st.subheader("感情分析")
    
    # ダミーの感情スコア（-1から1の範囲）
    sentiment_score = random.uniform(-0.5, 0.8)
    
    # ゲージチャートの作成
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=(sentiment_score + 1) * 50,  # -1〜1の範囲を0〜100に変換
        title={"text": "感情スコア"},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1},
            "bar": {"color": "#1E88E5"},
            "steps": [
                {"range": [0, 33], "color": "#EF5350"},
                {"range": [33, 66], "color": "#FFCA28"},
                {"range": [66, 100], "color": "#66BB6A"}
            ],
            "threshold": {
                "line": {"color": "black", "width": 4},
                "thickness": 0.75,
                "value": (sentiment_score + 1) * 50
            }
        }
    ))
    
    fig.update_layout(
        height=300,
        margin=dict(l=20, r=20, t=30, b=20)
    )
    
    st.plotly_chart(fig, use_container_width=True)

def render_activity_timeline(items: List[Dict[str, Any]]):
    """
    アクティビティタイムラインを表示します。
    
    Parameters
    ----------
    items : List[Dict[str, Any]]
        コンテンツアイテムのリスト
    """
    st.subheader("アクティビティタイムライン")
    
    # ダミーのタイムラインデータ
    hours = list(range(24))
    activity = [random.randint(0, 10) for _ in range(24)]
    
    # データフレームの作成
    df = pd.DataFrame({
        "時間": hours,
        "アクティビティ": activity
    })
    
    # Altairでチャートを作成
    chart = alt.Chart(df).mark_line(point=True).encode(
        x=alt.X('時間:Q', title='時間'),
        y=alt.Y('アクティビティ:Q', title='アクティビティ'),
        tooltip=['時間', 'アクティビティ']
    ).properties(
        height=250
    ).interactive()
    
    st.altair_chart(chart, use_container_width=True) 