import json
import time
import uuid
import random
import hashlib
from copy import deepcopy
from io import StringIO
from string import ascii_letters, digits
from typing import Callable, Optional, Tuple


APP_VERSION = "2.71.1"
DEVICE_NAME = "Xiaomi MI 6"
DEVICE_MODEL = "MI 6"
SALT_6X = "t0qEgfub6cvueAPgR5m9aQWWVciEer7v"

TOKEN_BY_GAME_TOKEN_URL = "https://api-takumi.mihoyo.com/account/ma-cn-session/app/getTokenByGameToken"
CHECK_QR_URL = "https://hk4e-sdk.mihoyo.com/hk4e_cn/combo/panda/qrcode/query"
QR_URL = "https://hk4e-sdk.mihoyo.com/hk4e_cn/combo/panda/qrcode/fetch"


def _get_ds2(query: str = "", body: str = "") -> str:
    t = str(int(time.time()))
    r = str(random.randint(100001, 200000))
    c = hashlib.md5(f"salt={SALT_6X}&t={t}&r={r}&b={body}&q={query}".encode()).hexdigest()
    return f"{t},{r},{c}"


def create_qr_session(timeout: float = 10.0) -> Tuple[str, str, str, str]:
    import httpx

    app_id = "2"
    device = "".join(random.choices((ascii_letters + digits), k=64))
    payload = {"app_id": app_id, "device": device}
    with httpx.Client(timeout=timeout) as client:
        resp = client.post(QR_URL, json=payload)
        resp.raise_for_status()
        data = resp.json()["data"]
    qr_url: str = data["url"]
    ticket = qr_url.split("ticket=", 1)[1]
    return qr_url, app_id, ticket, device


def build_qr_image_and_ascii(qr_url: str):
    from qrcode.main import QRCode

    qr = QRCode()
    qr.add_data(qr_url)
    image = qr.make_image()
    buf = StringIO()
    qr.print_ascii(out=buf)
    buf.seek(0)
    return image, buf.read()


def poll_qr_login(
    app_id: str,
    ticket: str,
    device: str,
    timeout_seconds: int = 180,
    status_callback: Optional[Callable[[str], None]] = None,
) -> Tuple[str, str]:
    import httpx

    deadline = time.time() + max(1, int(timeout_seconds))
    with httpx.Client(timeout=10.0) as client:
        while True:
            if time.time() > deadline:
                raise TimeoutError("扫码超时，请重试")
            payload = {"app_id": app_id, "ticket": ticket, "device": device}
            resp = client.post(CHECK_QR_URL, json=payload)
            resp.raise_for_status()
            data = resp.json()["data"]
            stat = data.get("stat")
            if stat == "Init":
                if status_callback:
                    status_callback("等待扫码")
            elif stat == "Scanned":
                if status_callback:
                    status_callback("等待确认")
            elif stat == "Confirmed":
                if status_callback:
                    status_callback("登录成功，正在获取 stoken")
                raw = data["payload"]["raw"]
                if isinstance(raw, str):
                    raw = json.loads(raw)
                return str(raw["uid"]), str(raw["token"])
            else:
                raise RuntimeError(f"未知状态: {stat}")
            time.sleep(1)


def get_stoken_by_game_token(uid: str, game_token: str, timeout: float = 10.0) -> Tuple[str, str]:
    import httpx

    headers = {
        "x-rpc-app_version": APP_VERSION,
        "DS": None,
        "x-rpc-aigis": "",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "x-rpc-game_biz": "bbs_cn",
        "x-rpc-sys_version": "12",
        "x-rpc-device_id": uuid.uuid4().hex,
        "x-rpc-device_name": DEVICE_NAME,
        "x-rpc-device_model": DEVICE_MODEL,
        "x-rpc-app_id": "bll8iq97cem8",
        "x-rpc-client_type": "4",
        "User-Agent": "okhttp/4.9.3",
    }
    payload = {"account_id": int(uid), "game_token": game_token}
    headers["DS"] = _get_ds2(body=json.dumps(payload, separators=(",", ":")))
    with httpx.Client(timeout=timeout) as client:
        resp = client.post(TOKEN_BY_GAME_TOKEN_URL, headers=deepcopy(headers), json=payload)
        resp.raise_for_status()
        data = resp.json()["data"]
    mid = str(data["user_info"]["mid"])
    stoken = str(data["token"]["token"])
    return mid, stoken


def build_miyoushe_cookie(uid: str, mid: str, stoken: str) -> str:
    uid = str(uid).strip()
    mid = str(mid).strip()
    stoken = str(stoken).strip()
    uid_fields = f"stuid={uid}; login_uid={uid}; account_id={uid}; ltuid={uid}"
    if stoken.startswith("v2_"):
        return f"{uid_fields}; stoken_v2={stoken}; mid_v2={mid}"
    return f"{uid_fields}; stoken={stoken}; mid={mid}"
