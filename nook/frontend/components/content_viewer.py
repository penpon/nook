"""
コンテンツビューアコンポーネント。
選択されたソースと日付に基づいてコンテンツを表示します。
"""

import streamlit as st
from typing import Dict, List, Optional, Any

from nook.frontend.utils.api_client import APIClient

def render_content(source: str, date: str) -> Optional[Dict[str, Any]]:
    """
    コンテンツを表示します。
    
    Parameters
    ----------
    source : str
        データソース
    date : str
        表示する日付
        
    Returns
    -------
    Optional[Dict[str, Any]]
        選択されたコンテンツ（チャット用）
    """
    try:
        api_client = APIClient()
        content_data = api_client.get_content(source, date)
        
        if not content_data or not content_data.get("items"):
            st.info(f"{date}の{source}データはありません。")
            return None
        
        st.header(f"{_get_source_display_name(source)} - {date}")
        
        items = content_data.get("items", [])
        
        for i, item in enumerate(items):
            with st.expander(item.get("title", f"項目 {i+1}"), expanded=i==0):
                _render_content_item(item)
        
        return None
    
    except Exception as e:
        st.error(f"コンテンツの取得に失敗しました: {str(e)}")
        return None

def _get_source_display_name(source: str) -> str:
    """
    ソースの表示名を取得します。
    
    Parameters
    ----------
    source : str
        データソース
        
    Returns
    -------
    str
        表示名
    """
    source_names = {
        "all": "すべてのソース",
        "reddit": "Reddit",
        "hackernews": "Hacker News",
        "github": "GitHub Trending",
        "techfeed": "Tech Feed",
        "paper": "論文"
    }
    return source_names.get(source, source)

def _render_content_item(item: Dict[str, Any]):
    """
    コンテンツ項目を表示します。
    
    Parameters
    ----------
    item : Dict[str, Any]
        コンテンツ項目
    """
    title = item.get("title", "タイトルなし")
    url = item.get("url", "")
    content = item.get("content", "")
    source = item.get("source", "")
    
    if url:
        st.markdown(f"### [{title}]({url})")
    else:
        st.markdown(f"### {title}")
    
    st.markdown(f"**ソース**: {source}")
    
    if content:
        with st.container():
            st.markdown(content) 