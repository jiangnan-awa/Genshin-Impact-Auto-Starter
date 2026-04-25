import json
import os
import time
import uuid
import traceback
from .security import decrypt_cookie
from . import config_paths
from .log_actions import log_action
from .secret_store import DpapiFileStore, select_default_store
SENSITIVE_KEYS = {"cookie", "game_cookie", "miyoushe_cookie", "stoken", "mid", "stuid"}
class AccountManager:
    def __init__(self, secret_store=None):
        self.base_path = ""
        self.accounts_file = ""
        self.settings_file = ""
        self.old_config_file = ""
        self._init_path()
        self.secret_store = secret_store or select_default_store(base_path=self.base_path)
        self.accounts = []
        self.settings = {
            "bettergi_path": "",
            "bettergi_onedragon_config": "",
            "bettergi_onedragon_config_2": "",
            "genshin_path": "",
            "external_launcher_path": "",
            "external_launcher_args": "",
            "external_launcher_wait_seconds": 5,
            "signin_order": ["genshin", "starrail", "zzz", "miyoushe"],
            "daily_signin_once": True,
            "skip_captcha_items_today": True,
            "mod_path": "",
            "mod_wait_seconds": 6,
            "last_signin_date": ""
            ,
            "debug_mode": False,
        }
        self.load_data()
        if not isinstance(self.settings.get("signin_order"), list) or not self.settings.get("signin_order"):
            self.settings["signin_order"] = ["genshin", "starrail", "zzz", "miyoushe"]
        if self.settings.get("daily_signin_once") is None:
            self.settings["daily_signin_once"] = True
        if self.settings.get("last_signin_date") is None:
            self.settings["last_signin_date"] = ""
        if self.settings.get("skip_captcha_items_today") is None:
            self.settings["skip_captcha_items_today"] = True
        if self.settings.get("mod_path") is None:
            self.settings["mod_path"] = ""
        if self.settings.get("mod_wait_seconds") is None:
            self.settings["mod_wait_seconds"] = 6
        if self.settings.get("external_launcher_path") is None:
            self.settings["external_launcher_path"] = ""
        if self.settings.get("external_launcher_args") is None:
            self.settings["external_launcher_args"] = ""
        if self.settings.get("external_launcher_wait_seconds") is None:
            self.settings["external_launcher_wait_seconds"] = 5
        if self.settings.get("bettergi_onedragon_config") is None:
            self.settings["bettergi_onedragon_config"] = ""
        if self.settings.get("bettergi_onedragon_config_2") is None:
            self.settings["bettergi_onedragon_config_2"] = ""
        try:
            self._apply_debug_mode()
        except Exception:
            pass
    def _init_path(self):
        paths = config_paths.get_config_paths()
        self.base_path = paths.base_path
        self.accounts_file = paths.accounts_file
        self.settings_file = paths.settings_file
        self.old_config_file = os.path.join(paths.base_path, "config.ini")
    def _override_base_path_for_tests(self, base_path: str) -> None:
        paths = config_paths.get_config_paths(base_path)
        self.base_path = paths.base_path
        self.accounts_file = paths.accounts_file
        self.settings_file = paths.settings_file
        self.old_config_file = os.path.join(paths.base_path, "config.ini")
        try:
            if hasattr(self.secret_store, "_base_path"):
                self.secret_store._base_path = self.base_path  # type: ignore[attr-defined]
        except Exception:
            pass
    def load_data(self):
        self._load_settings_file()
        self._load_accounts_file()
        try:
            self._apply_debug_mode()
        except Exception:
            pass
    def _is_debug(self) -> bool:
        try:
            return bool(self.settings.get("debug_mode"))
        except Exception:
            return False
    def _apply_debug_mode(self) -> None:
        enabled = self._is_debug()
        try:
            from .loghelper import setup_logging  # pylint: disable=import-outside-toplevel
            setup_logging(base_path=self.base_path, debug=enabled)
        except Exception:
            return
    def _sanitize_debug_text(self, text: str) -> str:
        if not text:
            return ""
        s = str(text)
        for k in ["cookie", "stoken", "token", "mid", "stuid", "ltoken", "account_id"]:
            s = s.replace(f"{k}=", f"{k}=masked")
            s = s.replace(f"{k}:", f"{k}: masked")
            s = s.replace(f"\"{k}\":", f"\"{k}\": \"masked\"")
            s = s.replace(f"'{k}':", f"'{k}': 'masked'")
        return s
    def _format_call_path(self, exc: Exception) -> str:
        try:
            tb = traceback.extract_tb(exc.__traceback__) if exc.__traceback__ else []
        except Exception:
            tb = []
        frames = []
        for fr in tb:
            fn = str(fr.filename or "")
            if "autostarter" not in fn:
                continue
            frames.append(f"{os.path.basename(fn)}:{fr.name}:{fr.lineno}")
        return " -> ".join(frames[-10:])
    def _extract_error_kv(self, exc: Exception) -> dict:
        kv = {"exc_type": exc.__class__.__name__}
        for attr in ["winerror", "errno", "hresult"]:
            try:
                v = getattr(exc, attr, None)
            except Exception:
                v = None
            if v is not None:
                kv[attr] = v
        try:
            if isinstance(getattr(exc, "args", None), tuple) and len(exc.args) >= 2:
                kv.setdefault("op", str(exc.args[1]))
        except Exception:
            pass
        return kv
    def save_data(self):
        ok_accounts = self._save_accounts_file()
        ok_settings = self._save_settings_file()
        return bool(ok_accounts and ok_settings)
    def _load_settings_file(self):
        if not os.path.exists(self.settings_file):
            return
        try:
            with open(self.settings_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                self.settings.update(data)
                removed = False
                for k in [
                    "bettergi_enabled",
                    "bettergi_onedragon_enabled",
                    "external_launcher_mode",
                    "mod_enabled",
                ]:
                    if k in self.settings:
                        try:
                            self.settings.pop(k, None)
                            removed = True
                        except Exception:
                            pass
                if removed:
                    try:
                        self._save_settings_file()
                    except Exception:
                        pass
        except Exception:
            return
    def _load_accounts_file(self):
        if not os.path.exists(self.accounts_file):
            self.accounts = []
            return
        try:
            with open(self.accounts_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            self.accounts = []
            return
        if isinstance(data, list):
            self.accounts = data
            return
        if not isinstance(data, dict):
            self.accounts = []
            return
        accounts = data.get("accounts", [])
        self.accounts = accounts if isinstance(accounts, list) else []
        try:
            self._upgrade_accounts_security_if_needed()
        except Exception:
            pass
    def _secret_ref(self, account_id: str) -> str:
        return f"GenshinAutoStarter/{account_id}"
    def _decrypt_if_possible(self, val: str) -> str:
        if not val:
            return ""
        try:
            dec = decrypt_cookie(val)
            return dec if dec else val
        except Exception:
            return val
    def _upgrade_accounts_security_if_needed(self) -> None:
        if not isinstance(self.accounts, list) or not self.accounts:
            return
        if not hasattr(self.secret_store, "save"):
            return
        changed = False
        for acc in self.accounts:
            if not isinstance(acc, dict):
                continue
            aid = str(acc.get("id") or "").strip()
            if not aid:
                continue
            payload = {}
            for k in list(SENSITIVE_KEYS):
                if k in acc and acc.get(k):
                    payload[k] = self._decrypt_if_possible(str(acc.get(k) or ""))
            if not payload:
                if acc.get("secret_ref") and acc.get("secret_backend"):
                    continue
                if acc.get("secret_ref"):
                    acc["secret_backend"] = getattr(self.secret_store, "backend_name", "unknown")
                    changed = True
                continue
            ref = str(acc.get("secret_ref") or self._secret_ref(aid))
            backend = getattr(self.secret_store, "backend_name", "unknown")
            log_action("AccountManager", "secure_migration", "start", account_id=aid, secret_backend=backend)
            self.secret_store.save(ref, payload)
            for k in list(SENSITIVE_KEYS):
                if k in acc:
                    acc.pop(k, None)
            acc["secret_ref"] = ref
            acc["secret_backend"] = backend
            changed = True
            log_action("AccountManager", "secure_migration", "ok", account_id=aid, secret_backend=backend)
        if not changed:
            return
        try:
            backup = self.accounts_file + f".bak_secure_migration_{time.strftime('%Y%m%d_%H%M%S')}"
            if os.path.exists(self.accounts_file):
                try:
                    with open(self.accounts_file, "rb") as fsrc:
                        raw = fsrc.read()
                    with open(backup, "wb") as fdst:
                        fdst.write(raw)
                except Exception:
                    pass
        except Exception:
            pass
        self._save_accounts_file()
    def _save_accounts_file(self) -> bool:
        log_action("AccountManager", "save_accounts", "start", count=len(self.accounts))
        try:
            os.makedirs(os.path.dirname(self.accounts_file), exist_ok=True)
            with open(self.accounts_file, "w", encoding="utf-8") as f:
                json.dump({"accounts": self.accounts}, f, ensure_ascii=False, indent=2)
            log_action("AccountManager", "save_accounts", "ok", count=len(self.accounts))
            return True
        except Exception:
            log_action("AccountManager", "save_accounts", "fail", count=len(self.accounts), reason="exception")
            return False
    def _save_settings_file(self) -> bool:
        log_action("AccountManager", "save_settings", "start", count=len(self.settings))
        try:
            os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
            log_action("AccountManager", "save_settings", "ok", count=len(self.settings))
            return True
        except Exception:
            log_action("AccountManager", "save_settings", "fail", count=len(self.settings), reason="exception")
            return False
    def load_accounts(self):
        self.load_data()
    def save_accounts(self):
        return self.save_data()
    def add_account(self, name, game_cookie="", miyoushe_cookie="", stoken="", mid="", stuid=""):
        aid = str(uuid.uuid4())
        ref = self._secret_ref(aid)
        backend = getattr(self.secret_store, "backend_name", "unknown")
        payload = {
            "game_cookie": str(game_cookie or ""),
            "miyoushe_cookie": str(miyoushe_cookie or ""),
            "stoken": str(stoken or ""),
            "mid": str(mid or ""),
            "stuid": str(stuid or ""),
        }
        try:
            self.secret_store.save(ref, payload)
        except Exception:
            kv = {"secret_backend": backend, "reason": "save_failed"}
            log_action("AccountManager", "add_account", "fail", **kv)
            return False
        account = {
            "id": aid,
            "name": name,
            "secret_ref": ref,
            "secret_backend": backend,
            "enable_genshin": True,
            "enable_starrail": True,
            "enable_zzz": True,
            "enable_miyoushe": True,
            "enable_bbs_read": True,
            "enable_bbs_like": True,
            "enable_bbs_share": True,
        }
        self.accounts.append(account)
        self.save_accounts()
        return True
    def get_accounts(self):
        decrypted_accounts = []
        for acc in self.accounts:
            new_acc = acc.copy()
            ref = str(acc.get("secret_ref") or self._secret_ref(str(acc.get("id") or "")))
            try:
                secret = self.secret_store.load(ref)
            except Exception:
                secret = {}
            if isinstance(secret, dict):
                for k in SENSITIVE_KEYS:
                    if k in secret:
                        new_acc[k] = str(secret.get(k) or "")
            for k in SENSITIVE_KEYS:
                new_acc.setdefault(k, "")
            if not new_acc.get('game_cookie') and new_acc.get('cookie'):
                new_acc['game_cookie'] = new_acc['cookie']
            if not new_acc.get('miyoushe_cookie') and new_acc.get('cookie'):
                new_acc['miyoushe_cookie'] = new_acc['cookie']
            if 'enable_bbs_read' not in new_acc:
                new_acc['enable_bbs_read'] = True
            if 'enable_bbs_like' not in new_acc:
                new_acc['enable_bbs_like'] = True
            if 'enable_bbs_share' not in new_acc:
                new_acc['enable_bbs_share'] = True
            decrypted_accounts.append(new_acc)
        return decrypted_accounts
    def update_account(self, account_id, **kwargs):
        changed_keys = sorted([str(k) for k in kwargs.keys()])
        log_action(
            "AccountManager",
            "update_account",
            "start",
            account_id=str(account_id),
            changed_keys=",".join(changed_keys),
        )
        for acc in self.accounts:
            if acc['id'] == account_id:
                secret_update = {k: kwargs.get(k) for k in SENSITIVE_KEYS if k in kwargs}
                if secret_update:
                    ref = str(acc.get("secret_ref") or self._secret_ref(str(account_id)))
                    try:
                        cur = self.secret_store.load(ref) if hasattr(self.secret_store, "load") else {}
                    except Exception:
                        cur = {}
                    if not isinstance(cur, dict):
                        cur = {}
                    for k, v in secret_update.items():
                        cur[k] = str(v or "")
                    try:
                        self.secret_store.save(ref, cur)
                        acc["secret_ref"] = ref
                        acc["secret_backend"] = getattr(self.secret_store, "backend_name", "unknown")
                    except Exception:
                        log_action(
                            "AccountManager",
                            "update_account",
                            "fail",
                            account_id=str(account_id),
                            reason="save_failed",
                        )
                        return False
                for k, v in kwargs.items():
                    if k in SENSITIVE_KEYS:
                        continue
                    acc[k] = v
                ok = bool(self.save_accounts())
                if ok:
                    log_action(
                        "AccountManager",
                        "update_account",
                        "ok",
                        account_id=str(account_id),
                        count=len(self.accounts),
                        changed_keys=",".join(changed_keys),
                    )
                else:
                    log_action(
                        "AccountManager",
                        "update_account",
                        "fail",
                        account_id=str(account_id),
                        count=len(self.accounts),
                        changed_keys=",".join(changed_keys),
                        reason="save_failed",
                    )
                return True
        log_action(
            "AccountManager",
            "update_account",
            "fail",
            account_id=str(account_id),
            changed_keys=",".join(changed_keys),
            reason="account_not_found",
        )
        return False
    def delete_account(self, account_id):
        self.accounts = [acc for acc in self.accounts if acc['id'] != account_id]
        self.save_accounts()
    def get_settings(self):
        return self.settings.copy()
    def update_settings(self, **kwargs):
        changed_keys = sorted([str(k) for k in kwargs.keys()])
        log_action(
            "AccountManager",
            "update_settings",
            "start",
            changed_keys=",".join(changed_keys),
            count=len(kwargs),
        )
        self.settings.update(kwargs)
        ok = bool(self._save_settings_file())
        if ok:
            log_action(
                "AccountManager",
                "update_settings",
                "ok",
                changed_keys=",".join(changed_keys),
                count=len(kwargs),
            )
        else:
            log_action(
                "AccountManager",
                "update_settings",
                "fail",
                changed_keys=",".join(changed_keys),
                count=len(kwargs),
                reason="save_failed",
            )
        if "debug_mode" in kwargs:
            try:
                self._apply_debug_mode()
            except Exception:
                pass
    def parse_cookie(self, cookie_str):
        fields = {}
        if not cookie_str:
            return fields
        import re
        patterns = {
            'stoken': r'stoken=([^;]+)',
            'stoken_v2': r'stoken_v2=([^;]+)',
            'mid': r'mid=([^;]+)',
            'mid_v2': r'mid_v2=([^;]+)',
            'stuid': r'stuid=([^;]+)',
            'ltoken': r'ltoken=([^;]+)',
            'ltoken_v2': r'ltoken_v2=([^;]+)',
            'cookie_token': r'cookie_token=([^;]+)',
            'cookie_token_v2': r'cookie_token_v2=([^;]+)',
            'login_ticket': r'login_ticket=([^;]+)',
            'login_uid': r'login_uid=([^;]+)',
            'account_id': r'account_id=([^;]+)',
            'account_id_v2': r'account_id_v2=([^;]+)',
            'ltuid': r'ltuid=([^;]+)',
            'ltuid_v2': r'ltuid_v2=([^;]+)',
            'account_mid_v2': r'account_mid_v2=([^;]+)',
        }
        for key, pattern in patterns.items():
            strict_pattern = rf'(?:^|;)\s*{key}=([^;]+)'
            match = re.search(strict_pattern, cookie_str)
            if match:
                fields[key] = match.group(1).strip()
        if 'stoken_v2' in fields:
            fields['stoken'] = fields['stoken_v2']
        if 'ltoken_v2' in fields:
            fields['ltoken'] = fields['ltoken_v2']
        if 'account_mid_v2' in fields:
            fields['mid'] = fields['account_mid_v2']
        elif 'mid_v2' in fields:
            fields['mid'] = fields['mid_v2']
        if 'stuid' not in fields:
            for k in ['account_id_v2', 'account_id', 'ltuid_v2', 'ltuid', 'login_uid']:
                if k in fields:
                    fields['stuid'] = fields[k]
                    break
        return fields
account_manager = AccountManager()
