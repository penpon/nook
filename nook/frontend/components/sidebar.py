"""
サイドバーコンポーネント。
ソースと日付の選択UIを提供します。
"""

import streamlit as st
from datetime import datetime, timedelta
import os
from typing import Tuple

from nook.frontend.utils.api_client import APIClient

def render_sidebar() -> Tuple[str, str]:
    """
    サイドバーを表示します。
    
    Returns
    -------
    Tuple[str, str]
        選択されたソースと日付のタプル
    """
    st.sidebar.title("Nook")
    st.sidebar.caption("パーソナル情報ハブ")
    
    # ソース選択
    sources = {
        "all": "すべて",
        "reddit": "Reddit",
        "hackernews": "Hacker News",
        "github": "GitHub Trending",
        "techfeed": "Tech Feed",
        "paper": "論文"
    }
    
    selected_source = st.sidebar.selectbox(
        "情報ソース",
        options=list(sources.keys()),
        format_func=lambda x: sources.get(x, x)
    )
    
    # 利用可能な日付を取得
    available_dates = _get_available_dates(selected_source)
    
    if not available_dates:
        st.sidebar.warning("利用可能なデータがありません。")
        selected_date = datetime.now().strftime("%Y-%m-%d")
    else:
        selected_date = st.sidebar.selectbox(
            "日付",
            options=available_dates,
            index=0
        )
    
    # 天気情報
    st.sidebar.markdown("---")
    _render_weather_widget()
    
    return selected_source, selected_date

def _get_available_dates(source: str) -> list:
    """
    指定されたソースで利用可能な日付のリストを取得します。
    
    Parameters
    ----------
    source : str
        データソース
        
    Returns
    -------
    list
        利用可能な日付のリスト（新しい順）
    """
    # 実際の実装ではAPIから取得するか、ファイルシステムをスキャンします
    # ここではダミーデータを返します
    today = datetime.now()
    dates = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]
    return dates

def _render_weather_widget():
    """
    サイドバーに天気ウィジェットを表示します。
    """
    try:
        # APIから天気データを取得
        api_client = APIClient()
        weather_data = api_client.get_weather()
        
        temperature = weather_data.get("temperature", "N/A")
        weather_icon = weather_data.get("icon", "❓")
        
        st.sidebar.markdown(f"### 現在の天気 {weather_icon}")
        st.sidebar.markdown(f"気温: {temperature}°C")
    except Exception as e:
        st.sidebar.error(f"天気データの取得に失敗しました: {str(e)}") 