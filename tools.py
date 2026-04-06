import hashlib
import random
import string
import time
import uuid

import setting


def md5(text: str) -> str:
    _md5 = hashlib.md5()
    _md5.update(text.encode())
    return _md5.hexdigest()


def random_text(num: int) -> str:
    return ''.join(random.sample(string.ascii_lowercase + string.digits, num))


def timestamp() -> int:
    return int(time.time())


def get_ds(web: bool) -> str:
    n = setting.mihoyobbs_salt
    if web:
        n = setting.mihoyobbs_salt_web
    i = str(timestamp())
    r = random_text(6)
    c = md5(f'salt={n}&t={i}&r={r}')
    return f"{i},{r},{c}"


def get_ds2(query: str = "", body: str = "") -> str:
    n = setting.mihoyobbs_salt_x6
    i = str(timestamp())
    r = str(random.randint(100001, 200000))
    c = md5(f'salt={n}&t={i}&r={r}&b={body}&q={query}')
    return f"{i},{r},{c}"


def get_device_id(cookie: str) -> str:
    return str(uuid.uuid3(uuid.NAMESPACE_URL, cookie))


def get_item(raw_data: dict) -> str:
    temp_name = raw_data["name"]
    temp_cnt = raw_data["cnt"]
    return f"「{temp_name}」x{temp_cnt}"


def get_next_day_timestamp() -> int:
    now_time = int(time.time())
    next_day_time = now_time - now_time % 86400 + time.timezone + 86400
    return next_day_time


def time_conversion(minute: int) -> str:
    h = minute // 60
    s = minute % 60
    return f"{h} 小时 {s} 分钟"


def tidy_cookie(cookies: str) -> str:
    cookie_dict = {}
    spilt_cookie = cookies.split(";")
    if len(spilt_cookie) < 2:
        return cookies
    for cookie in spilt_cookie:
        cookie = cookie.strip()
        if cookie == "":
            continue
        key, value = cookie.split("=", 1)
        cookie_dict[key] = value
    return "; ".join([f"{key}={value}" for key, value in cookie_dict.items()])


def get_useragent(useragent: str) -> str:
    if useragent == "":
        return setting.headers['User-Agent']
    if "miHoYoBBS" in useragent:
        i = useragent.index("miHoYoBBS")
        if useragent[i - 1] == " ":
            i = i - 1
        return f'{useragent[:i]} miHoYoBBS/{setting.mihoyobbs_version}'
    return f'{useragent} miHoYoBBS/{setting.mihoyobbs_version}'


def get_openssl_version() -> int:
    try:
        import ssl
    except ImportError:
        raise ImportError("Openssl Lib Error !!")
    temp_list = ssl.OPENSSL_VERSION_INFO
    return int(f"{str(temp_list[0])}{str(temp_list[1])}{str(temp_list[2])}")

