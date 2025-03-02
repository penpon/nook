"""
Nookのフロントエンドアプリケーション。
Streamlitを使用してUIを提供します。
"""

import streamlit as st
from nook.frontend.components.sidebar import render_sidebar
from nook.frontend.components.content_viewer import render_content
# チャットコンポーネントのインポートを削除
# from nook.frontend.components.chat import render_chat

def main():
    """
    メインアプリケーション関数。
    サイドバー、コンテンツビューアを表示します。
    """
    st.set_page_config(
        page_title="Nook - パーソナル情報ハブ",
        page_icon="📚",
        layout="wide",
    )

    # サイドバーの表示
    selected_source, selected_date = render_sidebar()
    
    # メインコンテンツの表示（チャットエリアなし）
    render_content(selected_source, selected_date)

if __name__ == "__main__":
    main() 