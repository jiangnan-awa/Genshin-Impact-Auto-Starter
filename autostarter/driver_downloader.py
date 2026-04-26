import os
import requests
import zipfile
import subprocess
import re
from .config_paths import detect_base_path
try:
    import winreg  # type: ignore
except ModuleNotFoundError:
    winreg = None  # type: ignore
try:
    from tqdm import tqdm  # type: ignore
except ModuleNotFoundError:
    tqdm = None  # type: ignore
def get_chrome_version():
    try:
        if winreg is not None:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Google\Chrome\BLBeacon")
            version, _ = winreg.QueryValueEx(key, "version")
            return version
    except:
        try:
            path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
            if not os.path.exists(path):
                path = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
            if os.path.exists(path):
                cmd = f'(Get-Item "{path}").VersionInfo.FileVersion'
                version = subprocess.check_output(['powershell', '-Command', cmd]).decode().strip()
                return version
        except:
            pass
    return None
import time
def download_file(url, save_path, retries=3, status_callback=None):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    for attempt in range(retries):
        try:
            msg = f"正在尝试下载驱动 (第 {attempt + 1}/{retries} 次)..."
            if status_callback:
                status_callback(msg)
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            with requests.Session() as session:
                response = session.get(url, stream=True, timeout=(15, 60), headers=headers, verify=False)
                if response.status_code == 404:
                    return False
                response.raise_for_status()
                total_size = int(response.headers.get('content-length', 0))
                with open(save_path, 'wb') as f:
                    for data in response.iter_content(chunk_size=16384):
                        if data:
                            f.write(data)
            if total_size > 0 and os.path.getsize(save_path) < total_size:
                raise Exception("文件下载不完整")
            return True
        except Exception:
            if os.path.exists(save_path):
                try:
                    os.remove(save_path)
                except:
                    pass
            if attempt < retries - 1:
                time.sleep((attempt + 1) * 2)
    return False
def get_chrome_download_url(version):
    major_version = version.split('.')[0]
    if int(major_version) >= 115:
        return f"https://storage.googleapis.com/chrome-for-testing-public/{version}/win64/chromedriver-win64.zip"
    return f"https://chromedriver.storage.googleapis.com/{version}/chromedriver_win32.zip"
def get_chrome_download_urls(version):
    major_version = version.split('.')[0]
    urls = []
    if int(major_version) >= 115:
        urls.append(f"https://storage.googleapis.com/chrome-for-testing-public/{version}/win64/chromedriver-win64.zip")
        try:
            api_url = "https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json"
            data = requests.get(api_url, timeout=5).json()
            for channel in ['stable', 'beta', 'dev', 'canary']:
                channel_data = data['channels'].get(channel.capitalize())
                if channel_data and channel_data['version'].startswith(major_version):
                    for download in channel_data['downloads'].get('chromedriver', []):
                        if download['platform'] == 'win64':
                            urls.append(download['url'])
                            mirror_url = download['url'].replace("https://storage.googleapis.com/chrome-for-testing-public/", "https://registry.npmmirror.com/-/binary/chrome-for-testing/")
                            urls.append(mirror_url)
        except:
            pass
        urls.append(f"https://registry.npmmirror.com/-/binary/chrome-for-testing/{version}/win64/chromedriver-win64.zip")
    else:
        try:
            mirror_api = f"https://registry.npmmirror.com/-/binary/chromedriver/LATEST_RELEASE_{major_version}"
            latest_version = requests.get(mirror_api, timeout=10).text.strip()
            urls.append(f"https://registry.npmmirror.com/-/binary/chromedriver/{latest_version}/chromedriver_win32.zip")
        except:
            pass
        urls.append(f"https://chromedriver.storage.googleapis.com/{version}/chromedriver_win32.zip")
    return urls
def download_chromedriver(version, status_callback=None):
    if not version: return False
    urls = get_chrome_download_urls(version)
    if not urls: return False
    base_path = detect_base_path()
    for url in urls:
        source_name = "镜像站" if "npmmirror" in url else "官方站"
        msg = f"检测到 Chrome {version}\n正在尝试从 {source_name} 下载..."
        if status_callback:
            status_callback(msg)
        temp_zip = os.path.join(base_path, "chromedriver.zip")
        if download_file(url, temp_zip, status_callback=lambda m: status_callback(f"{msg}\n{m}") if status_callback else None):
            try:
                if status_callback:
                    status_callback("下载完成，正在解压驱动...")
                with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
                    for file in zip_ref.namelist():
                        if file.endswith('chromedriver.exe'):
                            target_path = os.path.join(base_path, "chromedriver.exe")
                            with open(target_path, 'wb') as f:
                                f.write(zip_ref.read(file))
                            break
                os.remove(temp_zip)
                return True
            except Exception:
                if os.path.exists(temp_zip): os.remove(temp_zip)
    return False
def auto_setup_driver(browser_type, status_callback=None):
    if browser_type == 'chrome':
        version = get_chrome_version()
        return download_chromedriver(version, status_callback=status_callback)
    return False
if __name__ == "__main__":
    auto_setup_driver('chrome')
