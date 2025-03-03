"""
コンテンツビューアコンポーネント。
選択されたソースと日付に基づいてダッシュボード形式でコンテンツを表示します。
"""

import streamlit as st
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import os
from pathlib import Path

from nook.frontend.utils.api_client import APIClient

def get_available_dates() -> List[str]:
    """
    データが存在する日付のリストを取得します。
    
    Returns
    -------
    List[str]
        データが存在する日付のリスト（降順でソート済み）
    """
    # データフォルダのパス
    data_dir = Path("data")
    
    # すべてのデータソースのフォルダを確認
    available_dates = set()
    
    # データディレクトリが存在するか確認
    if not data_dir.exists():
        return []
    
    for source_dir in data_dir.iterdir():
        if source_dir.is_dir():
            # 各ソースフォルダ内のファイルを確認
            for file in source_dir.iterdir():
                if file.suffix == '.md':  # マークダウンファイルのみ
                    date_str = file.stem  # ファイル名から拡張子を除いた部分（日付）
                    if len(date_str) == 10 and date_str.count('-') == 2:  # YYYY-MM-DD 形式かチェック
                        available_dates.add(date_str)
    
    # 日付をソート（降順）
    sorted_dates = sorted(list(available_dates), reverse=True)
    return sorted_dates

def render_date_selector() -> str:
    """
    利用可能な日付のセレクターを表示します。
    
    Returns
    -------
    str
        選択された日付
    """
    # 利用可能な日付のリストを取得
    available_dates = get_available_dates()
    
    if not available_dates:
        st.warning("データが存在する日付が見つかりません。")
        return datetime.now().strftime("%Y-%m-%d")
    
    # デフォルトは最新の日付
    default_date = available_dates[0] if available_dates else datetime.now().strftime("%Y-%m-%d")
    
    # 日付選択
    selected_date = st.selectbox(
        "日付",
        options=available_dates,
        index=0
    )
    
    return selected_date

def render_content(source: str, date: str) -> Optional[Dict[str, Any]]:
    """
    ダッシュボード形式でコンテンツを表示します。
    
    Parameters
    ----------
    source : str
        データソース
    date : str
        表示する日付
        
    Returns
    -------
    Optional[Dict[str, Any]]
        選択されたコンテンツ
    """
    try:
        api_client = APIClient()
        content_data = api_client.get_content(source, date)
        
        if not content_data or not content_data.get("items"):
            st.info(f"{date}の{source}データはありません。")
            return None
        
        # カスタムCSSを適用
        _apply_custom_css()
        
        # ヘッダー部分
        source_display_name = _get_source_display_name(source)
        st.markdown(f"<h1 class='dashboard-header'>{source_display_name} - {date} <span class='refresh-icon'>↻</span></h1>", unsafe_allow_html=True)
        
        # ダッシュボードの概要セクション
        _render_dashboard_summary(content_data, source)
        
        # コンテンツアイテムをカード形式で表示
        items = content_data.get("items", [])
        
        # 各アイテムのコンテンツを記事ごとに分割
        processed_items = _process_markdown_content(items)
        
        # 分割されたアイテムを表示
        _render_content_cards(processed_items)
        
        return None
    
    except Exception as e:
        st.error(f"コンテンツの取得に失敗しました: {str(e)}")
        return None

def _apply_custom_css():
    """
    ダッシュボード用のカスタムCSSを適用します。
    """
    st.markdown("""
    <style>
    /* 全体のスタイル */
    .stApp {
        background-color: #000000;
        color: #e7e9ea;
    }
    
    /* マークダウンスタイル */
    .stMarkdown {
        color: #e7e9ea;
    }
    
    h1, h2, h3, h4, h5, h6 {
        color: #e7e9ea !important;
    }
    
    a {
        color: #1d9bf0 !important;
        text-decoration: none;
    }
    
    a:hover {
        text-decoration: underline !important;
    }
    
    hr {
        border-color: #2f3336;
        margin: 20px 0;
    }
    
    /* タブのスタイル改善 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
        background-color: #16181c;
        border-bottom: 1px solid #2f3336;
        padding: 0 10px;
        overflow-x: auto;
        flex-wrap: nowrap;
        white-space: nowrap;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 60px;
        white-space: nowrap;
        background-color: transparent !important;
        border-radius: 0;
        font-size: 18px;
        font-weight: 600;
        color: #71767b !important;
        border-bottom: 2px solid transparent;
        padding: 0 20px;
        margin-right: 10px;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: transparent !important;
        color: #e7e9ea !important;
        border-bottom: 2px solid #1d9bf0 !important;
    }
    
    /* スクロールバーのカスタマイズ */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: #16181c;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #2f3336;
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: #1d9bf0;
    }
    </style>
    """, unsafe_allow_html=True)

def _render_dashboard_summary(content_data: Dict[str, Any], source: str):
    """
    ダッシュボードの概要セクションを表示します。
    
    Parameters
    ----------
    content_data : Dict[str, Any]
        コンテンツデータ
    source : str
        データソース
    """
    items = content_data.get("items", [])
    
    # サマリーメトリクスを計算
    total_items = len(items)
    avg_length = sum(len(item.get("content", "")) for item in items) // max(1, total_items)
    
    # 3カラムレイアウトでメトリクスを表示
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{total_items}</div>
            <div class="metric-label">総アイテム数</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{avg_length}</div>
            <div class="metric-label">平均文字数</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{_get_source_display_name(source)}</div>
            <div class="metric-label">データソース</div>
        </div>
        """, unsafe_allow_html=True)

def _process_markdown_content(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Markdownコンテンツを処理します。
    シンプルに元のアイテムをそのまま返します。
    
    Parameters
    ----------
    items : List[Dict[str, Any]]
        コンテンツアイテムのリスト
        
    Returns
    -------
    List[Dict[str, Any]]
        処理されたアイテムのリスト
    """
    return items

def _render_content_cards(items: List[Dict[str, Any]]):
    """
    コンテンツアイテムをタブごとに表示します。
    
    Parameters
    ----------
    items : List[Dict[str, Any]]
        コンテンツアイテムのリスト
    """
    # ソースごとにアイテムをグループ化
    grouped_items = {}
    for item in items:
        source = item.get("source", "その他")
        if source not in grouped_items:
            grouped_items[source] = []
        grouped_items[source].append(item)
    
    # タブを作成（短い名前を使用）
    tab_names = {
        "reddit": "Reddit",
        "hackernews": "HN",
        "github": "GitHub",
        "techfeed": "Tech",
        "paper": "論文",
        "その他": "その他"
    }
    
    # タブを作成
    tabs = st.tabs([tab_names.get(source, source) for source in grouped_items.keys()])
    
    # 各タブにコンテンツを表示
    for i, (source, source_items) in enumerate(grouped_items.items()):
        with tabs[i]:
            # 各アイテムを表示
            for item in source_items:
                title = item.get("title", "タイトルなし")
                url = item.get("url", "")
                content = item.get("content", "")
                
                # タイトルを表示
                st.markdown(f"## {title}")
                
                # URLがあれば表示
                if url:
                    st.markdown(f"[リンク]({url})")
                
                # コンテンツをMarkdownとしてそのまま表示
                st.markdown("---")
                st.markdown(content)
                st.markdown("---")

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