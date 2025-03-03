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
    st.sidebar.markdown("<h1 style='color: white;'>Nook</h1>", unsafe_allow_html=True)
    st.sidebar.markdown("<p style='color: #b0bec5;'>パーソナル情報ハブ</p>", unsafe_allow_html=True)
    
    # ソース選択
    sources = {
        "all": "すべて",
        "reddit": "Reddit",
        "hackernews": "Hacker News",
        "github": "GitHub Trending",
        "techfeed": "Tech Feed",
        "paper": "論文"
    }
    
    # ソースアイコンの追加
    source_icons = {
        "all": "🌐",
        "reddit": "🔴",
        "hackernews": "🔶",
        "github": "🐙",
        "techfeed": "📱",
        "paper": "📄"
    }
    
    # ソース選択のカスタムスタイル
    st.sidebar.markdown("""
    <style>
    div[data-testid="stSelectbox"] {
        background-color: #37474f;
        border-radius: 10px;
        padding: 5px;
        margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    selected_source = st.sidebar.selectbox(
        "情報ソース",
        options=list(sources.keys()),
        format_func=lambda x: f"{source_icons.get(x, '')} {sources.get(x, x)}"
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

        weather_icon = get_weather_icon(weather_icon)
        
        # 天気ウィジェットのカスタムスタイル
        st.sidebar.markdown("""
        <style>
        .weather-widget {
            background-color: #37474f;
            border-radius: 10px;
            padding: 15px;
            margin-top: 10px;
            margin-bottom: 20px;
            text-align: center;
        }
        
        .weather-icon {
            font-size: 36px;
            margin-bottom: 10px;
        }
        
        .weather-temp {
            font-size: 24px;
            font-weight: bold;
            color: white;
        }
        
        .weather-label {
            font-size: 14px;
            color: #b0bec5;
        }
        </style>
        """, unsafe_allow_html=True)
        
        st.sidebar.markdown(f"""
        <div class="weather-widget">
            <div class="weather-icon">{weather_icon}</div>
            <div class="weather-temp">{temperature}°C</div>
            <div class="weather-label">現在の天気</div>
        </div>
        """, unsafe_allow_html=True)
    except Exception as e:
        st.sidebar.error(f"天気データの取得に失敗しました: {str(e)}") 

def get_weather_icon(weather_code: str) -> str:
    """
    天気コードに基づいて適切な絵文字アイコンを返します。
    
    Parameters
    ----------
    weather_code : str
        OpenWeatherMapの天気コード
        
    Returns
    -------
    str
        天気を表す絵文字アイコン
    """
    # 天気コードと絵文字のマッピング
    weather_icons = {
        # 晴れ
        "01d": "☀️",
        "01n": "🌙",
        # 薄い雲
        "02d": "⛅",
        "02n": "☁️",
        # 曇り
        "03d": "☁️",
        "03n": "☁️",
        "04d": "☁️",
        "04n": "☁️",
        # 雨
        "09d": "🌧️",
        "09n": "🌧️",
        "10d": "🌦️",
        "10n": "🌧️",
        # 雷雨
        "11d": "⛈️",
        "11n": "⛈️",
        # 雪
        "13d": "❄️",
        "13n": "❄️",
        # 霧
        "50d": "🌫️",
        "50n": "🌫️"
    }
    
    return weather_icons.get(weather_code, "🌈")  # デフォルトは虹のアイコン 