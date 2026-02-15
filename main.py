"""
CNC竞品博客监控系统 - 主程序
每天08:00自动执行，监控11个竞争对手博客的最新动态
"""
import argparse
import logging
import sys
import time
from datetime import datetime

from config import TARGETS, config
from utils.parser import site_monitor
from utils.storage import storage
from utils.notifier import notifier

# 日志记录器
logger = logging.getLogger(__name__)


def setup_logging():
    """配置日志"""
    # 确保日志目录存在 - 使用相对于 cwd 的路径
    import os
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, "monitor.log")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout)
        ]
    )


def check_keywords(title: str) -> bool:
    """检查标题是否包含关键词（不区分大小写）"""
    title_upper = title.upper()
    return any(keyword in title_upper for keyword in config.keywords)


def process_site(target: dict, retry_count: int = 0):
    """处理单个站点，返回 (result, new_articles, error_msg)"""
    site_key = target["key"]
    site_name = target["name"]
    url = target["url"]
    use_google = target.get("use_google", False)

    logger.info(f"正在监控: {site_name} ({url})")

    matched_articles = []
    error_msg = None

    try:
        # 获取当前Top 3文章
        articles = site_monitor.fetch_articles(site_key, url, use_google)

        if not articles:
            # 解析失败
            logger.warning(f"站点 {site_name} 解析结果为空")
            error_msg = "解析结果为空，可能网站结构已更改"
            return False, [], error_msg

        logger.info(f"站点 {site_name} 获取到 {len(articles)} 篇文章")

        # 检查是否有新增文章
        new_articles = storage.get_new_articles(site_key, articles)

        if not new_articles:
            logger.info(f"站点 {site_name} 无新增文章")
        else:
            # 过滤包含关键词的文章
            matched_articles = [a for a in new_articles if check_keywords(a.get("title", ""))]

            if matched_articles:
                logger.info(f"站点 {site_name} 发现 {len(matched_articles)} 篇包含关键词的新文章")
            else:
                logger.info(f"站点 {site_name} 有新增文章但不包含关键词，跳过通知")

        # 无论是否有新文章，都更新快照
        storage.update_snapshot(site_key, articles)
        return True, matched_articles, None

    except Exception as e:
        logger.error(f"处理站点 {site_name} 时出错: {e}")

        # 重试机制
        if retry_count < config.retry_count:
            logger.info(f"将在 {config.retry_delay} 秒后重试 ({retry_count + 1}/{config.retry_count})")
            time.sleep(config.retry_delay)
            return process_site(target, retry_count + 1)
        else:
            error_msg = f"重试{config.retry_count}次后仍失败: {str(e)}"
            return False, [], error_msg


def run_monitor():
    """运行监控任务"""
    logger.info("=" * 60)
    logger.info(f"开始执行竞品博客监控任务 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    success_count = 0
    fail_count = 0

    # 收集所有通知
    all_new_articles = []
    all_errors = []

    for target in TARGETS:
        result, new_articles, error_msg = process_site(target)
        if result:
            success_count += 1
        else:
            fail_count += 1

        if new_articles:
            all_new_articles.extend(new_articles)
        if error_msg:
            all_errors.append({"site": target["name"], "error": error_msg})

    # 汇总发送通知
    if all_new_articles or all_errors:
        notifier.send_summary(all_new_articles, all_errors)

    logger.info("=" * 60)
    logger.info(f"监控任务完成 - 成功: {success_count}, 失败: {fail_count}")
    logger.info(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    return fail_count == 0


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="CNC竞品博客监控系统")
    parser.add_argument("--test", action="store_true", help="测试模式，仅运行一次")
    parser.add_argument("--single", type=str, help="仅监控指定站点(key)")
    args = parser.parse_args()

    setup_logging()

    if args.single:
        # 仅监控指定站点
        target = next((t for t in TARGETS if t["key"] == args.single), None)
        if target:
            process_site(target)
        else:
            logger.error(f"未找到站点: {args.single}")
            sys.exit(1)
    else:
        # 正常运行
        if args.test:
            logger.info("测试模式：运行一次监控")
            run_monitor()
        else:
            # 定时任务模式
            while True:
                now = datetime.now()
                run_time = config._config.get("task", {}).get("run_time", "08:00")
                hour, minute = map(int, run_time.split(":"))

                if now.hour == hour and now.minute < minute:
                    logger.info(f"等待到 {run_time} 执行任务...")
                    time.sleep(60)
                else:
                    # 无论成功失败都等待一天后重试
                    run_monitor()
                    logger.info("任务执行完成，等待下一次执行...")
                    time.sleep(86400)  # 24小时


if __name__ == "__main__":
    main()
