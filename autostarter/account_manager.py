import json
import os
import uuid
import configparser
import shutil
from .security import encrypt_cookie, decrypt_cookie
from . import config_paths
from .log_actions import log_action

class AccountManager:
    def __init__(self):
        self.base_path = ""
        self.accounts_file = ""
        self.settings_file = ""
        self.old_config_file = ""
        self._init_path()
        self.accounts = []
        self.settings = {
            "bettergi_enabled": True,
            "bettergi_path": "",
            "bettergi_onedragon_enabled": False,
            "bettergi_onedragon_config": "",
            "bettergi_onedragon_config_2": "",
            "genshin_path": "",
            "external_launcher_mode": False,
            "external_launcher_path": "",
            "external_launcher_args": "",
            "external_launcher_wait_seconds": 5,
            "signin_order": ["genshin", "starrail", "zzz", "miyoushe"],
            "daily_signin_once": True,
            "skip_captcha_items_today": True,
            "mod_enabled": False,
            "mod_path": "",
            "mod_wait_seconds": 6,
            "last_signin_date": ""
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
        if self.settings.get("mod_enabled") is None:
            self.settings["mod_enabled"] = False
        if self.settings.get("mod_path") is None:
            self.settings["mod_path"] = ""
        if self.settings.get("mod_wait_seconds") is None:
            self.settings["mod_wait_seconds"] = 6
        if self.settings.get("external_launcher_mode") is None:
            self.settings["external_launcher_mode"] = False
        if self.settings.get("external_launcher_path") is None:
            self.settings["external_launcher_path"] = ""
        if self.settings.get("external_launcher_args") is None:
            self.settings["external_launcher_args"] = ""
        if self.settings.get("external_launcher_wait_seconds") is None:
            self.settings["external_launcher_wait_seconds"] = 5
        if self.settings.get("bettergi_onedragon_enabled") is None:
            self.settings["bettergi_onedragon_enabled"] = False
        if self.settings.get("bettergi_onedragon_config") is None:
            self.settings["bettergi_onedragon_config"] = ""
        if self.settings.get("bettergi_onedragon_config_2") is None:
            self.settings["bettergi_onedragon_config_2"] = ""
        self._migrate_from_old_config()

    def _init_path(self):
        paths = config_paths.get_config_paths()
        # 迁移旧版根目录文件到 config/（不覆盖已有目标）
        config_paths.migrate_root_files_to_config_dir(paths.base_path)

        self.base_path = paths.base_path
        self.accounts_file = paths.accounts_file
        self.settings_file = paths.settings_file
        # config.ini 仍保留在根目录（历史遗留）
        self.old_config_file = os.path.join(paths.base_path, "config.ini")

    def _override_base_path_for_tests(self, base_path: str) -> None:
        """
        仅供测试用：覆盖配置文件所在目录，避免污染真实环境。

        tests/test_config_migration.py 会依赖该方法。
        """
        paths = config_paths.get_config_paths(base_path)
        # 测试用：允许在临时目录模拟旧版根目录文件
        config_paths.migrate_root_files_to_config_dir(paths.base_path)

        self.base_path = paths.base_path
        self.accounts_file = paths.accounts_file
        self.settings_file = paths.settings_file
        self.old_config_file = os.path.join(paths.base_path, "config.ini")

    def load_data(self):
        """
        读取账号与全局设置。

        文件位置：默认位于 base_path/config/ 下：
        - accounts.json：仅账号列表（{"accounts": [...]} 或兼容旧版 list）
        - settings.json：仅全局设置（dict）

        自动迁移（兼容旧版混存格式）：
        若检测到旧版 accounts.json 同时包含 accounts+settings 且 settings.json 不存在，则：
        - 写入 settings.json
        - 备份 accounts.json 为 accounts.json.bak
        - 重写 accounts.json 为仅含 accounts
        """
        self._load_settings_file()
        self._load_accounts_file_with_migration()

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
                # 覆盖默认值，但不替换整个 settings（保留默认字段）
                self.settings.update(data)
        except Exception:
            # 读取失败：保留默认 settings
            return

    def _load_accounts_file_with_migration(self):
        if not os.path.exists(self.accounts_file):
            self.accounts = []
            return

        try:
            with open(self.accounts_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            self.accounts = []
            return

        # 兼容旧版本列表格式
        if isinstance(data, list):
            self.accounts = data
            return

        if not isinstance(data, dict):
            self.accounts = []
            return

        accounts = data.get("accounts", [])
        legacy_settings = data.get("settings")

        # 先加载账号（不管是否迁移都要可用）
        self.accounts = accounts if isinstance(accounts, list) else []

        # 自动迁移：accounts.json 混存 settings + settings.json 不存在
        if isinstance(legacy_settings, dict) and not os.path.exists(self.settings_file):
            self._migrate_legacy_accounts_json(data, legacy_settings)
            # 迁移完成（或部分完成）后，仍然用 legacy settings 覆盖一次内存 settings，
            # 保证本次运行行为与旧版一致。
            self.settings.update(legacy_settings)

    def _migrate_legacy_accounts_json(self, legacy_payload: dict, legacy_settings: dict) -> None:
        """
        将旧版 accounts.json（混存 accounts+settings）拆分为：
        - accounts.json：仅含 accounts
        - settings.json：仅含 settings

        迁移策略（尽量安全）：
        - 先写 settings.json
        - 再备份 accounts.json -> accounts.json.bak
        - 最后重写 accounts.json（仅账号）
        任一步失败则尽量不破坏原 accounts.json。
        """
        log_action("AccountManager", "migrate_split_settings", "start", from_file="accounts.json", to_file="settings.json")
        # 1) 写 settings.json
        try:
            tmp_settings = self.settings_file + ".tmp"
            with open(tmp_settings, "w", encoding="utf-8") as f:
                json.dump(legacy_settings, f, ensure_ascii=False, indent=2)
            os.replace(tmp_settings, self.settings_file)
        except Exception:
            # 写 settings.json 失败：不继续，避免破坏原 accounts.json
            log_action("AccountManager", "migrate_split_settings", "fail", reason="write_settings_failed")
            try:
                if os.path.exists(tmp_settings):
                    os.remove(tmp_settings)
            except Exception:
                pass
            return

        # 2) 备份 accounts.json
        backup_path = self.accounts_file + ".bak"
        try:
            if os.path.exists(backup_path):
                os.remove(backup_path)
            shutil.copy2(self.accounts_file, backup_path)
        except Exception:
            # 备份失败：不重写 accounts.json（并尽量回滚 settings.json）
            log_action("AccountManager", "migrate_split_settings", "fail", reason="backup_accounts_failed")
            try:
                if os.path.exists(self.settings_file):
                    os.remove(self.settings_file)
            except Exception:
                pass
            return

        # 3) 重写 accounts.json 为仅账号
        try:
            tmp_accounts = self.accounts_file + ".tmp"
            accounts_only = {"accounts": legacy_payload.get("accounts", [])}
            with open(tmp_accounts, "w", encoding="utf-8") as f:
                json.dump(accounts_only, f, ensure_ascii=False, indent=2)
            os.replace(tmp_accounts, self.accounts_file)
        except Exception:
            # 重写失败：保留备份与 settings.json，原 accounts.json 仍在（可能未被替换）
            log_action("AccountManager", "migrate_split_settings", "fail", reason="rewrite_accounts_failed")
            try:
                if os.path.exists(tmp_accounts):
                    os.remove(tmp_accounts)
            except Exception:
                pass
            return
        log_action("AccountManager", "migrate_split_settings", "ok", accounts_count=len(accounts_only.get("accounts") or []))

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
        # 为了兼容性保留，但逻辑移至 load_data
        self.load_data()

    def save_accounts(self):
        # 为了兼容性保留：旧版会把账号与设置一起写入一个文件。
        # 新版拆分后仍保持“保存时尽量落盘所有数据”的行为。
        return self.save_data()

    def _migrate_from_old_config(self):
        """从旧的 config.ini 迁移设置"""
        if not os.path.exists(self.old_config_file):
            return

        try:
            config = configparser.ConfigParser()
            config.read(self.old_config_file, encoding='utf-8')
            
            migrated = False

            # 1. 迁移米游社 Cookie
            if config.has_section('米游社'):
                old_cookie = config.get('米游社', 'Cookie', fallback='')
                enable_old = config.getboolean('米游社', '启用', fallback=False)
                
                if old_cookie and enable_old:
                    # 如果当前没有账号，则创建一个
                    if not self.accounts:
                        decrypted = decrypt_cookie(old_cookie)
                        if decrypted:
                            self.add_account("默认账号", miyoushe_cookie=decrypted)
                        else:
                            self.add_account("默认账号", miyoushe_cookie=old_cookie)
                        migrated = True
            
            # 2. 迁移启动设置
            if config.has_section('启动设置'):
                bettergi_enabled = config.getboolean('启动设置', 'BetterGI', fallback=None)
                if bettergi_enabled is not None:
                    self.settings['bettergi_enabled'] = bettergi_enabled
                    migrated = True
                
                bettergi_path = config.get('启动设置', 'BetterGI_path', fallback='')
                if bettergi_path:
                    self.settings['bettergi_path'] = bettergi_path
                    migrated = True
                    
                genshin_path = config.get('启动设置', 'genshin_impact_path', fallback='')
                if genshin_path:
                    self.settings['genshin_path'] = genshin_path
                    migrated = True

            if migrated:
                self.save_data()
                
            # 迁移完成后，将旧配置文件重命名为备份
            backup_path = self.old_config_file + ".bak"
            if os.path.exists(backup_path):
                os.remove(backup_path)
            os.rename(self.old_config_file, backup_path)
            
        except Exception as e:
            print(f"迁移旧配置文件时出错: {e}")

    def add_account(self, name, game_cookie="", miyoushe_cookie="", stoken="", mid="", stuid=""):
        # 确保存储的是加密后的 cookie/stoken/mid/stuid
        
        def encrypt_if_plain(val):
            if not val: return ""
            decrypted = decrypt_cookie(val)
            plain = decrypted if decrypted else val
            return encrypt_cookie(plain)

        account = {
            'id': str(uuid.uuid4()),
            'name': name,
            'game_cookie': encrypt_if_plain(game_cookie),
            'miyoushe_cookie': encrypt_if_plain(miyoushe_cookie),
            'stoken': encrypt_if_plain(stoken),
            'mid': encrypt_if_plain(mid),
            'stuid': encrypt_if_plain(stuid),
            'enable_genshin': True,
            'enable_starrail': True,
            'enable_zzz': True,
            'enable_miyoushe': True,
            'enable_bbs_read': True,
            'enable_bbs_like': True,
            'enable_bbs_share': True
        }
        self.accounts.append(account)
        self.save_accounts()
        return True

    def get_accounts(self):
        """返回带有解密数据的账号列表副本"""
        decrypted_accounts = []
        sensitive_keys = ['cookie', 'game_cookie', 'miyoushe_cookie', 'stoken', 'mid', 'stuid']
        for acc in self.accounts:
            new_acc = acc.copy()
            # 解密敏感数据
            for key in sensitive_keys:
                val = acc.get(key, '')
                new_acc[key] = decrypt_cookie(val) if val else ""
            
            # 兼容性处理：如果 game_cookie 为空且旧 cookie 存在，则复制
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
                sensitive_keys = ['cookie', 'game_cookie', 'miyoushe_cookie', 'stoken', 'mid', 'stuid']
                for k, v in kwargs.items():
                    if k in sensitive_keys:
                        # 加密敏感数据
                        if v:
                            encrypted = encrypt_cookie(v)
                            if encrypted:
                                acc[k] = encrypted
                            else:
                                print(f"警告: 账号 {acc['name']} 的 {k} 加密失败")
                        else:
                            acc[k] = ""
                    else:
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
        # settings.json 仅用于全局设置，避免每次改设置都重写 accounts.json
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

    def parse_cookie(self, cookie_str):
        """从 Cookie 字符串中解析 stoken, mid, stuid 等"""
        fields = {}
        if not cookie_str:
            return fields
            
        import re
        # 支持多种格式的解析
        # stoken=...; mid=...; stuid=...;
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
            # 使用更严谨的正则，防止 key 匹配到前缀相同的其他 key (如 stoken 匹配到 stoken_v2)
            strict_pattern = rf'(?:^|;)\s*{key}=([^;]+)'
            match = re.search(strict_pattern, cookie_str)
            if match:
                fields[key] = match.group(1).strip()
        
        # 兼容性处理
        # Stoken 优先处理 v2
        if 'stoken_v2' in fields:
            fields['stoken'] = fields['stoken_v2']

        if 'ltoken_v2' in fields:
            fields['ltoken'] = fields['ltoken_v2']
        
        # Mid 优先处理 v2
        if 'account_mid_v2' in fields:
            fields['mid'] = fields['account_mid_v2']
        elif 'mid_v2' in fields:
            fields['mid'] = fields['mid_v2']

        # Stuid 各种变体映射
        if 'stuid' not in fields:
            for k in ['account_id_v2', 'account_id', 'ltuid_v2', 'ltuid', 'login_uid']:
                if k in fields:
                    fields['stuid'] = fields[k]
                    break
            
        return fields

account_manager = AccountManager()
