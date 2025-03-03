"""
Nookのダッシュボードページ。
"""

import streamlit as st
from nook.frontend.components.content_viewer import render_content, render_date_selector, get_available_dates
from datetime import datetime
import pandas as pd
import re

def show():
    """ダッシュボードページを表示します。"""
    # Streamlitの設定を変更してナビゲーションバーを非表示にする
    st.set_page_config(
        page_title="Nook",
        page_icon="📚",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # カスタムCSSを適用してapp/dashboardナビゲーションを非表示にする
    hide_nav_style = """
        <style>
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        div[data-testid="stSidebarNav"] {display: none !important;}
        </style>
    """
    st.markdown(hide_nav_style, unsafe_allow_html=True)
    
    # サイドバーにタイトルを表示
    st.sidebar.title("Nook")
    st.sidebar.markdown("パーソナル情報ハブ")
    
    # サイドバーにセクションを追加
    st.sidebar.markdown("### 情報ソース")
    
    # ソース選択
    sources = ["all", "hackernews", "github", "reddit", "techfeed", "paper"]
    source_display_names = {
        "all": "すべて",
        "hackernews": "Hacker News",
        "github": "GitHub",
        "reddit": "Reddit",
        "techfeed": "Tech Feed",
        "paper": "論文"
    }
    
    selected_source = st.sidebar.selectbox(
        "",
        options=sources,
        format_func=lambda x: source_display_names.get(x, x)
    )
    
    # 日付選択
    st.sidebar.markdown("### 日付")
    selected_date = render_date_selector()
    
    # 天気情報の表示を削除
    
    # メインコンテンツを表示
    render_content(selected_source, selected_date)

