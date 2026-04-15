import ctypes
import ctypes.wintypes
import base64
import os
import platform
import hashlib

# Windows DPAPI structures
class DATA_BLOB(ctypes.Structure):
    _fields_ = [('cbData', ctypes.wintypes.DWORD),
                ('pbData', ctypes.POINTER(ctypes.c_char))]

def get_machine_fingerprint():
    """获取设备指纹信息：计算机名、处理器ID、机器GUID"""
    try:
        computer_name = platform.node()
        processor_id = platform.processor()
        
        # 尝试获取机器 GUID
        machine_guid = ""
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography")
            machine_guid, _ = winreg.QueryValueEx(key, "MachineGuid")
        except:
            pass
            
        fingerprint = f"{computer_name}|{processor_id}|{machine_guid}"
        return hashlib.sha256(fingerprint.encode()).digest()
    except:
        return b"default_fallback_salt_for_security"

def encrypt_cookie(text):
    """使用 Windows DPAPI 加密文本"""
    if not text:
        return ""
    
    try:
        # 1. 准备数据
        data = text.encode('utf-8')
        # 2. 结合设备指纹作为额外熵 (Entropy)
        entropy = get_machine_fingerprint()
        
        blob_in = DATA_BLOB(len(data), ctypes.create_string_buffer(data))
        blob_entropy = DATA_BLOB(len(entropy), ctypes.create_string_buffer(entropy))
        blob_out = DATA_BLOB()
        
        # 3. 调用 Windows DPAPI
        if ctypes.windll.crypt32.CryptProtectData(
            ctypes.byref(blob_in),
            u"CookieData",
            ctypes.byref(blob_entropy),
            None,
            None,
            0,
            ctypes.byref(blob_out)
        ):
            result = ctypes.string_at(blob_out.pbData, blob_out.cbData)
            ctypes.windll.kernel32.LocalFree(blob_out.pbData)
            # 返回 Base64 编码的密文
            return base64.b64encode(result).decode('utf-8')
    except Exception:
        pass
    return ""

def decrypt_cookie(encrypted_text):
    """使用 Windows DPAPI 解密文本"""
    if not encrypted_text:
        return ""
    
    try:
        # 1. Base64 解码
        data = base64.b64decode(encrypted_text)
        # 2. 准备指纹熵
        entropy = get_machine_fingerprint()
        
        blob_in = DATA_BLOB(len(data), ctypes.create_string_buffer(data))
        blob_entropy = DATA_BLOB(len(entropy), ctypes.create_string_buffer(entropy))
        blob_out = DATA_BLOB()
        
        # 3. 调用 Windows DPAPI
        if ctypes.windll.crypt32.CryptUnprotectData(
            ctypes.byref(blob_in),
            None,
            ctypes.byref(blob_entropy),
            None,
            None,
            0,
            ctypes.byref(blob_out)
        ):
            result = ctypes.string_at(blob_out.pbData, blob_out.cbData)
            ctypes.windll.kernel32.LocalFree(blob_out.pbData)
            return result.decode('utf-8')
    except Exception:
        # 如果解密失败（可能是明文或设备不匹配）
        pass
    return ""
