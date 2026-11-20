"""Asset storage: abstraksi backend S3-compatible + lokal.

Default: LocalStorageBackend di settings.ASSET_STORAGE_DIR.
S3Backend memakai httpx + AWS Signature V4 manual (stdlib hmac/hashlib)
— tanpa boto3. Kredensial S3 TIDAK pernah ditulis ke log.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import shutil
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Protocol

import httpx

from app.core.config import settings

# Root leg (opencode/) — path relatif di settings diselesaikan dari sini,
# bukan dari CWD proses (server bisa dijalankan dari mana saja).
_LEG_ROOT = Path(__file__).resolve().parents[3]


def resolve_storage_root(configured: Optional[str] = None) -> Path:
    """Selesaikan ASSET_STORAGE_DIR jadi path absolut."""
    raw = configured if configured is not None else settings.ASSET_STORAGE_DIR
    p = Path(raw).expanduser()
    if not p.is_absolute():
        p = _LEG_ROOT / p
    return p


def sanitize_key(key: str) -> str:
    """Normalisasi + validasi kunci storage.

    Tolak: path absolut, backslash, segmen '..' / '.', kunci kosong.
    Kembalikan kunci posix bersih (tanpa leading '/').
    """
    if not key or not key.strip():
        raise ValueError("storage key must not be empty")
    if "\\" in key:
        raise ValueError(f"invalid storage key (backslash): {key!r}")
    if key.startswith("/") or key.startswith("~"):
        raise ValueError(f"invalid storage key (absolute): {key!r}")
    parts = []
    for part in key.replace("\\", "/").split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            raise ValueError(f"invalid storage key (path traversal): {key!r}")
        parts.append(part)
    if not parts:
        raise ValueError("storage key must not be empty")
    return "/".join(parts)


class StorageBackend(Protocol):
    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str: ...
    def get(self, key: str) -> bytes: ...
    def delete(self, key: str) -> None: ...
    def exists(self, key: str) -> bool: ...
    def list(self, prefix: str = "") -> list[str]: ...
    def url(self, key: str) -> str: ...


class LocalStorageBackend:
    """Simpan file di disk lokal di bawah root yang dikonfigurasi."""

    def __init__(self, root: Optional[str | Path] = None):
        self.root = Path(root) if root is not None else resolve_storage_root()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        clean = sanitize_key(key)
        path = (self.root / clean).resolve()
        if not path.is_relative_to(self.root.resolve()):
            raise ValueError(f"invalid storage key (escapes root): {key!r}")
        return path

    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return sanitize_key(key)

    def get(self, key: str) -> bytes:
        path = self._path(key)
        if not path.is_file():
            raise FileNotFoundError(f"asset not found: {key!r}")
        return path.read_bytes()

    def delete(self, key: str) -> None:
        path = self._path(key)
        if path.is_file():
            path.unlink()

    def exists(self, key: str) -> bool:
        try:
            return self._path(key).is_file()
        except ValueError:
            return False

    def list(self, prefix: str = "") -> list[str]:
        prefix = sanitize_key(prefix) if prefix else ""
        out: list[str] = []
        base = self.root / prefix if prefix else self.root
        if not base.exists():
            return out
        for p in sorted(base.rglob("*")):
            if p.is_file():
                out.append(str(p.relative_to(self.root).as_posix()))
        return out

    def url(self, key: str) -> str:
        return sanitize_key(key)


def _hmac(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def _sign_v4(secret_key: str, region: str, service: str,
             method: str, url: str, headers: dict[str, str],
             payload_hash: str, amz_date: str, date_stamp: str) -> str:
    """Bangun header Authorization AWS Signature V4 (SigV4)."""
    parsed = urllib.parse.urlparse(url)
    canonical_uri = urllib.parse.quote(parsed.path or "/", safe="/~")
    canonical_qs = parsed.query  # sudah terurut oleh pemanggil bila perlu
    signed_headers = sorted(k.lower() for k in headers)
    canonical_headers = "".join(
        f"{k.lower()}:{headers[k].strip()}\n" for k in sorted(headers, key=str.lower)
    )
    signed_headers_str = ";".join(sorted(k.lower() for k in headers))
    canonical_request = "\n".join([
        method, canonical_uri, canonical_qs,
        canonical_headers, signed_headers_str, payload_hash,
    ])
    scope = f"{date_stamp}/{region}/{service}/aws4_request"
    string_to_sign = "\n".join([
        "AWS4-HMAC-SHA256", amz_date, scope,
        hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
    ])
    k_date = _hmac(("AWS4" + secret_key).encode("utf-8"), date_stamp)
    k_region = _hmac(k_date, region)
    k_service = _hmac(k_region, service)
    k_signing = _hmac(k_service, "aws4_request")
    signature = hmac.new(k_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
    access = headers.get("_access_key", "")
    return (
        f"AWS4-HMAC-SHA256 Credential={access}/{scope}, "
        f"SignedHeaders={signed_headers_str}, Signature={signature}"
    )


class S3Backend:
    """Backend S3-compatible via httpx + SigV4 manual (tanpa boto3).

    `transport` hanya untuk tes (mock httpx transport, tanpa network).
    """

    def __init__(self, endpoint: str = "", bucket: str = "",
                 access_key: str = "", secret_key: str = "",
                 region: str = "us-east-1", cdn_base_url: str = "",
                 transport: Optional[httpx.BaseTransport] = None):
        self.endpoint = (endpoint or "").rstrip("/")
        self.bucket = bucket
        self.access_key = access_key
        self.secret_key = secret_key
        self.region = region or "us-east-1"
        self.cdn_base_url = (cdn_base_url or "").rstrip("/")
        self._transport = transport

    def _require_config(self) -> None:
        missing = [n for n, v in (
            ("S3_ENDPOINT", self.endpoint), ("S3_BUCKET", self.bucket),
            ("S3_ACCESS_KEY", self.access_key), ("S3_SECRET_KEY", self.secret_key),
        ) if not v]
        if missing:
            raise ValueError(
                "S3 storage backend is not configured: missing "
                + ", ".join(missing)
                + " (set S3_ENDPOINT, S3_BUCKET, S3_ACCESS_KEY, S3_SECRET_KEY)"
            )

    def _object_url(self, key: str) -> str:
        clean = sanitize_key(key)
        return f"{self.endpoint}/{self.bucket}/{urllib.parse.quote(clean, safe='/')}"

    def url(self, key: str) -> str:
        clean = sanitize_key(key)
        if self.cdn_base_url:
            return f"{self.cdn_base_url}/{urllib.parse.quote(clean, safe='/')}"
        return self._object_url(clean)

    def _request(self, method: str, key: str = "", query: str = "",
                 data: bytes = b"", content_type: str = "application/octet-stream") -> httpx.Response:
        self._require_config()
        clean = sanitize_key(key) if key else ""
        url = self._object_url(clean) if clean else f"{self.endpoint}/{self.bucket}/"
        if query:
            url = f"{url}?{query}"
        parsed = urllib.parse.urlparse(url)
        host = parsed.netloc
        now = datetime.now(timezone.utc)
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        date_stamp = now.strftime("%Y%m%d")
        payload_hash = hashlib.sha256(data).hexdigest()
        headers = {
            "host": host,
            "x-amz-date": amz_date,
            "x-amz-content-sha256": payload_hash,
        }
        if method in ("PUT", "POST"):
            headers["content-type"] = content_type
            headers["content-length"] = str(len(data))
        headers["_access_key"] = self.access_key  # dipakai _sign_v4, dihapus sebelum kirim
        auth = _sign_v4(self.secret_key, self.region, "s3", method, url,
                        headers, payload_hash, amz_date, date_stamp)
        headers["Authorization"] = auth
        del headers["_access_key"]
        client_kwargs: dict = {"timeout": 120.0}
        if self._transport is not None:
            client_kwargs["transport"] = self._transport
        with httpx.Client(**client_kwargs) as client:
            return client.request(method, url, headers=headers, content=data)

    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        resp = self._request("PUT", key, data=data, content_type=content_type)
        if resp.status_code not in (200, 201, 204):
            raise RuntimeError(f"S3 PUT failed ({resp.status_code}): {resp.text[:300]}")
        return self.url(key)

    def get(self, key: str) -> bytes:
        resp = self._request("GET", key)
        if resp.status_code == 404:
            raise FileNotFoundError(f"asset not found: {key!r}")
        if resp.status_code != 200:
            raise RuntimeError(f"S3 GET failed ({resp.status_code}): {resp.text[:300]}")
        return resp.content

    def delete(self, key: str) -> None:
        resp = self._request("DELETE", key)
        if resp.status_code not in (200, 204):
            raise RuntimeError(f"S3 DELETE failed ({resp.status_code}): {resp.text[:300]}")

    def exists(self, key: str) -> bool:
        try:
            resp = self._request("HEAD", key)
        except ValueError:
            return False
        return resp.status_code == 200

    def list(self, prefix: str = "") -> list[str]:
        clean_prefix = sanitize_key(prefix) if prefix else ""
        query = "list-type=2" + (f"&prefix={urllib.parse.quote(clean_prefix, safe='')}" if clean_prefix else "")
        resp = self._request("GET", query=query)
        if resp.status_code != 200:
            raise RuntimeError(f"S3 LIST failed ({resp.status_code}): {resp.text[:300]}")
        root = ET.fromstring(resp.content)
        ns = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}
        keys = []
        for contents in root.findall("s3:Contents", ns) or root.findall("Contents"):
            key_el = contents.find("s3:Key", ns)
            if key_el is None:
                key_el = contents.find("Key")
            if key_el is not None and key_el.text:
                keys.append(key_el.text)
        return keys


def get_storage_backend(transport: Optional[httpx.BaseTransport] = None) -> StorageBackend:
    """Factory dari settings.STORAGE_BACKEND.

    "local" (default) -> LocalStorageBackend.
    "s3" tanpa kredensial -> ValueError jelas saat dipakai (bukan crash import).
    """
    backend = (settings.STORAGE_BACKEND or "local").lower()
    if backend == "local":
        return LocalStorageBackend()
    if backend == "s3":
        return S3Backend(
            endpoint=settings.S3_ENDPOINT,
            bucket=settings.S3_BUCKET,
            access_key=settings.S3_ACCESS_KEY,
            secret_key=settings.S3_SECRET_KEY,
            region=settings.S3_REGION or "us-east-1",
            cdn_base_url=settings.S3_CDN_BASE_URL,
            transport=transport,
        )
    raise ValueError(f"unknown STORAGE_BACKEND: {backend!r} (expected 'local' or 's3')")
