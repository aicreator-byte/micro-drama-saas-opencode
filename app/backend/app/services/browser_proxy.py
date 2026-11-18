"""Local CONNECT relay proxy (stdlib only).

Why this exists (verified 2026-11-17 on this VM): Chromium/Playwright
talking DIRECTLY to the VM egress proxy fails every HTTPS navigation
with ``net::ERR_TUNNEL_CONNECTION_FAILED`` — curl to the same proxy and
the same targets works, and Chromium's CONNECT bytes are well-formed.
The difference is in what Chromium sends on CONNECT (browser
User-Agent, ...); a minimal curl-style CONNECT issued by this relay is
accepted by the egress proxy, and Chromium through the relay loads
https://example.com (200) and https://accounts.google.com (200,
sign-in page, email field present).

The relay listens on 127.0.0.1 only, accepts CONNECT from the local
browser, re-issues a curl-style CONNECT to the upstream proxy taken
from the environment (``HTTPS_PROXY``/``HTTP_PROXY``; no upstream means
a direct connection), then pipes bytes both ways. It never logs the
upstream credentials, request bodies, or response bodies — only the
CONNECT target host:port at debug level.
"""
import base64
import logging
import socket
import threading
from typing import Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def upstream_proxy_from_env() -> Optional[Tuple[str, int, Optional[str]]]:
    """Return ``(host, port, basic_auth_header)`` for the env proxy.

    Reads ``HTTPS_PROXY`` (then ``HTTP_PROXY``). Returns None when no
    proxy is configured — the relay then connects directly. The auth
    header is built at runtime from the environment and never stored.
    """
    import os
    raw = os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY") or ""
    if not raw:
        return None
    parsed = urlparse(raw)
    if not parsed.hostname or not parsed.port:
        return None
    auth = None
    if parsed.username:
        token = f"{parsed.username}:{parsed.password or ''}".encode()
        auth = "Basic " + base64.b64encode(token).decode()
    return parsed.hostname, parsed.port, auth


class ConnectRelay:
    """A minimal CONNECT-only forward proxy on localhost.

    Usage::

        relay = ConnectRelay()
        port = relay.start()          # OS-assigned 127.0.0.1 port
        # ... point the browser at http://127.0.0.1:<port> ...
        relay.stop()
    """

    def __init__(self, upstream: Optional[Tuple[str, int, Optional[str]]] = None):
        # None means "read the env proxy now"; pass () to force direct.
        self._upstream = upstream_proxy_from_env() if upstream is None else upstream
        self._server: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self.port: Optional[int] = None

    @property
    def proxy_url(self) -> Optional[str]:
        if self.port is None:
            return None
        return f"http://127.0.0.1:{self.port}"

    def start(self) -> int:
        if self._server is not None:
            return self.port  # type: ignore[return-value]
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("127.0.0.1", 0))
        server.listen(16)
        self._server = server
        self.port = server.getsockname()[1]
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()
        logger.info("CONNECT relay listening on 127.0.0.1:%s", self.port)
        return self.port

    def stop(self) -> None:
        server, self._server = self._server, None
        if server is not None:
            try:
                server.close()
            except OSError:
                pass
        self.port = None

    def _serve(self) -> None:
        assert self._server is not None
        while self._server is not None:
            try:
                client, _ = self._server.accept()
            except OSError:
                return
            threading.Thread(target=self._handle, args=(client,),
                             daemon=True).start()

    def _handle(self, client: socket.socket) -> None:
        upstream_sock: Optional[socket.socket] = None
        try:
            request = b""
            client.settimeout(30)
            while b"\r\n\r\n" not in request:
                chunk = client.recv(4096)
                if not chunk:
                    return
                request += chunk
            try:
                line = request.split(b"\r\n", 1)[0].decode("ascii")
                method, target, _version = line.split(" ", 2)
            except ValueError:
                return
            if method.upper() != "CONNECT":
                client.sendall(b"HTTP/1.1 405 Method Not Allowed\r\n\r\n")
                return
            logger.debug("CONNECT relay: %s", target)
            upstream_sock = self._connect_upstream(target)
            if upstream_sock is None:
                client.sendall(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
                return
            client.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
            self._pipe(client, upstream_sock)
        except OSError as exc:
            logger.debug("CONNECT relay connection closed: %s", exc)
        finally:
            for sock in (client, upstream_sock):
                if sock is not None:
                    try:
                        sock.close()
                    except OSError:
                        pass

    def _connect_upstream(self, target: str) -> Optional[socket.socket]:
        """Open a tunnel to ``target`` (host:port), via env proxy if set."""
        try:
            if self._upstream is None:
                host, port = target.rsplit(":", 1)
                sock = socket.create_connection((host, int(port)), timeout=30)
                return sock
            proxy_host, proxy_port, auth = self._upstream
            sock = socket.create_connection((proxy_host, proxy_port), timeout=30)
            headers = (
                f"CONNECT {target} HTTP/1.1\r\n"
                f"Host: {target}\r\n"
                "Proxy-Connection: Keep-Alive\r\n"
            )
            if auth:
                headers += f"Proxy-Authorization: {auth}\r\n"
            headers += "\r\n"
            sock.sendall(headers.encode("ascii"))
            response = b""
            sock.settimeout(30)
            while b"\r\n\r\n" not in response:
                chunk = sock.recv(4096)
                if not chunk:
                    sock.close()
                    return None
                response += chunk
            status_line = response.split(b"\r\n", 1)[0].decode("ascii", "replace")
            if " 200" not in status_line:
                logger.debug("CONNECT relay: upstream refused (%s)", status_line)
                sock.close()
                return None
            return sock
        except (OSError, ValueError) as exc:
            logger.debug("CONNECT relay: cannot reach %s: %s", target, exc)
            return None

    @staticmethod
    def _pipe(a: socket.socket, b: socket.socket) -> None:
        def _forward(src: socket.socket, dst: socket.socket) -> None:
            try:
                while True:
                    data = src.recv(65536)
                    if not data:
                        break
                    dst.sendall(data)
            except OSError:
                pass
            finally:
                try:
                    dst.shutdown(socket.SHUT_WR)
                except OSError:
                    pass

        t1 = threading.Thread(target=_forward, args=(a, b), daemon=True)
        t2 = threading.Thread(target=_forward, args=(b, a), daemon=True)
        t1.start()
        t2.start()
        t1.join()
        t2.join()


# Module-level singleton: one relay per process is enough (the browser
# service starts it lazily on first use).
_relay: Optional[ConnectRelay] = None


def get_relay() -> ConnectRelay:
    """Return the process relay, starting it on first use."""
    global _relay
    if _relay is None:
        _relay = ConnectRelay()
        _relay.start()
    return _relay


if __name__ == "__main__":  # standalone: python -m app.services.browser_proxy [port]
    import sys
    import time

    relay = ConnectRelay()
    port = relay.start()
    print(f"CONNECT relay on 127.0.0.1:{port} (upstream from HTTPS_PROXY env)")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        relay.stop()
