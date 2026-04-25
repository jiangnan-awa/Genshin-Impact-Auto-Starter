from __future__ import annotations
import base64
import json
import os
import sys
from typing import Any, Optional
from . import config_paths
class SecretStoreBase:
    backend_name = "base"
    def is_available(self) -> bool:  # pragma: no cover
        return False
    def save(self, ref: str, payload: dict[str, Any]) -> None:  # pragma: no cover
        raise NotImplementedError
    def load(self, ref: str) -> dict[str, Any]:  # pragma: no cover
        raise NotImplementedError
class DpapiFileStore(SecretStoreBase):
    backend_name = "dpapi"
    def __init__(self, base_path: Optional[str] = None):
        self._base_path = base_path
        self._win32crypt = None
        try:
            import win32crypt  # type: ignore
            self._win32crypt = win32crypt
        except Exception:
            self._win32crypt = None
        try:
            from .security import encrypt_cookie as _enc, decrypt_cookie as _dec
            self._fallback_encrypt = _enc
            self._fallback_decrypt = _dec
        except Exception:
            self._fallback_encrypt = None
            self._fallback_decrypt = None
    def is_available(self) -> bool:
        if sys.platform != "win32":
            return False
        if self._win32crypt is not None:
            return True
        return bool(self._fallback_encrypt is not None and self._fallback_decrypt is not None)
    def _file_path(self) -> str:
        paths = config_paths.get_config_paths(self._base_path)
        return os.path.join(paths.config_dir, "secret_store_dpapi.json")
    def _load_map(self) -> dict[str, str]:
        p = self._file_path()
        if not os.path.exists(p):
            return {}
        try:
            with open(p, "r", encoding="utf-8") as f:
                obj = json.load(f)
            return obj if isinstance(obj, dict) else {}
        except Exception:
            return {}
    def _save_map(self, m: dict[str, str]) -> None:
        p = self._file_path()
        os.makedirs(os.path.dirname(p), exist_ok=True)
        tmp = p + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(m, f, ensure_ascii=False, indent=2)
        os.replace(tmp, p)
    def save(self, ref: str, payload: dict[str, Any]) -> None:
        if not self.is_available():
            raise RuntimeError("DPAPI 不可用")
        raw = json.dumps(payload or {}, ensure_ascii=False).encode("utf-8")
        if self._win32crypt is not None:
            protected = self._win32crypt.CryptProtectData(raw, None, None, None, None, 0)
            if isinstance(protected, tuple) and len(protected) >= 2:
                protected_bytes = protected[1]
            else:
                protected_bytes = protected
            b64 = base64.b64encode(bytes(protected_bytes)).decode("ascii")
        else:
            b64 = str(self._fallback_encrypt(raw.decode("utf-8")) or "")
            if not b64:
                raise RuntimeError("DPAPI 加密失败")
        m = self._load_map()
        m[str(ref)] = b64
        self._save_map(m)
    def load(self, ref: str) -> dict[str, Any]:
        if not self.is_available():
            return {}
        m = self._load_map()
        b64 = m.get(str(ref))
        if not b64:
            return {}
        try:
            if self._win32crypt is not None:
                protected = base64.b64decode(b64)
                unprotected = self._win32crypt.CryptUnprotectData(protected, None, None, None, 0)
                if isinstance(unprotected, tuple) and len(unprotected) >= 2:
                    raw = unprotected[1]
                else:
                    raw = unprotected
                decoded = bytes(raw).decode("utf-8")
            else:
                decoded = str(self._fallback_decrypt(b64) or "")
                if not decoded:
                    return {}
            obj = json.loads(decoded)
            return obj if isinstance(obj, dict) else {}
        except Exception:
            return {}
class UnsupportedStore(SecretStoreBase):
    backend_name = "unsupported"
    def __init__(self, message: str):
        self._message = message
    def is_available(self) -> bool:
        return False
    def save(self, ref: str, payload: dict[str, Any]) -> None:  # pragma: no cover
        _ = (ref, payload)
        raise RuntimeError(self._message)
    def load(self, ref: str) -> dict[str, Any]:  # pragma: no cover
        _ = ref
        raise RuntimeError(self._message)
def select_default_store(
    *,
    base_path: Optional[str] = None,
    dpapi: Optional[Any] = None,
    platform: Optional[str] = None,
) -> Any:
    plat = platform or sys.platform
    if dpapi is None:
        dpapi = DpapiFileStore(base_path=base_path)
    if str(plat) == "win32":
        if hasattr(dpapi, "is_available") and dpapi.is_available():
            return dpapi
        return UnsupportedStore("DPAPI 不可用，无法安全保存账号敏感信息")
    return UnsupportedStore("当前版本仅支持 Windows")
