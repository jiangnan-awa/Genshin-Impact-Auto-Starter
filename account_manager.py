import json
import os
import sys
import uuid
import configparser
from security import encrypt_cookie, decrypt_cookie

class AccountManager:
    def __init__(self):
        self.config_file = ""
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
        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
        self.config_file = os.path.join(base_path, 'accounts.json')
        self.old_config_file = os.path.join(base_path, 'config.ini')

    def load_data(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self.accounts = data.get('accounts', [])
                        self.settings.update(data.get('settings', {}))
                    elif isinstance(data, list):
                        # 兼容旧版本列表格式
                        self.accounts = data
            except:
                self.accounts = []
        else:
            self.accounts = []

    def save_data(self):
        try:
            data = {
                'accounts': self.accounts,
                'settings': self.settings
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except:
            return False

    def load_accounts(self):
        # 为了兼容性保留，但逻辑移至 load_data
        self.load_data()

    def save_accounts(self):
        # 为了兼容性保留，实际调用 save_data
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
                self.save_accounts()
                return True
        return False

    def delete_account(self, account_id):
        self.accounts = [acc for acc in self.accounts if acc['id'] != account_id]
        self.save_accounts()

    def get_settings(self):
        return self.settings.copy()

    def update_settings(self, **kwargs):
        self.settings.update(kwargs)
        self.save_data()

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
