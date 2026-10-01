from __future__ import annotations

import argparse
import getpass

import pyotp

from .db import db


def main() -> None:
    parser = argparse.ArgumentParser(description="Quản trị IOT Drone Station")
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create-user")
    create.add_argument("username")
    create.add_argument("--role", choices=["admin", "user"], required=True)
    password_command = sub.add_parser("set-password")
    password_command.add_argument("username")
    totp_command = sub.add_parser("rotate-totp")
    totp_command.add_argument("username")
    args = parser.parse_args()
    db.initialize()
    if args.command in {"create-user", "set-password"}:
        password = getpass.getpass("Mật khẩu mới (ít nhất 12 ký tự): ")
        confirm = getpass.getpass("Nhập lại mật khẩu: ")
        if password != confirm or len(password) < 12:
            raise SystemExit("Mật khẩu không khớp hoặc ngắn hơn 12 ký tự")
        if args.command == "set-password":
            db.set_password(args.username, password)
            print(f"Đã đổi mật khẩu và thu hồi session của {args.username}")
            return
        secret = pyotp.random_base32() if args.role == "admin" else None
        db.create_user(args.username, password, args.role, secret)
        print(f"Đã tạo user {args.username} ({args.role})")
    else:
        secret = pyotp.random_base32()
        db.set_totp_secret(args.username, secret)
        print(f"Đã đổi TOTP và thu hồi session của {args.username}")
    if secret:
        print("TOTP secret (chỉ hiển thị một lần):", secret)
        print("URI:", pyotp.TOTP(secret).provisioning_uri(args.username, issuer_name="IOT Drone Station"))


if __name__ == "__main__":
    main()
