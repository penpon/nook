"""
チャットコンポーネント。
選択されたコンテンツに関するチャットインターフェースを提供します。
"""

import streamlit as st
import uuid
from typing import Dict, List, Any

from nook.frontend.utils.api_client import APIClient

def render_chat(content: Dict[str, Any]):
    """
    チャットインターフェースを表示します。
    
    Parameters
    ----------
    content : Dict[str, Any]
        選択されたコンテンツ
    """
    st.header("チャット")
    
    # セッション状態の初期化
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    if "topic_id" not in st.session_state:
        st.session_state.topic_id = str(uuid.uuid4())
    
    # チャット履歴の表示
    _display_chat_history()
    
    # 入力フォーム
    with st.form(key="chat_form", clear_on_submit=True):
        user_input = st.text_area("メッセージ", height=100)
        submit_button = st.form_submit_button("送信")
        
        if submit_button and user_input:
            _send_message(user_input, content)

def _display_chat_history():
    """
    チャット履歴を表示します。
    """
    for message in st.session_state.chat_history:
        role = message.get("role", "")
        content = message.get("content", "")
        
        if role == "user":
            st.markdown(f"**あなた**: {content}")
        elif role == "assistant":
            st.markdown(f"**アシスタント**: {content}")

def _send_message(message: str, content: Dict[str, Any]):
    """
    メッセージを送信し、レスポンスを表示します。
    
    Parameters
    ----------
    message : str
        ユーザーメッセージ
    content : Dict[str, Any]
        選択されたコンテンツ
    """
    # ユーザーメッセージをチャット履歴に追加
    user_message = {"role": "user", "content": message}
    st.session_state.chat_history.append(user_message)
    
    try:
        # APIクライアントの初期化
        api_client = APIClient()
        
        # マークダウンコンテンツの準備
        markdown_content = content.get("content", "")
        
        # APIリクエスト
        response = api_client.send_chat_message(
            topic_id=st.session_state.topic_id,
            message=message,
            chat_history=st.session_state.chat_history,
            markdown=markdown_content
        )
        
        # アシスタントのレスポンスをチャット履歴に追加
        assistant_message = {"role": "assistant", "content": response.get("response", "")}
        st.session_state.chat_history.append(assistant_message)
        
        # 画面を更新
        st.experimental_rerun()
        
    except Exception as e:
        st.error(f"メッセージの送信に失敗しました: {str(e)}") 