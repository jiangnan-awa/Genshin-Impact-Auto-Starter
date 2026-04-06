import os
import sys
import requests
import zipfile
import winreg
import platform
import subprocess
import re
from tqdm import tqdm

def get_chrome_version():
    """获取本地 Chrome 浏览器版本"""
    try:
        # 尝试从注册表获取
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Google\Chrome\BLBeacon")
        version, _ = winreg.QueryValueEx(key, "version")
        return version
    except:
        try:
            # 尝试从文件路径获取
            path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
            if not os.path.exists(path):
                path = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
            
            if os.path.exists(path):
                # 使用 powershell 获取版本
                cmd = f'(Get-Item "{path}").VersionInfo.FileVersion'
                version = subprocess.check_output(['powershell', '-Command', cmd]).decode().strip()
                return version
        except:
            pass
    return None

def get_edge_version():
    """获取本地 Edge 浏览器版本"""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Edge\BLBeacon")
        version, _ = winreg.QueryValueEx(key, "version")
        return version
    except:
        try:
            path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
            if os.path.exists(path):
                cmd = f'(Get-Item "{path}").VersionInfo.FileVersion'
                version = subprocess.check_output(['powershell', '-Command', cmd]).decode().strip()
                return version
        except:
            pass
    return None

import time

def get_base_path():
    """获取程序运行的基础目录"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def download_file(url, save_path, retries=3, status_callback=None):
    """带进度条的下载函数，增加重试机制并模拟浏览器请求头"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    
    for attempt in range(retries):
        try:
            msg = f"正在尝试下载驱动 (第 {attempt + 1}/{retries} 次)..."
            if status_callback:
                status_callback(msg)
                
            # 禁用 SSL 警告并设置 verify=False 以提高兼容性
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
            with requests.Session() as session:
                # 显式设置 verify=False 以解决打包后可能的证书路径问题
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
    """获取单个最可能的 Chrome 驱动下载链接（用于手动引导）"""
    major_version = version.split('.')[0]
    if int(major_version) >= 115:
        return f"https://storage.googleapis.com/chrome-for-testing-public/{version}/win64/chromedriver-win64.zip"
    return f"https://chromedriver.storage.googleapis.com/{version}/chromedriver_win32.zip"

def get_edge_download_url(version):
    """获取单个最可能的 Edge 驱动下载链接（用于手动引导）"""
    return f"https://msedgedriver.azureedge.net/{version}/edgedriver_win64.zip"

def get_chrome_download_urls(version):
    """获取 Chrome 驱动下载链接列表（按照尝试优先级排序）"""
    major_version = version.split('.')[0]
    urls = []
    
    if int(major_version) >= 115:
        # 1. 官方源 (针对极新版本，官方永远是最全的)
        urls.append(f"https://storage.googleapis.com/chrome-for-testing-public/{version}/win64/chromedriver-win64.zip")
        
        # 2. 尝试从官方 JSON API 获取 (如果具体版本号不对，尝试获取该大版本的最新小版本)
        try:
            api_url = "https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json"
            data = requests.get(api_url, timeout=5).json()
            # 检查 Stable, Beta, Dev, Canary
            for channel in ['stable', 'beta', 'dev', 'canary']:
                channel_data = data['channels'].get(channel.capitalize())
                if channel_data and channel_data['version'].startswith(major_version):
                    for download in channel_data['downloads'].get('chromedriver', []):
                        if download['platform'] == 'win64':
                            urls.append(download['url'])
                            # 同时构造对应的镜像站链接
                            mirror_url = download['url'].replace("https://storage.googleapis.com/chrome-for-testing-public/", "https://registry.npmmirror.com/-/binary/chrome-for-testing/")
                            urls.append(mirror_url)
        except:
            pass

        # 3. 国内镜像 (npmmirror) - 使用用户提供的正确路径结构
        # 尝试直接拼接（如果版本完全匹配）
        urls.append(f"https://registry.npmmirror.com/-/binary/chrome-for-testing/{version}/win64/chromedriver-win64.zip")
            
    else:
        # 旧版本逻辑 (114及以下)
        try:
            # 优先镜像 (旧版本镜像同步很稳定)
            mirror_api = f"https://registry.npmmirror.com/-/binary/chromedriver/LATEST_RELEASE_{major_version}"
            latest_version = requests.get(mirror_api, timeout=10).text.strip()
            urls.append(f"https://registry.npmmirror.com/-/binary/chromedriver/{latest_version}/chromedriver_win32.zip")
        except:
            pass
        
        # 官方备选
        urls.append(f"https://chromedriver.storage.googleapis.com/{version}/chromedriver_win32.zip")
            
    return urls

def download_chromedriver(version, status_callback=None):
    """根据版本下载 Chromedriver (多源尝试)"""
    if not version: return False
    urls = get_chrome_download_urls(version)
    if not urls: return False
    
    base_path = get_base_path()
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

def download_edgedriver(version, status_callback=None):
    """根据版本下载 Edgedriver (多源尝试)"""
    if not version: return False
    
    urls = [
        f"https://msedgedriver.azureedge.net/{version}/edgedriver_win64.zip",
        f"https://msedge.sf.dl.delivery.mp.microsoft.com/filestreamingservice/files/msedgedriver/{version}/edgedriver_win64.zip"
    ]
    
    base_path = get_base_path()
    for url in urls:
        if status_callback:
            status_callback(f"正在尝试下载 Edge 驱动 ({'官方' if 'azureedge' in url else '备份节点'})...")
        
        temp_zip = os.path.join(base_path, "edgedriver.zip")
        if download_file(url, temp_zip, status_callback=status_callback):
            try:
                if status_callback:
                    status_callback("下载完成，正在解压驱动...")
                with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
                    for file in zip_ref.namelist():
                        if file.endswith('msedgedriver.exe'):
                            target_path = os.path.join(base_path, "msedgedriver.exe")
                            with open(target_path, 'wb') as f:
                                f.write(zip_ref.read(file))
                            break
                os.remove(temp_zip)
                return True
            except Exception:
                if os.path.exists(temp_zip): os.remove(temp_zip)
    return False
                
def auto_setup_driver(browser_type, status_callback=None):
    """自动安装驱动的主入口"""
    if browser_type == 'chrome':
        version = get_chrome_version()
        return download_chromedriver(version, status_callback=status_callback)
    elif browser_type == 'edge':
        version = get_edge_version()
        return download_edgedriver(version, status_callback=status_callback)
    return False

if __name__ == "__main__":
    # 测试
    auto_setup_driver('chrome')
