"""Trusted-local-HTTPS browser smoke test for the current PC web UI.

This is intentionally a standalone test: it starts an isolated FastAPI app and
Vite dev server, uses the in-memory test mail sink, and never bypasses HTTPS
certificate validation in the temporary browser profile.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from threading import Thread
from uuid import uuid4

import pyotp
import uvicorn
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from server.app.config import Settings
from server.app.main import create_app


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_for_port(port: int, timeout: float = 15.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket() as sock:
            sock.settimeout(0.2)
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(0.1)
    raise RuntimeError(f"loopback port did not open: {port}")


def run(command: list[str], *, cwd: Path | None = None) -> None:
    subprocess.run(command, cwd=cwd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def make_certificates(work: Path) -> tuple[Path, Path, Path]:
    ca_key = work / "ca.key"
    ca_cert = work / "ca.crt"
    server_key = work / "server.key"
    csr = work / "server.csr"
    server_cert = work / "server.crt"
    ext = work / "server.ext"
    run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", str(ca_key), "-out", str(ca_cert), "-days", "1", "-subj", "/CN=SCOPE01 isolated test CA", "-addext", "basicConstraints=critical,CA:TRUE", "-addext", "keyUsage=critical,keyCertSign,cRLSign"])
    run(["openssl", "req", "-newkey", "rsa:2048", "-nodes", "-keyout", str(server_key), "-out", str(csr), "-subj", "/CN=localhost"])
    ext.write_text("subjectAltName=DNS:localhost,IP:127.0.0.1\nextendedKeyUsage=serverAuth\n", encoding="utf-8")
    run(["openssl", "x509", "-req", "-in", str(csr), "-CA", str(ca_cert), "-CAkey", str(ca_key), "-CAcreateserial", "-out", str(server_cert), "-days", "1", "-sha256", "-extfile", str(ext)])
    return ca_cert, server_cert, server_key


def trust_ca(certutil: str, profile: Path, ca_cert: Path) -> None:
    run([certutil, "-N", "-d", f"sql:{profile}", "--empty-password"])
    run([certutil, "-A", "-d", f"sql:{profile}", "-n", "SCOPE01 isolated test CA", "-t", "C,,", "-a", "-i", str(ca_cert)])


def main() -> int:
    certutil = os.environ.get("SCOPE01_CERTUTIL")
    chrome = os.environ.get("SCOPE01_CHROME", "/usr/bin/google-chrome")
    if not certutil or not Path(certutil).is_file():
        print("BLOCKED: SCOPE01_CERTUTIL must point to a temporary certutil binary; no certificate bypass was used")
        return 2
    if not Path(chrome).is_file():
        print("BLOCKED: SCOPE01_CHROME is unavailable")
        return 2

    work = Path(tempfile.mkdtemp(prefix="scope01-browser-e2e-"))
    screenshot = work / "scope01-authenticated-dashboard.png"
    api_port = free_port()
    ui_port = free_port()
    database = work / "scope01.sqlite3"
    profile = work / "chrome-profile"
    profile.mkdir()
    ca_cert, server_cert, server_key = make_certificates(work)
    test_home = work / "home"
    nss_db = test_home / ".pki" / "nssdb"
    nss_db.mkdir(parents=True)
    trust_ca(certutil, nss_db, ca_cert)

    origin = f"https://localhost:{ui_port}"
    settings = Settings(
        app_env="test",
        database_url=f"sqlite:///{database}",
        session_secret=__import__("secrets").token_urlsafe(32),
        cookie_secure=True,
        allowed_origins=(origin,),
        host="127.0.0.1",
        port=api_port,
        enable_test_adapters=True,
    )
    application = create_app(settings, initialize_schema=True)
    api_server = uvicorn.Server(uvicorn.Config(application, host="127.0.0.1", port=api_port, log_level="error"))
    api_thread = Thread(target=api_server.run, daemon=True)
    api_thread.start()
    vite_env = os.environ.copy()
    vite_env.update({"VITE_HTTPS_CERT": str(server_cert), "VITE_HTTPS_KEY": str(server_key), "VITE_API_PROXY_TARGET": f"http://127.0.0.1:{api_port}"})
    vite = subprocess.Popen(["npm", "--prefix", "frontend", "run", "dev", "--", "--host", "127.0.0.1", "--port", str(ui_port)], cwd=ROOT, env=vite_env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        wait_for_port(api_port)
        wait_for_port(ui_port)
        with sync_playwright() as playwright:
            context = playwright.chromium.launch_persistent_context(profile, headless=True, executable_path=chrome, args=["--no-sandbox"], env={**os.environ, "HOME": str(test_home), "XDG_CONFIG_HOME": str(test_home / ".config")})
            page = context.new_page()
            page.goto(origin, wait_until="networkidle")
            assert "PUBLIC READ ONLY" in page.locator("body").inner_text()
            assert page.evaluate("async () => (await fetch('/api/v1/internal/zones')).status") == 401

            email = f"scope01-browser-{uuid4().hex[:10]}@sample.com"
            password = "BrowserPassword-12345"
            page.get_by_role("button", name="Đăng nhập / Đăng ký").click()
            page.get_by_role("button", name="Tạo tài khoản mới").click()
            page.get_by_label("Họ tên").fill("Browser Test User")
            page.get_by_label("Email").fill(email)
            page.get_by_label("Mật khẩu").fill(password)
            page.get_by_label("Nhập lại mật khẩu").fill(password)
            page.get_by_role("checkbox", name="Tôi đã đọc và đồng ý với điều khoản sử dụng.").check()
            page.get_by_role("button", name="Tạo tài khoản").click()
            code_input = page.locator('input[inputmode="numeric"]')
            code_input.wait_for()
            verification = application.state.fake_mail.latest(email, "VERIFY_EMAIL")
            assert verification is not None
            code_input.fill(verification.code)
            page.get_by_role("button", name="Xác nhận").click()
            page.get_by_label("Mã 2FA").wait_for()
            secret = page.locator(".secret-warning code").first.inner_text()
            page.get_by_label("Mã 2FA").fill(pyotp.TOTP(secret).now())
            page.get_by_role("button", name="Xác nhận").click()
            page.get_by_role("button", name="Tiếp tục vào hệ thống").click()
            page.get_by_role("heading", name="Tài khoản đang chờ duyệt").wait_for()
            assert "Tài khoản đang chờ duyệt" in page.locator("body").inner_text()
            cookies = context.cookies()
            session_cookie = next(cookie for cookie in cookies if cookie["name"] == "session")
            assert session_cookie["secure"] is True and session_cookie["httpOnly"] is True and session_cookie["sameSite"].lower() == "lax"
            assert page.evaluate("document.cookie.includes('session=')") is False
            assert page.evaluate("localStorage.length") == 0
            assert page.evaluate("async () => (await fetch('/api/v1/auth/logout', {method: 'POST'})).status") == 403
            page.screenshot(path=screenshot, full_page=True)
            page.get_by_role("button", name="Đăng xuất").first.click()

            page.get_by_role("button", name="Đăng nhập / Đăng ký").click()
            page.get_by_label("Email").fill(email)
            page.get_by_label("Mật khẩu").fill(password)
            page.get_by_role("checkbox", name="Tôi đã đọc và đồng ý với điều khoản sử dụng.").check()
            page.get_by_role("button", name="Tiếp tục xác thực").click()
            code_input = page.locator('input[inputmode="numeric"]')
            code_input.wait_for()
            login_mail = application.state.fake_mail.latest(email, "LOGIN_OTP")
            assert login_mail is not None
            code_input.fill(login_mail.code)
            page.get_by_role("button", name="Xác nhận").click()
            page.get_by_label("Mã xác nhận").wait_for()
            page.get_by_label("Mã xác nhận").fill(pyotp.TOTP(secret).now())
            page.get_by_role("button", name="Xác nhận").click()
            page.get_by_role("heading", name="Tài khoản đang chờ duyệt").wait_for()
            assert page.evaluate("async () => (await fetch('/api/v1/internal/zones')).status") == 403
            context.close()
    finally:
        vite.terminate()
        try:
            vite.wait(timeout=5)
        except subprocess.TimeoutExpired:
            vite.kill()
        api_server.should_exit = True
        api_thread.join(timeout=5)
        for path in (work / "ca.key", work / "server.key", work / "server.csr", work / "server.ext", work / "ca.srl"):
            path.unlink(missing_ok=True)
    print(f"PASS: current PC web trusted HTTPS browser smoke; screenshot={screenshot}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
