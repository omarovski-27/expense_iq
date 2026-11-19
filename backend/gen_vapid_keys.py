"""Generate a VAPID key pair for Web Push. Run once: python gen_vapid_keys.py

Paste both values into Render's environment (VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY).
Rotating them invalidates every existing device subscription.
"""
import base64

from cryptography.hazmat.primitives import serialization
from py_vapid import Vapid


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def generate() -> tuple[str, str]:
    vapid = Vapid()
    vapid.generate_keys()
    public = vapid.public_key.public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )
    private = vapid.private_key.private_numbers().private_value.to_bytes(32, "big")
    return _b64url(public), _b64url(private)


if __name__ == "__main__":
    pub, priv = generate()
    print(f"VAPID_PUBLIC_KEY={pub}")
    print(f"VAPID_PRIVATE_KEY={priv}")
