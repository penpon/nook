"""ローカルファイルシステムでのデータ操作ユーティリティ。"""

import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional


class LocalStorage:
    """
    ローカルファイルシステムでのデータ操作を担当するクラス。
    
    Parameters
    ----------
    base_dir : str
        ベースディレクトリのパス。
    """
    
    def __init__(self, base_dir: str):
        """
        LocalStorageを初期化します。
        
        Parameters
        ----------
        base_dir : str
            ベースディレクトリのパス。
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def save_markdown(self, content: str, service_name: str, date: Optional[datetime] = None) -> Path:
        """
        Markdownコンテンツを保存します。
        
        Parameters
        ----------
        content : str
            保存するMarkdownコンテンツ。
        service_name : str
            サービス名（ディレクトリ名）。
        date : datetime, optional
            日付。指定しない場合は現在の日付。
            
        Returns
        -------
        Path
            保存されたファイルのパス。
        """
        if date is None:
            date = datetime.now()
        
        date_str = date.strftime("%Y-%m-%d")
        service_dir = self.base_dir / service_name
        service_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = service_dir / f"{date_str}.md"
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        return file_path
    
    def load_markdown(self, service_name: str, date: Optional[datetime] = None) -> Optional[str]:
        """
        Markdownコンテンツを読み込みます。
        
        Parameters
        ----------
        service_name : str
            サービス名（ディレクトリ名）。
        date : datetime, optional
            日付。指定しない場合は現在の日付。
            
        Returns
        -------
        str or None
            読み込まれたMarkdownコンテンツ。ファイルが存在しない場合はNone。
        """
        if date is None:
            date = datetime.now()
        
        date_str = date.strftime("%Y-%m-%d")
        file_path = self.base_dir / service_name / f"{date_str}.md"
        
        if not file_path.exists():
            return None
        
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    
    def list_dates(self, service_name: str) -> List[datetime]:
        """
        利用可能な日付の一覧を取得します。
        
        Parameters
        ----------
        service_name : str
            サービス名（ディレクトリ名）。
            
        Returns
        -------
        List[datetime]
            利用可能な日付のリスト。
        """
        service_dir = self.base_dir / service_name
        
        if not service_dir.exists():
            return []
        
        dates = []
        for file_path in service_dir.glob("*.md"):
            try:
                date_str = file_path.stem
                date = datetime.strptime(date_str, "%Y-%m-%d")
                dates.append(date)
            except ValueError:
                continue
        
        return sorted(dates, reverse=True) 