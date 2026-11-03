"""Symmetric encryption for third-party tokens stored in the database.

Whoop and Oura hand out tokens that unlock a player's full health history -
far more than this app stores itself. They therefore never sit in the database
in plain text.

The key comes from ``WEARABLE_ENCRYPTION_KEY`` when set. If it is not set we
derive one from ``JWT_SECRET_KEY``, so a deployment that only configured the
JWT secret still gets encryption instead of silently falling back to plaintext.
Rotating either value makes existing tokens undecryptable on purpose - players
then simply reconnect their device.
"""

from __future__ import annotations

import base64
import hashlib
import os

from cryptography.fernet import Fernet, InvalidToken

_ENV_KEY = "WEARABLE_ENCRYPTION_KEY"


def _derive_key() -> bytes:
    configured = os.getenv(_ENV_KEY, "").strip()
    if configured:
        # A real Fernet key can be used as-is; anything else becomes key material.
        try:
            Fernet(configured.encode("utf-8"))
            return configured.encode("utf-8")
        except (ValueError, TypeError):
            secret = configured
    else:
        from app.services.auth import JWT_SECRET_KEY

        secret = JWT_SECRET_KEY

    digest = hashlib.sha256(f"volleysync-wearables:{secret}".encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def _fernet() -> Fernet:
    # Built per call so a changed environment variable takes effect on restart
    # without any module-level caching surprises in tests.
    return Fernet(_derive_key())


def encrypt_secret(value: str | None) -> str | None:
    if value is None:
        return None
    return _fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: str | None) -> str | None:
    """Return the plaintext, or ``None`` when the value cannot be decrypted.

    A rotated key must not crash the API - the caller treats ``None`` as
    "connection is broken, ask the player to reconnect".
    """
    if value is None:
        return None
    try:
        return _fernet().decrypt(value.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError, TypeError):
        return None


def hash_ingest_token(token: str) -> str:
    """Ingest tokens are compared by hash, like a password."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
