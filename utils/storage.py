"""
存储模块 - 管理本地JSON数据存储
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from config import DATA_FILE


class Storage:
    """数据存储类"""

    def __init__(self, data_file: Path = DATA_FILE):
        self.data_file = data_file
        self._ensure_data_file()

    def _ensure_data_file(self):
        """确保数据文件存在"""
        if not self.data_file.exists():
            self.data_file.parent.mkdir(parents=True, exist_ok=True)
            self._save_data({})

    def _load_data(self) -> Dict:
        """加载数据文件"""
        try:
            with open(self.data_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def _save_data(self, data: Dict):
        """保存数据文件"""
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_yesterday_snapshot(self, site_key: str) -> List[Dict]:
        """获取指定站点的昨日快照"""
        data = self._load_data()
        return data.get(site_key, [])

    def get_all_snapshots(self) -> Dict:
        """获取所有站点的快照"""
        return self._load_data()

    def update_snapshot(self, site_key: str, articles: List[Dict]) -> None:
        """更新指定站点的快照"""
        data = self._load_data()
        data[site_key] = articles
        self._save_data(data)

    def get_all_urls(self, site_key: str) -> set:
        """获取指定站点的所有URL集合（用于比对）"""
        snapshot = self.get_yesterday_snapshot(site_key)
        return {article.get("url", "") for article in snapshot if article.get("url")}

    def has_new_articles(self, site_key: str, current_articles: List[Dict]) -> bool:
        """检查是否有新增文章"""
        yesterday_urls = self.get_all_urls(site_key)

        for article in current_articles:
            url = article.get("url", "")
            if url and url not in yesterday_urls:
                return True
        return False

    def get_new_articles(self, site_key: str, current_articles: List[Dict]) -> List[Dict]:
        """获取新增文章列表"""
        yesterday_urls = self.get_all_urls(site_key)
        new_articles = []

        for article in current_articles:
            url = article.get("url", "")
            if url and url not in yesterday_urls:
                new_articles.append(article)

        return new_articles


# 全局存储实例
storage = Storage()
