"""
通知模块 - Telegram和Email通知
"""
import asyncio
import logging
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Dict, Optional

from telegram import Bot
from telegram.error import TelegramError

from config import config

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Telegram通知类"""

    def __init__(self, token: str = None, chat_id: str = None):
        self.token = token or config.telegram_token
        self.chat_id = chat_id or config.telegram_chat_id
        self.bot = Bot(token=self.token) if self.token else None

    def is_configured(self) -> bool:
        """检查是否已配置"""
        return bool(self.token and self.chat_id and self.bot)

    def send_message(self, text: str) -> bool:
        """发送消息"""
        if not self.is_configured():
            logger.warning("Telegram未配置，跳过发送")
            return False

        try:
            # python-telegram-bot 20.x 使用异步API
            import concurrent.futures
            def _send():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(
                        self.bot.send_message(
                            chat_id=self.chat_id,
                            text=text,
                            parse_mode="HTML"
                        )
                    )
                finally:
                    loop.close()

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(_send)
                future.result()

            logger.info(f"Telegram消息发送成功")
            return True
        except TelegramError as e:
            logger.error(f"Telegram发送失败: {e}")
            return False
        except Exception as e:
            logger.error(f"Telegram发送失败: {e}")
            return False

    def send_article_alert(self, site_name: str, article: Dict) -> bool:
        """发送文章提醒"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        message = (
            f"📢 <b>【竞品动态提醒】</b>\n\n"
            f"<b>厂商</b>：{site_name}\n"
            f"<b>标题</b>：{article.get('title', '')}\n"
            f"<b>链接</b>：{article.get('url', '')}\n"
            f"<b>检测时间</b>：{timestamp}"
        )

        return self.send_message(message)

    def send_error_alert(self, site_name: str, error_msg: str) -> bool:
        """发送错误报警"""
        message = (
            f"⚠️ <b>【爬虫失效提醒】</b>\n\n"
            f"<b>站点</b>：{site_name}\n"
            f"<b>错误</b>：{error_msg}\n"
            f"<b>时间</b>：{datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )

        return self.send_message(message)


class EmailNotifier:
    """Email通知类"""

    def __init__(self):
        self.config = config.email_config

    def is_configured(self) -> bool:
        """检查是否已配置"""
        return bool(
            self.config.get("smtp_host") and
            self.config.get("username") and
            self.config.get("password") and
            self.config.get("to_emails")
        )

    def _create_html_content(self, articles: List[Dict], site_name: str) -> str:
        """创建HTML内容"""
        rows = ""
        for article in articles:
            rows += f"""
            <tr>
                <td>{site_name}</td>
                <td>{article.get('title', '')}</td>
                <td><a href="{article.get('url', '')}">{article.get('url', '')}</a></td>
                <td>{article.get('date', '')}</td>
            </tr>
            """

        html = f"""
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #4CAF50; color: white; }}
                tr:nth-child(even) {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <h2>📢 竞品监控新文章提醒</h2>
            <p>检测到以下新增文章（包含关键词：CNC/Machining）：</p>
            <table>
                <tr>
                    <th>厂商</th>
                    <th>标题</th>
                    <th>链接</th>
                    <th>日期</th>
                </tr>
                {rows}
            </table>
            <p style="color: #666; font-size: 12px;">
                此邮件由CNC竞品监控系统自动发送<br>
                检测时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            </p>
        </body>
        </html>
        """
        return html

    def send_email(self, subject: str, html_content: str) -> bool:
        """发送邮件"""
        if not self.is_configured():
            logger.warning("Email未配置，跳过发送")
            return False

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.config.get("from_email", self.config.get("username"))
            msg["To"] = ", ".join(self.config["to_emails"])

            part = MIMEText(html_content, "html", "utf-8")
            msg.attach(part)

            smtp_host = self.config["smtp_host"]
            smtp_port = self.config.get("smtp_port", 587)
            username = self.config["username"]
            password = self.config["password"]
            use_tls = self.config.get("use_tls", False)
            use_ssl = self.config.get("use_ssl", False)

            if use_ssl:
                # 使用 SSL 连接 (端口 465)
                with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
                    server.login(username, password)
                    server.send_message(msg)
            else:
                # 使用普通 SMTP 连接
                with smtplib.SMTP(smtp_host, smtp_port) as server:
                    if use_tls:
                        server.starttls()
                    server.login(username, password)
                    server.send_message(msg)

            logger.info(f"Email发送成功: {subject}")
            return True

        except Exception as e:
            logger.error(f"Email发送失败: {e}")
            return False

    def send_article_alert(self, articles: List[Dict], site_name: str) -> bool:
        """发送文章提醒"""
        date_str = datetime.now().strftime("%Y-%m-%d")
        subject = f"【竞品监控】发现新文章提醒 - {date_str}"

        html_content = self._create_html_content(articles, site_name)
        return self.send_email(subject, html_content)


class Notifier:
    """统一通知类"""

    def __init__(self):
        self.telegram = TelegramNotifier()
        self.email = EmailNotifier()

    def notify_new_articles(self, site_name: str, articles: List[Dict]) -> None:
        """通知新文章"""
        for article in articles:
            self.telegram.send_article_alert(site_name, article)

        if self.email.is_configured() and articles:
            self.email.send_article_alert(articles, site_name)

    def notify_error(self, site_name: str, error_msg: str) -> None:
        """通知错误"""
        self.telegram.send_error_alert(site_name, error_msg)

    def send_summary(self, all_articles: List[Dict], all_errors: List[Dict]) -> None:
        """发送汇总通知"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        # Telegram 汇总消息
        if self.telegram.is_configured():
            message = f"📊 <b>【竞品监控日报】</b>\n\n"
            message += f"<b>检测时间</b>：{timestamp}\n\n"

            if all_articles:
                message += f"📢 <b>发现 {len(all_articles)} 篇新文章：</b>\n"
                for article in all_articles:
                    title = article.get('title', '')[:50]
                    url = article.get('url', '')
                    message += f"• {title}\n{url}\n\n"
            else:
                message += "✅ 无新增文章\n\n"

            if all_errors:
                message += f"⚠️ <b>{len(all_errors)} 个站点异常：</b>\n"
                for err in all_errors:
                    message += f"• {err['site']}: {err['error'][:50]}\n"

            self.telegram.send_message(message)

        # Email 汇总（有文章或错误时发送）
        if self.email.is_configured() and (all_articles or all_errors):
            subject = f"【竞品监控】日报 - {timestamp}"
            if all_articles:
                subject = f"【竞品监控】发现 {len(all_articles)} 篇新文章 - {timestamp}"
            html = self._create_summary_html(all_articles, all_errors, timestamp)
            self.email.send_email(subject, html)

    def _create_summary_html(self, all_articles: List[Dict], all_errors: List[Dict], timestamp: str) -> str:
        """创建汇总HTML内容"""
        rows = ""
        for article in all_articles:
            rows += f"""
            <tr>
                <td>{article.get('title', '')}</td>
                <td><a href="{article.get('url', '')}">链接</a></td>
            </tr>
            """

        error_rows = ""
        for err in all_errors:
            error_rows += f"""
            <tr>
                <td>{err['site']}</td>
                <td>{err['error']}</td>
            </tr>
            """

        html = f"""
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #4CAF50; color: white; }}
                tr:nth-child(even) {{ background-color: #f2f2f2; }}
                .error {{ background-color: #ffcccc; }}
            </style>
        </head>
        <body>
            <h2>📊 竞品监控日报</h2>
            <p><b>检测时间</b>：{timestamp}</p>

            <h3>📢 新文章 ({len(all_articles)})</h3>
            {f'<table><tr><th>标题</th><th>链接</th></tr>{rows}</table>' if all_articles else '<p>✅ 无新增文章</p>'}

            {f'<h3>⚠️ 异常站点 ({len(all_errors)})</h3><table><tr><th>站点</th><th>错误</th></tr>{error_rows}</table>' if all_errors else ''}
        </body>
        </html>
        """
        return html


# 全局通知器实例
notifier = Notifier()
telegram_notifier = TelegramNotifier()
email_notifier = EmailNotifier()
