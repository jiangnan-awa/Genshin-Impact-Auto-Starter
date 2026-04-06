import json
import time
import httpx
import random
from string import ascii_letters, digits
from qrcode.main import QRCode
from qrcode.image.styledpil import StyledPilImage
from typing import Tuple, TypedDict, Literal
from io import StringIO
import logging
import uuid
import hashlib
from copy import deepcopy

APP_VERSION = "2.71.1"
DEVICE_NAME = "Xiaomi MI 6"
DEVICE_MODEL = "MI 6"
SALT_6X = "t0qEgfub6cvueAPgR5m9aQWWVciEer7v"

HEADERS_QRCODE_API = {
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

TOKEN_BY_GAME_TOKEN_URL = (
    "https://api-takumi.mihoyo.com/account/ma-cn-session/app/getTokenByGameToken"
)
CHECK_QR_URL = "https://hk4e-sdk.mihoyo.com/hk4e_cn/combo/panda/qrcode/query"
QR_URL = "https://hk4e-sdk.mihoyo.com/hk4e_cn/combo/panda/qrcode/fetch"

log = logging
log.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%S')


class PayloadRaw(TypedDict):
    uid: str
    """用户ID"""
    token: str
    """游戏Token"""


class PayLoad(TypedDict):
    proto: Literal["Account", "Raw"]
    raw: PayloadRaw
    ext: str


class CheckQRResult(TypedDict):
    stat: str
    """状态"""
    payload: PayLoad
    realname_info: dict


class StokenDataTokenResult(TypedDict):
    token_type: int
    """SToken类型"""
    token: str
    """SToken"""


class StokenDataUserInfoResult(TypedDict):
    aid: str
    """用户ID"""
    mid: str
    """用户代号"""


class StokenDataResult(TypedDict):
    token: StokenDataTokenResult
    user_info: StokenDataUserInfoResult
    realname_info: dict
    need_realperson: bool


class StokenResult(TypedDict):
    retcode: int
    message: str
    data: StokenDataResult


def get_ds2(query: str = "", body: str = "") -> str:
    """
    获取米游社的签名字符串，用于访问米游社API时的签名验证。

    :param query: 请求的查询参数
    :param body: 请求的主体内容
    :return: 返回一个字符串，格式为"时间戳,随机字符串,签名"。
    """
    n = SALT_6X
    i = str(int(time.time()))
    r = str(random.randint(100001, 200000))
    c = hashlib.md5(f'salt={n}&t={i}&r={r}&b={body}&q={query}'.encode()).hexdigest()
    return f"{i},{r},{c}"


def get_qr_url() -> Tuple[str, str, str, str]:
    """
    说明:
        获取二维码URL
    """
    app_id = "2"
    device = "".join(random.choices((ascii_letters + digits), k=64))
    _json = {
        "app_id": app_id,
        "device": device,
    }
    response = httpx.post(QR_URL, json=_json)
    result = response.json()
    data = result["data"]
    qr_url: str = data["url"]
    ticket = qr_url.split("ticket=")[1]
    return qr_url, app_id, ticket, device


def check_login(app_id: str, ticket: str, device: str):
    """
    说明:
        检查二维码登录状态
    参数:
        :param app_id: 来自`get_qr_url`的`_json`
        :param ticket: 来自`get_qr_url`
        :param device: 设备ID
    """
    # {'stat': 'Init', 'payload': {'proto': 'Raw', 'raw': '', 'ext': ''}, 'realname_info': None}
    # {'stat': 'Scanned', 'payload': {'proto': 'Raw', 'raw': '', 'ext': ''}, 'realname_info': None}
    # {'stat': 'Confirmed', 'payload': {'proto': 'Account', 'raw': '{"uid":"","token":""}', 'ext': ''}, 'realname_info': None}
    while True:
        _json = {"app_id": app_id, "ticket": ticket, "device": device}
        response = httpx.post(CHECK_QR_URL, json=_json)
        result = response.json()
        data: CheckQRResult = result["data"]
        # match python>=3.10
        if data["stat"] == "Init":
            log.info("等待扫码")
        elif data["stat"] == "Scanned":
            log.info("等待确认")
        elif data["stat"] == "Confirmed":
            log.info("登录成功")
            raw = json.loads(data["payload"]["raw"])
            game_token = raw["token"]
            uid = raw["uid"]
            return uid, game_token
        else:
            log.error("未知的状态")
            raise ValueError("未知的状态")
        time.sleep(1)


def show_qrcode(qr_url: str):
    """
    说明:
        显示二维码
    参数:
        :param qr_url: 二维码URL
    """
    qr = QRCode()
    qr.add_data(qr_url)
    image = qr.make_image()
    image.save("code.png")
    f = StringIO()
    qr.print_ascii(out=f)
    f.seek(0)
    print(f.read())


def get_stoken_by_game_token(uid: str, game_token: str):
    """
    说明:
        获取stoken
    参数:
        :param uid: 用户ID
        :param game_token: 游戏Token
    """
    headers = deepcopy(HEADERS_QRCODE_API)
    _json = {"account_id": int(uid), "game_token": game_token}
    headers["DS"] = get_ds2(body=json.dumps(_json))
    response = httpx.post(
        TOKEN_BY_GAME_TOKEN_URL,
        headers=headers,
        json=_json,
    )
    result: StokenResult = response.json()
    data = result["data"]
    mid = data["user_info"]["mid"]
    return mid, data["token"]["token"]


def main():
    qr_url, app_id, ticket, device = get_qr_url()
    show_qrcode(qr_url)
    uid, game_token = check_login(app_id, ticket, device)
    mid, stoken = get_stoken_by_game_token(uid, game_token)
    print(f"{uid=}, {mid=} ,{game_token=}, {stoken=}")


if __name__ == "__main__":
    main()
