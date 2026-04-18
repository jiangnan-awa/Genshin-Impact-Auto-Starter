import logging
import os
from logging.handlers import TimedRotatingFileHandler
from typing import Optional

from .config_paths import detect_base_path


_LOG_FORMAT = "%(asctime)s %(levelname)s %(message)s"
_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"
_LOGGER_NAME = "AutoStarter"


def _make_rotating_namer(logs_dir: str):
    """
    将 TimedRotatingFileHandler 默认生成的文件名：
      <...>/autostarter.log.YYYY-MM-DD
    重命名为：
      <...>/autostarter-YYYY-MM-DD.log
    """

    def namer(default_name: str) -> str:
        base = os.path.basename(default_name)
        # 兼容 handler.suffix="%Y-%m-%d" 的默认命名：autostarter.log.2026-04-18
        date_part = base.split(".")[-1] if "." in base else base
        return os.path.join(logs_dir, f"autostarter-{date_part}.log")

    return namer


def setup_logging(base_path: Optional[str] = None) -> logging.Logger:
    """
    幂等初始化日志系统：
    - 默认写入 <base_path>/logs/autostarter.log
    - TimedRotatingFileHandler: when='midnight', backupCount=14, encoding='utf-8'
    - handler.namer: autostarter-YYYY-MM-DD.log
    - 同时输出到控制台（StreamHandler）
    - logger 名称 AutoStarter，propagate=False
    - 将 httpx logger 设为 CRITICAL
    """
    bp = base_path or detect_base_path()
    logs_dir = os.path.join(bp, "logs")
    os.makedirs(logs_dir, exist_ok=True)

    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    formatter = logging.Formatter(fmt=_LOG_FORMAT, datefmt=_DATE_FORMAT)

    log_file_path = os.path.join(logs_dir, "autostarter.log")

    # 幂等：避免重复添加 handler（允许外部先清空 handlers 以便重配）
    has_file_handler = False
    has_stream_handler = False
    for h in list(logger.handlers):
        if isinstance(h, TimedRotatingFileHandler):
            try:
                if os.path.abspath(getattr(h, "baseFilename", "")) == os.path.abspath(
                    log_file_path
                ):
                    has_file_handler = True
            except Exception:
                # baseFilename 读取失败则不视为已配置
                pass
        elif isinstance(h, logging.StreamHandler) and not isinstance(
            h, TimedRotatingFileHandler
        ):
            # TimedRotatingFileHandler 是 FileHandler 子类，不应算作 StreamHandler
            has_stream_handler = True

    if not has_file_handler:
        file_handler = TimedRotatingFileHandler(
            filename=log_file_path,
            when="midnight",
            backupCount=14,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)
        file_handler.suffix = "%Y-%m-%d"
        file_handler.namer = _make_rotating_namer(logs_dir)
        logger.addHandler(file_handler)

    if not has_stream_handler:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        stream_handler.setLevel(logging.INFO)
        logger.addHandler(stream_handler)

    # 获取httpx的日志记录器，并将其级别设置为CRITICAL，让日志不再输出httpx的相关日志
    logging.getLogger("httpx").setLevel(logging.CRITICAL)

    return logger

log = setup_logging()
