import time
import random
import string
import hashlib
import json
import uuid
import requests
import re
from datetime import date

from . import config as bbs_config
from . import gamecheckin as bbs_gamecheckin
from . import mihoyobbs as bbs_mihoyobbs
from . import error as bbs_error

GAME_CONFIGS = {
    'genshin': {
        'biz': ['hk4e_cn'],
        'act_id_cn': 'e202311201442471',
        'signgame': 'hk4e',
        'name': '原神'
    },
    'starrail': {
        'biz': ['hkrpg_cn'],
        'act_id_cn': 'e202304121516551',
        'signgame': 'hkrpg',
        'name': '崩坏：星穹铁道'
    },
    'zzz': {
        'biz': ['nap_cn'],
        'act_id_cn': 'e202406242138391',
        'act_id_cn_list': ['e202406242138391', 'e202406031448091'],
        'signgame': 'nap',
        'name': '绝区零'
    }
}

class MihoyoClient:
    def __init__(self):
        self.mihoyobbs_version = "2.99.1"
        self.ua = "Mozilla/5.0 (Linux; Android 12; Unspecified Device) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/103.0.5060.129 Mobile Safari/537.36"
        self.ua = f"{self.ua} miHoYoBBS/{self.mihoyobbs_version}"
        self.common_headers = {
            'Accept': 'application/json, text/plain, */*',
            'DS': "",
            "x-rpc-channel": "miyousheluodi",
            'Origin': 'https://webstatic.mihoyo.com',
            'x-rpc-app_version': self.mihoyobbs_version,
            'User-Agent': self.ua,
            'x-rpc-client_type': '5',
            'Referer': '',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'zh-CN,en-US;q=0.8',
            'X-Requested-With': 'com.mihoyo.hyperion',
        }

    def _today(self) -> str:
        return date.today().isoformat()

    def _get_daily_state(self, account_data) -> dict:
        state = (account_data or {}).get("daily_signin_state")
        return state if isinstance(state, dict) else {}

    def _get_item_daily_entry(self, account_data, item: str) -> dict:
        state = self._get_daily_state(account_data)
        entry = state.get(item)
        return entry if isinstance(entry, dict) else {}

    def _should_skip_item_today(self, account_data, item: str) -> str:
        item_key = "miyoushe" if (item or "").strip().lower() in {"miyoushe", "bbs"} else (item or "").strip().lower()
        try:
            from .account_manager import account_manager
            settings = account_manager.get_settings() or {}
        except Exception:
            settings = {}

        if not settings.get("daily_signin_once", True):
            return ""

        entry = self._get_item_daily_entry(account_data, item_key)
        if (entry.get("date") or "") != self._today():
            return ""

        status = (entry.get("status") or "").lower()
        if status == "captcha" and settings.get("skip_captcha_items_today", True):
            return "captcha"
        if status in {"done", "captcha"}:
            return "done"
        return ""

    def _classify_daily_status(self, text: str) -> str:
        t = (text or "").strip()
        if not t:
            return ""
        if "触发验证码" in t or "验证码" in t:
            return "captcha"
        if "已连续签到" in t or "今天获得的奖励是" in t:
            return "done"
        if "并没有绑定任何" in t or "没有绑定任何" in t:
            return "done"
        if "无可签到内容" in t or "无签到角色" in t or "无角色" in t:
            return "done"
        if "请先手动签到一次" in t or "今天已经全部完成了" in t:
            return "done"
        if "成功" in t or "已签" in t or "已签到" in t or "今天已经" in t:
            return "done"
        return ""

    def _update_daily_state(self, account_data, item: str, status: str) -> None:
        if status not in {"done", "captcha"}:
            return
        item_key = "miyoushe" if (item or "").strip().lower() in {"miyoushe", "bbs"} else (item or "").strip().lower()
        acc_id = (account_data or {}).get("id") or ""
        if not acc_id:
            return
        try:
            from .account_manager import account_manager
            # 注意：account_data 通常来自 get_accounts() 的一次性快照。
            # 在同一次运行内对多个签到项依次调用 _update_daily_state 时，
            # 如果仍然从 account_data 读取 daily_signin_state，会导致后写入的项
            # 覆盖先前项（因为快照里没有包含刚写入的新状态）。
            #
            # 这里改为从存储中读取“最新状态”再合并写回，避免只保存一个项目。
            latest_state = {}
            try:
                latest_accounts = account_manager.get_accounts() or []
                latest_acc = next((a for a in latest_accounts if (a.get("id") or "") == acc_id), None)
                if isinstance((latest_acc or {}).get("daily_signin_state"), dict):
                    latest_state = dict(latest_acc["daily_signin_state"])
            except Exception:
                latest_state = dict(self._get_daily_state(account_data))

            state = latest_state
            state[item_key] = {"date": self._today(), "status": status}
            account_manager.update_account(acc_id, daily_signin_state=state)
        except Exception:
            return

    def _generate_ds(self, q: str = "", b: str = "") -> str:
        """生成米游社DS签名"""
        t = str(int(time.time()))
        r = ''.join(random.sample(string.ascii_lowercase + string.digits, 6))
        salt = "b0EofkfMKq2saWV9fwux18J5vzcFTlex"
        s = f"salt={salt}&t={t}&r={r}&b={b}&q={q}"
        m = hashlib.md5(s.encode()).hexdigest()
        return f"{t},{r},{m}"

    def _generate_ds_web(self) -> str:
        """生成米游社网页端DS签名"""
        t = str(int(time.time()))
        r = ''.join(random.sample(string.ascii_lowercase + string.digits, 6))
        salt_web = "DlOUwIupfU6YespEUWDJmXtutuXV6owG"
        m = hashlib.md5(f"salt={salt_web}&t={t}&r={r}".encode()).hexdigest()
        return f"{t},{r},{m}"

    def _generate_ds2(self, q: str = "", b: str = "") -> str:
        t = str(int(time.time()))
        r = str(random.randint(100001, 200000))
        salt = "t0qEgfub6cvueAPgR5m9aQWWVciEer7v"
        s = f"salt={salt}&t={t}&r={r}&b={b}&q={q}"
        m = hashlib.md5(s.encode()).hexdigest()
        return f"{t},{r},{m}"

    def get_roles(self, cookie, game_key):
        """获取指定游戏的角色"""
        if not cookie: return []
        
        device_id = str(uuid.uuid4()).replace('-', '')
        headers = self.common_headers.copy()
        headers['Cookie'] = cookie
        headers['x-rpc-device_id'] = device_id
        
        config = GAME_CONFIGS.get(game_key)
        if not config: return []
        
        roles = []
        for biz in config['biz']:
            url = f'https://api-takumi.mihoyo.com/binding/api/getUserGameRolesByCookie?game_biz={biz}'

            req_headers = headers.copy()
            req_headers['DS'] = self._generate_ds(q=f'game_biz={biz}')
            
            try:
                resp = requests.get(url, headers=req_headers, timeout=10).json()
                if resp.get('retcode') == 0:
                    data_list = (resp.get('data') or {}).get('list') or []
                    for r in data_list:
                        r['game_biz'] = biz
                    roles += data_list
            except Exception:
                pass
        return roles

    def sign_in_game(self, cookie, game_key):
        """通用游戏签到"""
        roles = self.get_roles(cookie, game_key)
        if not roles:
            return "无角色"
            
        config = GAME_CONFIGS.get(game_key)
        
        results = []
        device_id = str(uuid.uuid4()).replace('-', '')
        
        for role in roles:
            is_cn = 'cn' in role.get('region', '')
            if not is_cn:
                continue

            act_id = config.get('act_id_cn')
            if game_key == 'zzz':
                info_url = 'https://act-nap-api.mihoyo.com/event/luna/zzz/info?lang=zh-cn'
                sign_url = 'https://act-nap-api.mihoyo.com/event/luna/zzz/sign'
            else:
                info_url = 'https://api-takumi.mihoyo.com/event/luna/info?lang=zh-cn'
                sign_url = 'https://api-takumi.mihoyo.com/event/luna/sign'

            headers = self.common_headers.copy()
            headers['DS'] = self._generate_ds_web()
            headers['Referer'] = 'https://act.mihoyo.com/'
            headers['Origin'] = 'https://act.mihoyo.com'
            headers['Cookie'] = cookie
            headers['x-rpc-device_id'] = device_id
            if config.get('signgame'):
                headers['x-rpc-signgame'] = config.get('signgame')

            try:
                info = requests.get(
                    info_url,
                    headers=headers,
                    params={'act_id': act_id, 'region': role.get('region'), 'uid': role.get('game_uid')},
                    timeout=10
                ).json()
                if info.get('retcode') != 0:
                    msg = info.get('message') or ""
                    if msg:
                        results.append(f"{role['nickname']}: 失败({info.get('retcode')}, {msg})")
                    else:
                        results.append(f"{role['nickname']}: 失败({info.get('retcode')})")
                    continue

                info_data = info.get('data') or {}
                if info_data.get('is_sign'):
                    results.append(f"{role['nickname']}: 已签")
                    continue
                if info_data.get('first_bind'):
                    results.append(f"{role['nickname']}: 请先手动签到一次")
                    continue

                sign = requests.post(
                    sign_url,
                    headers=headers,
                    json={'act_id': act_id, 'region': role.get('region'), 'uid': role.get('game_uid')},
                    timeout=10
                ).json()
                code = sign.get('retcode')
                msg = sign.get('message') or ""
                if code == 0 and (sign.get('data') or {}).get('success') == 0:
                    results.append(f"{role['nickname']}: 成功")
                elif code == -5003:
                    results.append(f"{role['nickname']}: 已签")
                else:
                    if msg:
                        results.append(f"{role['nickname']}: 失败({code}, {msg})")
                    else:
                        results.append(f"{role['nickname']}: 失败({code})")
            except Exception:
                results.append(f"{role['nickname']}: 错误")
                
        return "; ".join(results) if results else "无签到角色"

    def sign_in_miyoushe(self, cookie):
        """米游币签到"""
        if not cookie: return "无 Cookie"
        if "stoken=" not in cookie and "ltoken=" not in cookie:
            return "Cookie 不完整 (需 stoken)"
        
        device_id = str(uuid.uuid4()).replace('-', '')
        url = 'https://bbs-api.miyoushe.com/apihub/app/api/signIn'
        gids_list = [2]
        results = []
        
        headers = self.common_headers.copy()
        headers['Cookie'] = cookie
        headers['x-rpc-device_id'] = device_id
        headers['Referer'] = 'https://act.mihoyo.com/'
        headers['Origin'] = 'https://act.mihoyo.com'
        headers['Content-Type'] = 'application/json'

        for gid in gids_list:
            post_data = json.dumps({"gids": gid}, separators=(",", ":"))
            headers['DS'] = self._generate_ds2("", post_data)
            try:
                r = requests.post(url, headers=headers, data=post_data, timeout=10).json()
                ret = r.get('retcode')
                if ret == 0:
                    results.append("成功")
                elif ret == 1008:
                    results.append("已签")
                elif ret == -100:
                    results.append("Cookie 已过期")
                elif ret == 1034:
                    results.append("触发验证码 (需手动验证)")
                else:
                    msg = r.get('message') or ""
                    if msg:
                        results.append(f"失败({ret}, {msg})")
                    else:
                        results.append(f"失败({ret})")
            except Exception:
                results.append("错误")

        return "; ".join(results) if results else "失败"

    def _extract_cookie_value(self, cookie, keys):
        if not cookie:
            return ""
        for key in keys:
            # 使用更严谨的正则，防止 stoken 匹配到 stoken_v2
            m = re.search(rf"(?:^|;)\s*{re.escape(key)}=([^;]+)", cookie)
            if m:
                return m.group(1).strip()
        return ""

    def _apply_bbs_config(self, account_data):
        game_cookie = account_data.get('game_cookie') or account_data.get('cookie') or ""
        miyoushe_cookie = account_data.get('miyoushe_cookie') or account_data.get('cookie') or ""
        
        base = bbs_config.copy_config()
        # 游戏签到使用 game_cookie
        base["account"]["cookie"] = game_cookie
        
        # 优先从独立字段获取，如果没有则从 miyoushe_cookie 字符串提取
        stuid_val = account_data.get('stuid') or ""
        stuid = (self._extract_cookie_value(stuid_val, ["stuid", "account_id_v2", "ltuid_v2", "account_id", "ltuid", "login_uid"]) or stuid_val) \
                if stuid_val else self._extract_cookie_value(miyoushe_cookie, ["stuid", "account_id_v2", "ltuid_v2", "account_id", "ltuid", "login_uid"])
        
        stoken_val = account_data.get('stoken') or ""
        stoken = (self._extract_cookie_value(stoken_val, ["stoken_v2", "stoken", "stoken_v1"]) or stoken_val) \
                 if stoken_val else self._extract_cookie_value(miyoushe_cookie, ["stoken_v2", "stoken", "stoken_v1"])
        
        mid_val = account_data.get('mid') or ""
        mid = (self._extract_cookie_value(mid_val, ["mid_v2", "account_mid_v2", "mid", "ltmid_v2"]) or mid_val) \
              if mid_val else self._extract_cookie_value(miyoushe_cookie, ["mid_v2", "account_mid_v2", "mid", "ltmid_v2"])
        
        base["account"]["stuid"] = stuid
        base["account"]["stoken"] = stoken
        base["account"]["mid"] = mid
        # 米游社签到逻辑内部会使用 base["account"]["miyoushe_cookie"] 如果我们这样定义，
        # 但目前 MihoyoBBSTools 的 mihoyobbs.py 使用的是 config.config["account"]["cookie"]。
        # 为了让 mihoyobbs.py 使用正确的 cookie，我们需要在运行它之前切换 config。
        base["account"]["miyoushe_cookie"] = miyoushe_cookie 

        base["mihoyobbs"]["enable"] = account_data.get('enable_miyoushe', True)
        base["mihoyobbs"]["checkin"] = account_data.get('enable_miyoushe', True)
        base["mihoyobbs"]["read"] = account_data.get("enable_bbs_read", True)
        base["mihoyobbs"]["like"] = account_data.get("enable_bbs_like", True)
        base["mihoyobbs"]["share"] = account_data.get("enable_bbs_share", True)
        base["mihoyobbs"]["checkin_list"] = [5, 2]  # 默认签到大别野和原神版块

        base["games"]["cn"]["genshin"]["checkin"] = account_data.get('enable_genshin', True)
        base["games"]["cn"]["honkai_sr"]["checkin"] = account_data.get('enable_starrail', True)
        base["games"]["cn"]["zzz"]["checkin"] = account_data.get('enable_zzz', True)
        base["games"]["cn"]["enable"] = any([
            base["games"]["cn"]["genshin"]["checkin"],
            base["games"]["cn"]["honkai_sr"]["checkin"],
            base["games"]["cn"]["zzz"]["checkin"],
        ])

        if not base["device"]["id"]:
            base["device"]["id"] = str(uuid.uuid4()).replace('-', '')

        bbs_config.serverless = True
        bbs_config.config = base

    def _normalize_miyoushe_cookie_for_bbs(self, cookie: str) -> str:
        if not cookie:
            return ""
        from .account_manager import account_manager
        fields = account_manager.parse_cookie(cookie)
        stuid = fields.get("stuid") or ""
        mid = fields.get("mid") or ""
        stoken = fields.get("stoken_v2") or fields.get("stoken") or fields.get("stoken_v1") or ""
        cookie_token = fields.get("cookie_token") or fields.get("cookie_token_v2") or ""
        ltoken = fields.get("ltoken") or fields.get("ltoken_v2") or ""

        parts = []
        if stuid:
            parts.append(f"stuid={stuid}")
            parts.append(f"login_uid={stuid}")
            parts.append(f"account_id={stuid}")
            parts.append(f"ltuid={stuid}")
        if stoken:
            if stoken.startswith("v2_"):
                parts.append(f"stoken_v2={stoken}")
            else:
                parts.append(f"stoken={stoken}")
        if mid:
            if stoken.startswith("v2_"):
                parts.append(f"mid_v2={mid}")
            else:
                parts.append(f"mid={mid}")
        if cookie_token:
            parts.append(f"cookie_token={cookie_token}")
        if ltoken:
            parts.append(f"ltoken={ltoken}")

        return "; ".join(parts) if parts else cookie

    def _ensure_cookie_token_for_bbs(self, cookie: str) -> str:
        if not cookie:
            return ""
        if "cookie_token=" in cookie:
            return cookie
        try:
            stuid = (bbs_config.config.get("account") or {}).get("stuid") or ""
            stoken = (bbs_config.config.get("account") or {}).get("stoken") or ""
            if not stuid or not stoken:
                return cookie

            bbs_config.serverless = True
            from . import login as bbs_login
            cookie_token = bbs_login.get_cookie_token_by_stoken()
            cookie_token = (cookie_token or "").strip()
            if cookie_token:
                return f"{cookie}; cookie_token={cookie_token}"
        except Exception:
            pass
        finally:
            try:
                bbs_config.serverless = True
            except Exception:
                pass
        return cookie

    def sign_in_all(self, account_data):
        """对单个账号执行所有启用的签到"""
        game_cookie = account_data.get('game_cookie') or account_data.get('cookie') or ""
        miyoushe_cookie = account_data.get('miyoushe_cookie') or account_data.get('cookie') or ""
        enable_miyoushe = account_data.get('enable_miyoushe', True)
        
        if not game_cookie and not miyoushe_cookie:
            return ["Cookie 无效或为空"]

        if not game_cookie and miyoushe_cookie:
            from .account_manager import account_manager
            fields = account_manager.parse_cookie(miyoushe_cookie)
            if fields.get("ltoken") or fields.get("cookie_token"):
                game_cookie = miyoushe_cookie

        effective_account_data = dict(account_data or {})
        if game_cookie and not effective_account_data.get("game_cookie"):
            effective_account_data["game_cookie"] = game_cookie
        if miyoushe_cookie and not effective_account_data.get("miyoushe_cookie"):
            effective_account_data["miyoushe_cookie"] = miyoushe_cookie

        self._apply_bbs_config(effective_account_data)

        results = []
        # 1. 执行游戏签到 (使用 game_cookie，已在 _apply_bbs_config 中设置)
        try:
            game_result = bbs_gamecheckin.run_task()
            if game_result:
                results.append(f"游戏签到:\n{game_result.strip()}")
        except Exception as e:
            results.append(f"游戏签到: 失败({e})")

        # 2. 执行米游社签到 (使用 miyoushe_cookie)
        if enable_miyoushe:
            try:
                from .account_manager import account_manager
                fields = account_manager.parse_cookie(miyoushe_cookie)
                stoken = fields.get("stoken") or fields.get("stoken_v2") or fields.get("stoken_v1")
                if not stoken:
                    results.append("米游社: 跳过 (需 stoken)")
                    return results

                # 在执行米游社任务前，临时将 config 中的 cookie 设为 miyoushe_cookie
                # 因为 MihoyoBBSTools 的 Mihoyobbs 类初始化时会读取 config.config["account"]["cookie"]
                original_cookie = bbs_config.config["account"]["cookie"]
                bbs_cookie = self._normalize_miyoushe_cookie_for_bbs(miyoushe_cookie)
                bbs_cookie = self._ensure_cookie_token_for_bbs(bbs_cookie)
                bbs_config.config["account"]["cookie"] = bbs_cookie
                
                bbs = bbs_mihoyobbs.Mihoyobbs()
                results.append(bbs.run_task())
                
                # 恢复原状
                bbs_config.config["account"]["cookie"] = original_cookie
            except (bbs_error.StokenError, bbs_error.CookieError) as e:
                results.append(f"米游社: 失败({e})")
            except Exception as e:
                results.append(f"米游社: 失败({e})")

        return results

    def sign_in_item(self, account_data, item: str):
        game_cookie = account_data.get('game_cookie') or account_data.get('cookie') or ""
        miyoushe_cookie = account_data.get('miyoushe_cookie') or account_data.get('cookie') or ""

        if not game_cookie and not miyoushe_cookie:
            return ["Cookie 无效或为空"]

        if not game_cookie and miyoushe_cookie:
            from .account_manager import account_manager
            fields = account_manager.parse_cookie(miyoushe_cookie)
            if fields.get("ltoken") or fields.get("cookie_token"):
                game_cookie = miyoushe_cookie

        effective_account_data = dict(account_data or {})
        if game_cookie and not effective_account_data.get("game_cookie"):
            effective_account_data["game_cookie"] = game_cookie
        if miyoushe_cookie and not effective_account_data.get("miyoushe_cookie"):
            effective_account_data["miyoushe_cookie"] = miyoushe_cookie

        item = (item or "").strip().lower()
        item_labels = {"genshin": "原神", "starrail": "崩坏：星穹铁道", "zzz": "绝区零", "miyoushe": "米游社", "bbs": "米游社"}
        skip_reason = self._should_skip_item_today(account_data, item)
        if skip_reason == "captcha":
            return [f"{item_labels.get(item, item)}: 跳过 (今日触证码)"]
        if skip_reason == "done":
            return [f"{item_labels.get(item, item)}: 跳过 (今日已完成)"]

        if item in {"genshin", "starrail", "zzz"}:
            game_mid_map = {"genshin": "genshin", "starrail": "honkai_sr", "zzz": "zzz"}
            name_map = {"genshin": "原神", "starrail": "崩坏：星穹铁道", "zzz": "绝区零"}
            enabled_map = {
                "genshin": bool(account_data.get("enable_genshin", True)),
                "starrail": bool(account_data.get("enable_starrail", True)),
                "zzz": bool(account_data.get("enable_zzz", True)),
            }
            if not enabled_map.get(item, True):
                return [f"{name_map[item]}: 未启用"]
            if not game_cookie:
                return [f"{name_map[item]}: 失败 (Cookie 无效)"]

            per_item_data = dict(effective_account_data)
            per_item_data["enable_genshin"] = False
            per_item_data["enable_starrail"] = False
            per_item_data["enable_zzz"] = False
            if item == "genshin":
                per_item_data["enable_genshin"] = True
            elif item == "starrail":
                per_item_data["enable_starrail"] = True
            elif item == "zzz":
                per_item_data["enable_zzz"] = True

            self._apply_bbs_config(per_item_data)
            try:
                game_result = bbs_gamecheckin.run_task_selected([game_mid_map[item]])
                if game_result:
                    out = f"{name_map[item]}:\n{game_result.strip()}"
                    self._update_daily_state(account_data, item, self._classify_daily_status(out))
                    return [out]
                out = f"{name_map[item]}: 跳过 (无可签到角色)"
                self._update_daily_state(account_data, item, self._classify_daily_status(out))
                return [out]
            except Exception as e:
                return [f"{name_map[item]}: 失败({e})"]

        if item in {"miyoushe", "bbs"}:
            enable_miyoushe = bool(account_data.get('enable_miyoushe', True))
            if not enable_miyoushe:
                return ["米游社: 未启用"]
            try:
                from .account_manager import account_manager
                fields = account_manager.parse_cookie(miyoushe_cookie)
                stoken = fields.get("stoken") or fields.get("stoken_v2") or fields.get("stoken_v1")
                if not stoken:
                    return ["米游社: 跳过 (需 stoken)"]

                self._apply_bbs_config(effective_account_data)
                original_cookie = bbs_config.config["account"]["cookie"]
                bbs_cookie = self._normalize_miyoushe_cookie_for_bbs(miyoushe_cookie)
                bbs_cookie = self._ensure_cookie_token_for_bbs(bbs_cookie)
                bbs_config.config["account"]["cookie"] = bbs_cookie

                bbs = bbs_mihoyobbs.Mihoyobbs()
                out = bbs.run_task()
                bbs_config.config["account"]["cookie"] = original_cookie
                self._update_daily_state(account_data, "miyoushe", self._classify_daily_status(out))
                return [out]
            except (bbs_error.StokenError, bbs_error.CookieError) as e:
                return [f"米游社: 失败({e})"]
            except Exception as e:
                return [f"米游社: 失败({e})"]

        return [f"{item}: 跳过(未知任务)"]
    
    # 兼容旧代码，但尽量不使用
    def sign_in(self, cookie: str) -> bool:
        account_data = {"cookie": cookie, "enable_genshin": True, "enable_starrail": False, "enable_zzz": False, "enable_miyoushe": False}
        results = self.sign_in_all(account_data)
        return any("成功" in r or "已签" in r for r in results)

mihoyo_client = MihoyoClient()
