"""
Nookのフロントエンドアプリケーション。
Streamlitを使用してダッシュボード形式のUIを提供します。
"""

import streamlit as st
from nook.frontend.components.sidebar import render_sidebar
from nook.frontend.components.content_viewer import render_content
# チャットコンポーネントのインポートを削除
# from nook.frontend.components.chat import render_chat

def main():
    """
    メインアプリケーション関数。
    サイドバー、ダッシュボード形式のコンテンツビューアを表示します。
    """
    st.set_page_config(
        page_title="Nook - パーソナル情報ハブ",
        page_icon="📚",
        layout="wide",
    )

    # カスタムテーマの適用
    _apply_theme()

    # サイドバーの表示
    selected_source, selected_date = render_sidebar()
    
    # ダッシュボード形式のメインコンテンツの表示
    render_content(selected_source, selected_date)

def _apply_theme():
    """
    アプリケーション全体のテーマを適用します。
    """
    st.markdown("""
    <style>
    .stApp {
        background-color: #f5f7fa;
    }
    
    h1, h2, h3 {
        color: #1E88E5;
    }
    
    .stSidebar {
        background-color: #263238;
    }
    
    .stSidebar [data-testid="stSidebarNav"] {
        background-color: #263238;
    }
    
    .stSidebar [data-testid="stSidebarNav"] span {
        color: white;
    }
    
    .stSidebar [data-testid="stMarkdownContainer"] h1 {
        color: white;
    }
    
    .stSidebar [data-testid="stMarkdownContainer"] h3 {
        color: white;
    }
    
    .stSidebar [data-testid="stMarkdownContainer"] p {
        color: #b0bec5;
    }
    
    .stSidebar [data-testid="stMarkdownContainer"] caption {
        color: #b0bec5;
    }
    </style>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main() 