# 竞争对手博客更新自动化监控系统需求文档 (V2.1)

## 1. 项目概述

本系统旨在通过自动化脚本，每日监控 **11 家** 竞争对手官网博客的最新动态。系统采用“**首页 Top 3 快照对比法**”，即仅记录每个博客列表页的前三篇文章，通过比对每日差异来识别新内容，并在命中特定关键词时通过 Telegram 发送实时提醒。

## 2. 监控目标列表

系统需覆盖以下 11 个核心竞争对手（优先级按列表顺序）：

| 序号 | 竞争对手名称 | 目标博客/新闻页面 URL | 备注 |
| :--- | :--- | :--- | :--- |
| 1   | 3ERP | `https://www.3erp.com/blog/`  | |
| 2   | RapidDirect | `https://www.rapiddirect.com/blog/`  | |
| 3   | Fictiv | `https://www.google.com/search?q=site:fictiv.com/articles&tbs=qdr:w`  | 需要使用 Google 搜索结果作为数据源 (防爬虫) |
| 4   | Protolabs | `https://www.protolabs.com/resources/blog/`  | |
| 5   | Wayken | `https://waykenrm.com/blogs/`  | |
| 6   | JLCCNC | `https://jlccnc.com/blog/` | |
| 7   | Partmfg | `https://www.partmfg.com/blog/` | |
| 8   | China-Machining | `https://www.china-machining.com/blog/` | |
| 9   | HLC-Metalparts | `https://www.hlc-metalparts.com/newslist-1`  | 已找到直接访问链接 |
| 10  | Zintilon | `https://www.zintilon.com/blog/`  | |
| 11  | CNC Lathing | `https://www.google.com/search?q=site:cnclathing.com/blog&tbs=qdr:w`  | 需要使用 Google 搜索结果作为数据源 (防爬虫) |

> **注意**：部分站点（如 Fictiv, HLC-Metalparts, CNC Lathing）因反爬策略或动态加载问题，可能需要使用 Google 搜索结果页（site:domain/blog）作为替代数据源。

---

## 3. 功能需求

### 3.1 定时任务

- **执行时间**：每天早上 **08:00**（北京时间）。
- **频率**：1次/24小时。
- **容错**：若任务失败，自动重试机制（见 4.3）。

### 3.2 增量识别逻辑（Top 3 快照法）

系统无需抓取全站，只需执行以下步骤：

1.  **解析**：进入博客列表页，提取前 **3 条**文章的 **标题(Title)** 和 **链接(URL)**。
2.  **比对**：将当前抓取的 Top 3 与本地存储的“昨日 Top 3”进行 URL 唯一性对比。
3.  **判定**：
    -   若当前 Top 3 中的某个 URL 在昨日记录中不存在，则视为**新增文章**。
    -   若无变化，则跳过该站点。
4.  **更新**：无论是否有新文章，任务结束后均更新本地存储的 Top 3 数据，保持最新状态。

### 3.3 关键词过滤

针对判定的“新增文章”，需检测其 **标题(Title)** 或 **摘要(Summary)** 是否包含以下关键词（不区分大小写）：

-   **CNC**
-   **machining**

### 3.4 通知机制

-   **平台**：
    1.  **Telegram Bot** (即时消息)
    2.  **Email** (邮件通知)
-   **触发条件**：发现新文章 **且** 包含上述任一关键词。
-   **通知格式**：

    **1. Telegram 消息：**
    > 📢 **【竞品动态提醒】**
    >
    > **厂商**：[厂商名称]
    > **标题**：[文章标题]
    > **链接**：[文章URL]
    > **检测时间**：YYYY-MM-DD HH:MM

    **2. Email 邮件：**
    -   **标题**：`【竞品监控】发现新文章提醒 - [日期]`
    -   **内容**：包含新文章详情的 HTML 表格（厂商、标题、链接、摘要）。

---

## 4. 技术规格

### 4.1 数据流图 (Data Flow)

```mermaid
graph TD
    A[开始定时任务 (08:00)] --> B{读取目标列表};
    B --> C[遍历竞争对手站点];
    C --> D[发送 HTTP 请求];
    D --> E{请求成功?};
    E -- 否 --> F[记录错误 & 稍后重试];
    E -- 是 --> G[解析 HTML 获取 Top 3 文章];
    G --> H{解析成功?};
    H -- 否 (为空) --> I[发送爬虫失效报警];
    H -- 是 --> J[读取本地 data.json];
    J --> K{URL 是否为新?};
    K -- 否 --> L[跳过];
    K -- 是 --> M{包含关键词? (CNC/Machining)};
    M -- 否 --> N[忽略通知];
    M -- 是 --> O[发送 Telegram 消息];
    O --> P[更新本地 data.json];
    L --> P;
    N --> P;
    P --> Q{还有下一个站点?};
    Q -- 是 --> C;
    Q -- 否 --> R[结束任务];
```

### 4.2 技术栈建议

-   **核心语言**：Python 3.10+
-   **网络请求**：
    -   `requests` 或 `httpx`：用于基础静态页面抓取。
    -   `fake-useragent`：用于随机切换 User-Agent。
-   **HTML 解析**：`BeautifulSoup4` (bs4)。
-   **数据存储**：
    -   轻量级 `JSON` 文件 (data.json)：适合当前数据量级。
    -   可选 `SQLite`：若后期需保留历史归档。
-   **消息通知**：
    -   `python-telegram-bot`：Telegram Bot API。
    -   `smtplib` + `email` (标准库)：用于发送邮件通知 (SMTP)。
-   **任务调度**：GitHub Actions (推荐，免费且稳定) 或 本地 Crontab / Windows Task Scheduler。

### 4.3 异常处理机制

1.  **请求失败**：
    -   若站点返回 4xx/5xx 或超时，记录 Error Log。
    -   实施指数退避策略，或在 10 分钟后重试一次。
2.  **结构变更/解析为空**：
    -   若请求成功但解析出的文章列表为空（可能是网站改版或选择器失效），需发送一次“⚠️ **爬虫失效提醒**”给管理员。
3.  **反爬虫对抗**：
    -   **UA 伪装**：每次请求随机切换 User-Agent。
    -   **请求间隔**：不同站点之间增加 2-5 秒随机延时，避免触发 IP 封禁。

---

## 5. 存储结构示例 (data.json)

文件将存储每个站点的最新快照状态：

```json
{
  "3erp": [
    {
      "title": "CNC Tips 2026",
      "url": "https://www.3erp.com/blog/cnc-tips",
      "date": "2026-02-13"
    },
    {
      "title": "Machining Guide",
      "url": "https://www.3erp.com/blog/guide",
      "date": "2026-02-12"
    },
    {
      "title": "Old Article",
      "url": "https://www.3erp.com/blog/old",
      "date": "2026-02-10"
    }
  ],
  "fictiv": [
      // ...
  ]
}
```

### 5.4 已知限制 (Known Limitations)
-   **反爬虫保护 (Anti-Bot Protection)**:
    -   **CNC Lathing** (`cnclathing.com`) 启用了 Cloudflare 高级防护，当前的 `requests` 方案会返回 403 Forbidden。
    -   **Fictiv** (`fictiv.com`) 可能返回通用页面元素而非博客文章，建议在生产环境中使用 Selenium 或 Playwright 进行精确抓取。
-   **Google/DuckDuckGo 搜索**:
    -   使用搜索结果作为数据源时，可能会遇到验证码或临时封锁。建议仅作为备用方案。

## 6. 项目文件结构建议

```text
Trae_CNC_Monitor/
├── main.py              # 主程序入口
├── config.py            # 配置文件 (URL列表, Telegram Token, 关键词)
├── utils/
│   ├── notifier.py      # Telegram 通知模块
│   ├── parser.py        # 页面解析逻辑 (针对不同站点)
│   └── storage.py       # JSON 读写操作
├── data.json            # 本地数据存储
├── requirements.txt     # 依赖库列表
├── .github/
│   └── workflows/
│       └── daily_monitor.yml # GitHub Actions 配置 (可选)
└── README.md            # 项目说明文档
```

## 7. 下一步行动计划

1.  **环境搭建**：初始化 Python 环境，安装 `requests`, `beautifulsoup4`, `python-telegram-bot`。
2.  **解析器开发**：针对 11 个站点逐一编写 CSS 选择器规则（这是工作量最大的部分）。
3.  **核心逻辑实现**：编写“比对-通知-更新”的主循环逻辑。
4.  **测试验证**：手动模拟新文章发布，测试通知是否触发。
5.  **部署**：配置定时任务。
