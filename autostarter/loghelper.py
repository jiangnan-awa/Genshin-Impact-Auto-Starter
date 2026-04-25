import logging
import os
import re
import time
from typing import Optional
from .config_paths import detect_base_path
_LOG_FORMAT = "%(asctime)s %(levelname)s %(message)s"
_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"
_LOGGER_NAME = "AutoStarter"
def setup_logging(base_path: Optional[str] = None, *, debug: bool = False) -> logging.Logger:
    bp = base_path or detect_base_path()
    logs_dir = os.path.join(bp, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    try:
        pat = re.compile(r"^autostarter-(\d{4}-\d{2}-\d{2})\.log$")
        now = time.time()
        max_age_sec = 14 * 24 * 3600
        for fn in os.listdir(logs_dir):
            m = pat.match(fn)
            if not m:
                continue
            full = os.path.join(logs_dir, fn)
            try:
                if now - os.path.getmtime(full) > max_age_sec:
                    os.remove(full)
            except Exception:
                pass
    except Exception:
        pass
    level = logging.DEBUG if bool(debug) else logging.INFO
    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(level)
    logger.propagate = False
    formatter = logging.Formatter(fmt=_LOG_FORMAT, datefmt=_DATE_FORMAT)
    today = time.strftime("%Y-%m-%d", time.localtime())
    log_file_path = os.path.join(logs_dir, f"autostarter-{today}.log")
    has_file_handler = False
    has_stream_handler = False
    for h in list(logger.handlers):
        if isinstance(h, logging.FileHandler):
            try:
                if os.path.abspath(getattr(h, "baseFilename", "")) == os.path.abspath(
                    log_file_path
                ):
                    has_file_handler = True
                try:
                    h.setLevel(level)
                except Exception:
                    pass
            except Exception:
                pass
        elif isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler):
            has_stream_handler = True
            try:
                h.setLevel(level)
            except Exception:
                pass
    if not has_file_handler:
        file_handler = logging.FileHandler(filename=log_file_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        file_handler.setLevel(level)
        logger.addHandler(file_handler)
    if not has_stream_handler:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        stream_handler.setLevel(level)
        logger.addHandler(stream_handler)
    logging.getLogger("httpx").setLevel(logging.CRITICAL)
    return logger
log = setup_logging()
