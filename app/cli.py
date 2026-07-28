"""Owner-operated administrative commands."""

from __future__ import annotations

import argparse
import asyncio
import getpass
import sys
import unicodedata

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from sqlalchemy import select

from app.database import dispose_database, get_session_factory
from app.models import User
from app.utils import hash_password, normalize_identity


class UserProvisionInput(BaseModel):
    """Validated input for the owner-only local user provisioning command."""

    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=1, max_length=100)
    email: EmailStr
    display_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=12, max_length=256)
    admin: bool = False

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        normalized = normalize_identity(value)
        if len(normalized) > 100:
            raise ValueError("username must not exceed 100 normalized characters")
        return normalized

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        normalized = normalize_identity(str(value))
        if len(normalized) > 255:
            raise ValueError("email must not exceed 255 normalized characters")
        return normalized

    @field_validator("display_name")
    @classmethod
    def normalize_display_name(cls, value: str) -> str:
        normalized = unicodedata.normalize("NFC", value).strip()
        if not normalized:
            raise ValueError("display name must not be blank")
        if any(unicodedata.category(char) in {"Cc", "Cs"} for char in normalized):
            raise ValueError("display name contains control or surrogate characters")
        if len(normalized) > 255:
            raise ValueError("display name must not exceed 255 characters")
        return normalized


async def create_user(
    *, username: str, email: str, display_name: str, password: str, admin: bool
) -> None:
    command = UserProvisionInput(
        username=username,
        email=email,
        display_name=display_name,
        password=password,
        admin=admin,
    )

    async with get_session_factory()() as session, session.begin():
        duplicate = await session.scalar(
            select(User.id).where(
                (User.username == command.username) | (User.email == command.email)
            )
        )
        if duplicate is not None:
            raise ValueError("username or email already exists")
        session.add(
            User(
                username=command.username,
                email=command.email,
                display_name=command.display_name,
                password_hash=hash_password(command.password),
                is_admin=command.admin,
            )
        )


def read_password(*, from_stdin: bool) -> str:
    """Read a password without placing it in the process argument list."""

    if from_stdin:
        value = sys.stdin.readline()
        if not value:
            raise ValueError("password stdin was empty")
        return value.rstrip("\r\n")

    password = getpass.getpass("Password: ")
    confirmation = getpass.getpass("Confirm password: ")
    if password != confirmation:
        raise ValueError("password confirmation did not match")
    return password


async def _main_async(args: argparse.Namespace) -> None:
    try:
        if args.command == "create-user":
            await create_user(
                username=args.username,
                email=args.email,
                display_name=args.display_name,
                password=read_password(from_stdin=args.password_stdin),
                admin=args.admin,
            )
            print("user created")
    finally:
        await dispose_database()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    create = subparsers.add_parser("create-user")
    create.add_argument("--username", required=True)
    create.add_argument("--email", required=True)
    create.add_argument("--display-name", required=True)
    create.add_argument(
        "--password-stdin",
        action="store_true",
        help="read one password line from standard input instead of prompting",
    )
    create.add_argument("--admin", action="store_true")
    args = parser.parse_args()
    asyncio.run(_main_async(args))


if __name__ == "__main__":
    main()
