"""
配置模块 - 加载和管理系统配置
"""
import os
import yaml
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent
CONFIG_FILE = PROJECT_ROOT / "config.yaml"
DATA_FILE = PROJECT_ROOT / "data" / "data.json"
LOG_FILE = PROJECT_ROOT / "logs" / "monitor.log"

# 监控目标列表（11个竞争对手）
TARGETS = [
    {
        "name": "3ERP",
        "key": "3erp",
        "url": "https://www.3erp.com/blog/",
        "use_google": False
    },
    {
        "name": "RapidDirect",
        "key": "rapiddirect",
        "url": "https://www.rapiddirect.com/blog/",
        "use_google": False
    },
    {
        "name": "Fictiv",
        "key": "fictiv",
        "url": "https://fictiv.com/articles",
        "use_google": False
    },
    {
        "name": "Protolabs",
        "key": "protolabs",
        "url": "https://www.protolabs.com/resources/blog/",
        "use_google": False
    },
    {
        "name": "Wayken",
        "key": "wayken",
        "url": "https://waykenrm.com/blogs/",
        "use_google": False
    },
    {
        "name": "JLCCNC",
        "key": "jlccnc",
        "url": "https://jlccnc.com/blog/category/knowledge-hub",
        "use_google": False
    },
    {
        "name": "Partmfg",
        "key": "partmfg",
        "url": "https://www.partmfg.com/blog/",
        "use_google": False
    },
    {
        "name": "China-Machining",
        "key": "china-machining",
        "url": "https://www.china-machining.com/blog/",
        "use_google": False
    },
    {
        "name": "HLC-Metalparts",
        "key": "hlc-metalparts",
        "url": "https://www.hlc-metalparts.com/newslist-757014-1",
        "use_google": False
    },
    {
        "name": "Zintilon",
        "key": "zintilon",
        "url": "https://www.zintilon.com/blog/",
        "use_google": False
    },
    {
        "name": "CNC Lathing",
        "key": "cnclathing",
        "url": "https://www.cnclathing.com/guide",
        "use_google": False
    }
]


class Config:
    """配置类"""

    def __init__(self):
        self._config = self._load_config()

    def _load_config(self):
        """加载配置文件"""
        if not CONFIG_FILE.exists():
            raise FileNotFoundError(f"配置文件不存在: {CONFIG_FILE}")

        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    @property
    def telegram_token(self):
        """Telegram Bot Token"""
        return self._config.get("telegram", {}).get("bot_token", "")

    @property
    def telegram_chat_id(self):
        """Telegram Chat ID"""
        return self._config.get("telegram", {}).get("chat_id", "")

    @property
    def email_config(self):
        """Email配置"""
        return self._config.get("email", {})

    @property
    def keywords(self):
        """监控关键词"""
        return [k.upper() for k in self._config.get("keywords", ["CNC", "MACHINING"])]

    @property
    def retry_count(self):
        """重试次数"""
        return self._config.get("task", {}).get("retry_count", 3)

    @property
    def retry_delay(self):
        """重试延迟（秒）"""
        return self._config.get("task", {}).get("retry_delay", 600)

    @property
    def request_timeout(self):
        """请求超时（秒）"""
        return self._config.get("task", {}).get("request_timeout", 30)

    @property
    def min_delay(self):
        """最小请求间隔（秒）"""
        return self._config.get("task", {}).get("min_delay", 2)

    @property
    def max_delay(self):
        """最大请求间隔（秒）"""
        return self._config.get("task", {}).get("max_delay", 5)

    def is_telegram_configured(self):
        """检查Telegram是否已配置"""
        return bool(self.telegram_token and self.telegram_chat_id)

    def is_email_configured(self):
        """检查Email是否已配置"""
        email_cfg = self.email_config
        return bool(
            email_cfg.get("smtp_host") and
            email_cfg.get("username") and
            email_cfg.get("password") and
            email_cfg.get("to_emails")
        )


# 全局配置实例
config = Config()
