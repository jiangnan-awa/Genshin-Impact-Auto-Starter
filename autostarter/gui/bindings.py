from __future__ import annotations
from typing import Any, Callable, Dict, List, Optional, Tuple
def bind_default_shortcuts(root: object, on_reload: Optional[Callable[[], None]] = None) -> None:
    if not hasattr(root, "bind"):
        return
    def _safe_call(_event=None):
        if on_reload is not None:
            on_reload()
    try:
        root.bind("<Control-r>", _safe_call)  # type: ignore[attr-defined]
    except Exception:
        return
def load_accounts() -> List[Dict[str, Any]]:
    from autostarter.account_manager import account_manager
    return account_manager.get_accounts()
def load_settings() -> Dict[str, Any]:
    from autostarter.account_manager import account_manager
    return account_manager.get_settings()
def add_account(name: str) -> bool:
    from autostarter.account_manager import account_manager
    return bool(account_manager.add_account(name))
def delete_account(account_id: str) -> None:
    from autostarter.account_manager import account_manager
    account_manager.delete_account(account_id)
def update_account(account_id: str, **kwargs: Any) -> bool:
    from autostarter.account_manager import account_manager
    return bool(account_manager.update_account(account_id, **kwargs))
def update_settings(**kwargs: Any) -> None:
    from autostarter.account_manager import account_manager
    account_manager.update_settings(**kwargs)
def parse_cookie(cookie_str: str) -> Dict[str, str]:
    from autostarter.account_manager import account_manager
    parsed = account_manager.parse_cookie(cookie_str)
    return parsed if isinstance(parsed, dict) else {}
def auto_get_game_cookie() -> str:
    from autostarter.cookie_login import get_cookie_auto
    cookie = get_cookie_auto()
    return cookie or ""
def qr_get_miyoushe_cookie(
    *,
    timeout_seconds: int = 180,
    status_callback: Optional[Callable[[str], None]] = None,
) -> Tuple[str, Dict[str, str]]:
    from autostarter import qr_login_handler as qr
    qr_url, app_id, ticket, device = qr.create_qr_session()
    if status_callback is not None:
        status_callback(f"二维码已生成：{qr_url}")
    uid, game_token = qr.poll_qr_login(
        app_id=app_id,
        ticket=ticket,
        device=device,
        timeout_seconds=timeout_seconds,
        status_callback=status_callback,
    )
    mid, stoken = qr.get_stoken_by_game_token(uid=uid, game_token=game_token)
    cookie = qr.build_miyoushe_cookie(uid=uid, mid=mid, stoken=stoken)
    return cookie, {"stuid": str(uid), "mid": str(mid), "stoken": str(stoken)}
__all__ = [
    "bind_default_shortcuts",
    "load_accounts",
    "load_settings",
    "add_account",
    "delete_account",
    "update_account",
    "update_settings",
    "parse_cookie",
    "auto_get_game_cookie",
    "qr_get_miyoushe_cookie",
]
