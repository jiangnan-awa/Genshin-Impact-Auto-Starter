import sys


def get_new_session(**kwargs):
    try:
        import httpx

        http_client = httpx.Client(timeout=30, transport=httpx.HTTPTransport(retries=10), follow_redirects=True,
                                   **kwargs)
        import tools

        if tools.get_openssl_version() < 102:
            httpx.get()
    except (TypeError, ModuleNotFoundError) as e:
        import requests
        from requests.adapters import HTTPAdapter

        http_client = requests.Session()
        http_client.mount('http://', HTTPAdapter(max_retries=10))
        http_client.mount('https://', HTTPAdapter(max_retries=10))
    return http_client


def is_module_imported(module_name):
    return module_name in sys.modules


def get_new_session_use_proxy(http_proxy: str):
    if is_module_imported("httpx"):
        proxies = {
            "http://": f'http://{http_proxy}',
            "https://": f'http://{http_proxy}'
        }
        return get_new_session(proxies=proxies)
    else:
        session = get_new_session()
        session.proxies = {
            "http": f'http://{http_proxy}',
            "https": f'http://{http_proxy}'
        }
        return session


http = get_new_session()

