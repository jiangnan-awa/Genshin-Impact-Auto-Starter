"""
autostarter.gui.bindings

集中管理 GUI 与业务层的轻量绑定/封装。

导入时不得创建 Tk，也不得调用 mainloop。
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional


BindingMap = Dict[str, Callable[[], None]]


def install_bindings(root: Any, bindings: Optional[BindingMap] = None) -> None:
    """
    为 root 安装事件绑定（骨架实现）。

    参数：
    - root: Tk/CTk 根窗口或任意支持 bind 的对象
    - bindings: {"<Control-q>": callback, ...}
    """
    if not bindings:
        return

    for sequence, callback in bindings.items():
        try:
            root.bind(sequence, lambda _evt=None, cb=callback: cb())
        except Exception:
            # headless DummyTk 或不兼容对象：忽略
            continue


def load_accounts() -> List[dict]:
    """
    读取账号列表（解密后的副本）。
    """
    from autostarter.account_manager import account_manager

    return account_manager.get_accounts()


def save_accounts() -> bool:
    """
    保存账号与设置（写入 accounts.json）。
    """
    from autostarter.account_manager import account_manager

    return bool(account_manager.save_accounts())


def load_settings() -> dict:
    from autostarter.account_manager import account_manager

    return account_manager.get_settings()


def save_settings(**kwargs) -> None:
    from autostarter.account_manager import account_manager

    account_manager.update_settings(**kwargs)


def auto_get_cookie() -> str:
    """
    通过浏览器自动获取国服 Cookie（与旧版 gui.py 行为一致）。
    """
    from autostarter.cookie_login import get_cookie_auto

    return get_cookie_auto()


__all__ = [
    "BindingMap",
    "install_bindings",
    "load_accounts",
    "save_accounts",
    "load_settings",
    "save_settings",
    "auto_get_cookie",
]
