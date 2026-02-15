"""
解析器模块 - 解析各站点HTML获取Top 3文章
"""
import random
import time
import logging
from typing import List, Dict, Optional

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

from config import config

logger = logging.getLogger(__name__)


class SeleniumHelper:
    """Selenium辅助类 - 用于处理JavaScript动态加载的页面"""

    _driver = None

    @classmethod
    def get_driver(cls):
        """获取或创建WebDriver"""
        if cls._driver is None:
            try:
                from selenium import webdriver
                from selenium.webdriver.chrome.service import Service
                from selenium.webdriver.chrome.options import Options

                chrome_options = Options()
                chrome_options.add_argument("--headless")
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")
                chrome_options.add_argument("--disable-gpu")
                chrome_options.add_argument("--window-size=1920,1080")
                chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

                # 优先使用系统自带的 chromedriver（GitHub Actions 环境）
                try:
                    service = Service("/usr/bin/chromedriver")
                    cls._driver = webdriver.Chrome(service=service, options=chrome_options)
                except Exception:
                    # 回退到 webdriver_manager（本地 Windows 环境）
                    from webdriver_manager.chrome import ChromeDriverManager
                    service = Service(ChromeDriverManager().install())
                    cls._driver = webdriver.Chrome(service=service, options=chrome_options)

                logger.info("Selenium WebDriver 初始化成功")
            except Exception as e:
                logger.error(f"Selenium 初始化失败: {e}")
                return None
        return cls._driver

    @classmethod
    def fetch_page(cls, url: str, wait_time: int = 5) -> Optional[str]:
        """使用Selenium获取页面HTML"""
        driver = cls.get_driver()
        if not driver:
            return None

        try:
            driver.get(url)
            time.sleep(wait_time)  # 等待JavaScript加载
            return driver.page_source
        except Exception as e:
            logger.error(f"Selenium获取页面失败 [{url}]: {e}")
            return None

    @classmethod
    def close(cls):
        """关闭WebDriver"""
        if cls._driver:
            cls._driver.quit()
            cls._driver = None


class Parser:
    """页面解析器类"""

    def __init__(self):
        self.ua = UserAgent()
        self.session = requests.Session()

    def _get_headers(self) -> Dict:
        """获取随机请求头"""
        return {
            "User-Agent": self.ua.random,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
        }

    def _fetch_page(self, url: str, use_google: bool = False) -> Optional[str]:
        """获取页面内容"""
        try:
            response = self.session.get(
                url,
                headers=self._get_headers(),
                timeout=config.request_timeout,
                allow_redirects=True
            )
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.error(f"获取页面失败 [{url}]: {e}")
            return None

    def _parse_common(self, soup: BeautifulSoup, selectors: Dict) -> List[Dict]:
        """通用解析方法"""
        articles = []

        title_selector = selectors.get("title", "a")
        url_selector = selectors.get("url", "a")
        container_selector = selectors.get("container")

        if container_selector:
            containers = soup.select(container_selector)
            for container in containers[:3]:
                title_elem = container.select_one(title_selector)
                url_elem = container.select_one(url_selector)

                if title_elem and url_elem:
                    title = title_elem.get_text(strip=True)
                    url = url_elem.get("href", "")

                    if title and url:
                        articles.append({
                            "title": title,
                            "url": url,
                            "date": ""
                        })
        else:
            links = soup.select(url_selector)[:3]
            for link in links:
                title = link.get_text(strip=True)
                url = link.get("href", "")

                if title and url:
                    articles.append({
                        "title": title,
                        "url": url,
                        "date": ""
                    })

        return articles

    def parse_3erp(self, html: str) -> List[Dict]:
        """解析 3ERP 博客"""
        soup = BeautifulSoup(html, "lxml")
        articles = []

        # 3ERP 使用 article.bde-loop-item 结构
        article_elements = soup.select("article.bde-loop-item")

        for article in article_elements[:3]:
            # 查找标题 - 多个选择器尝试
            title_elem = (
                article.select_one("h2.bde-heading") or
                article.select_one("div.bde-text-20841-103") or
                article.select_one("div[class*='bde-text-']")
            )
            # 查找链接
            link_elem = article.select_one("a.bde-container-link")

            if title_elem and link_elem:
                title = title_elem.get_text(strip=True)
                url = link_elem.get("href", "")

                if title and url and len(title) > 5:
                    articles.append({
                        "title": title,
                        "url": url,
                        "date": ""
                    })

        return articles

    def parse_rapiddirect(self, html: str) -> List[Dict]:
        """解析 RapidDirect 博客"""
        soup = BeautifulSoup(html, "lxml")
        articles = []

        # 使用 h2 + next sibling link 方式
        headings = soup.find_all('h2')
        for h in headings[:3]:
            title = h.get_text(strip=True)
            next_a = h.find_next('a')
            if next_a and title and len(title) > 5:
                url = next_a.get('href', '')
                if url and '/blog/' in url and 'category' not in url:
                    articles.append({
                        "title": title,
                        "url": url,
                        "date": ""
                    })

        return articles

    def parse_fictiv(self, html: str) -> List[Dict]:
        """解析 Fictiv 网站"""
        soup = BeautifulSoup(html, "lxml")
        articles = []

        # 找到所有 /articles/ 链接，从父元素获取标题
        links = soup.find_all('a', href=lambda x: x and '/articles/' in x and 'category' not in x)
        seen = set()

        for link in links:
            href = link.get('href', '')
            if href and href not in seen:
                seen.add(href)

                # 从父元素获取标题
                parent = link.find_parent(['div', 'section', 'article'])
                if parent:
                    title_elem = parent.select_one('h2, h3, h4')
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                        if title and len(title) > 10:
                            # 补全URL
                            url = href if href.startswith('http') else 'https://fictiv.com' + href
                            articles.append({
                                "title": title[:100],
                                "url": url,
                                "date": ""
                            })
                            if len(articles) >= 3:
                                break

        return articles

    def parse_protolabs(self, html: str) -> List[Dict]:
        """解析 Protolabs 博客"""
        soup = BeautifulSoup(html, "lxml")
        articles = []

        # 使用 h2/h3 + parent link 方式
        headings = soup.find_all(['h2', 'h3'])
        for h in headings[:3]:
            title = h.get_text(strip=True)
            parent_a = h.find_parent('a')
            if parent_a and title and len(title) > 5:
                url = parent_a.get('href', '')
                if url:
                    # 补全URL
                    if not url.startswith('http'):
                        url = 'https://www.protolabs.com' + url
                    articles.append({
                        "title": title,
                        "url": url,
                        "date": ""
                    })

        return articles

    def parse_wayken(self, html: str) -> List[Dict]:
        """解析 Wayken 博客"""
        soup = BeautifulSoup(html, "lxml")

        selectors = {
            "container": "div.blog-item, article, div.post",
            "title": "h2 a, h3 a, a.article-title",
            "url": "h2 a, h3 a, a.article-title"
        }
        return self._parse_common(soup, selectors)

    def parse_jlccnc(self, html: str) -> List[Dict]:
        """解析 JLCCNC 博客"""
        soup = BeautifulSoup(html, "lxml")
        articles = []

        # 找到所有博客链接
        links = soup.find_all('a', href=True)
        seen = set()

        for link in links:
            href = link.get('href', '')
            # 过滤出博客文章链接
            if href and '/blog/' in href and 'category' not in href:
                if href not in seen:
                    seen.add(href)
                    text = link.get_text(strip=True)
                    # 过滤太短的标题
                    if text and len(text) > 15:
                        # 补全URL
                        url = href if href.startswith('http') else 'https://jlccnc.com' + href
                        articles.append({
                            "title": text[:100],
                            "url": url,
                            "date": ""
                        })
                        if len(articles) >= 3:
                            break

        return articles

    def parse_partmfg(self, html: str) -> List[Dict]:
        """解析 Partmfg 博客"""
        soup = BeautifulSoup(html, "lxml")

        selectors = {
            "container": "div.blog-post, article, div.post",
            "title": "h2 a, h3 a, a.post-title",
            "url": "h2 a, h3 a, a.post-title"
        }
        return self._parse_common(soup, selectors)

    def parse_china_machining(self, html: str) -> List[Dict]:
        """解析 China-Machining 博客"""
        soup = BeautifulSoup(html, "lxml")

        selectors = {
            "container": "div.blog-item, article, div.news-item",
            "title": "h2 a, h3 a, a.title",
            "url": "h2 a, h3 a, a.title"
        }
        return self._parse_common(soup, selectors)

    def parse_hlc_metalparts(self, html: str) -> List[Dict]:
        """解析 HLC-Metalparts 新闻列表"""
        soup = BeautifulSoup(html, "lxml")
        articles = []

        # 查找所有 /news/ 链接
        links = soup.find_all('a', href=lambda x: x and '/news/' in x)
        seen = set()

        for link in links:
            href = link.get('href', '')
            if href and href not in seen:
                seen.add(href)

                # 首先尝试直接获取链接文本
                text = link.get_text(strip=True)

                # 如果链接文本为空，尝试从祖父元素获取
                if not text or len(text) < 5:
                    parent = link.parent
                    if parent:
                        grandparent = parent.parent
                        if grandparent:
                            text = grandparent.get_text(strip=True)

                # 去除日期部分（格式如 Feb 10, 2026）
                if text:
                    import re
                    # 匹配各种月份格式
                    text = re.sub(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d+,\s+\d{4}', '', text)
                    text = text.strip()

                # 过滤太短的标题
                if text and len(text) > 15:
                    # 补全URL
                    url = href if href.startswith('http') else 'https://www.hlc-metalparts.com' + href
                    articles.append({
                        "title": text[:100],
                        "url": url,
                        "date": ""
                    })
                    if len(articles) >= 3:
                        break

        return articles

    def parse_zintilon(self, html: str) -> List[Dict]:
        """解析 Zintilon 博客"""
        soup = BeautifulSoup(html, "lxml")
        articles = []

        # 使用 h2/h3 + parent link 方式
        headings = soup.find_all(['h2', 'h3'])
        for h in headings[:3]:
            title = h.get_text(strip=True)
            parent_a = h.find_parent('a')
            if parent_a and title and len(title) > 5:
                url = parent_a.get('href', '')
                if url:
                    # 补全URL
                    if not url.startswith('http'):
                        url = 'https://www.zintilon.com' + url
                    articles.append({
                        "title": title,
                        "url": url,
                        "date": ""
                    })

        return articles

    def parse_cnclathing(self, html: str) -> List[Dict]:
        """解析 CNC Lathing 网站"""
        soup = BeautifulSoup(html, "lxml")
        articles = []

        # 查找所有链接
        links = soup.find_all('a', href=True)
        seen = set()

        # 需要过滤的关键词
        exclude_keywords = ['quote', 'about', 'products', 'contact', 'home', 'email', 'cdn-cgi', 'tel:', 'blog', 'news']

        for link in links:
            href = link.get('href', '')
            text = link.get_text(strip=True)

            # 过滤
            if (href and href not in seen and
                text and len(text) > 15 and
                not any(kw in href.lower() for kw in exclude_keywords) and
                not any(kw in text.lower() for kw in ['email', 'quote', 'phone', 'contact'])):

                # 只保留有意义的文章/指南链接
                if '/' in href and not href.startswith('//'):
                    seen.add(href)
                    url = href if href.startswith('http') else 'https://www.cnclathing.com' + href
                    articles.append({
                        "title": text[:100],
                        "url": url,
                        "date": ""
                    })
                    if len(articles) >= 3:
                        break

        return articles

    def parse(self, site_key: str, html: str) -> List[Dict]:
        """根据站点key调用对应的解析方法"""
        parser_methods = {
            "3erp": self.parse_3erp,
            "rapiddirect": self.parse_rapiddirect,
            "fictiv": self.parse_fictiv,
            "protolabs": self.parse_protolabs,
            "wayken": self.parse_wayken,
            "jlccnc": self.parse_jlccnc,
            "partmfg": self.parse_partmfg,
            "china-machining": self.parse_china_machining,
            "hlc-metalparts": self.parse_hlc_metalparts,
            "zintilon": self.parse_zintilon,
            "cnclathing": self.parse_cnclathing,
        }

        parser = parser_methods.get(site_key)
        if parser:
            return parser(html)

        logger.warning(f"未找到站点 {site_key} 的解析方法")
        return []


class SiteMonitor:
    """站点监控类"""

    # 需要使用 Selenium 的站点
    SELENIUM_SITES = ["jlccnc"]

    def __init__(self):
        self.parser = Parser()

    def fetch_articles(self, site_key: str, url: str, use_google: bool = False) -> List[Dict]:
        """获取站点文章列表"""
        html = self._fetch_page(url, use_google, site_key)
        if not html:
            return []

        articles = self.parser.parse(site_key, html)
        return articles[:3]  # 只返回Top 3

    def _fetch_page(self, url: str, use_google: bool = False, site_key: str = None) -> Optional[str]:
        """获取页面内容（带延时）"""
        time.sleep(random.uniform(config.min_delay, config.max_delay))

        # 对于需要 Selenium 的站点
        if site_key and site_key in self.SELENIUM_SITES:
            logger.info(f"使用 Selenium 获取站点 {site_key}")
            return SeleniumHelper.fetch_page(url)

        return self.parser._fetch_page(url, use_google)


# 全局解析器实例
parser = Parser()
site_monitor = SiteMonitor()
