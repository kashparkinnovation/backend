import os
import logging
from pathlib import Path
import firebase_admin
from firebase_admin import credentials, auth
from django.conf import settings
from decouple import config

logger = logging.getLogger(__name__)

# Module-level singleton — initialized once per process
_firebase_app = None


def _resolve_service_account_path() -> str:
    """Return the absolute path to the service account JSON file."""
    path = config('FIREBASE_SERVICE_ACCOUNT_JSON', default='')
    if path:
        return path
    # Default: firebase-service-account.json at the backend root
    base_dir = Path(__file__).resolve().parent.parent.parent
    return str(base_dir / 'firebase-service-account.json')


def get_firebase_app():
    """Initialize and return the Firebase Admin app (singleton)."""
    global _firebase_app

    # Already initialized
    if _firebase_app is not None:
        return _firebase_app

    # Already initialized by another code path (e.g. tests)
    if firebase_admin._apps:
        _firebase_app = firebase_admin.get_app()
        return _firebase_app

    sa_path = _resolve_service_account_path()

    if not os.path.exists(sa_path):
        raise RuntimeError(
            f"Firebase service account JSON not found at: {sa_path}\n"
            "Set the FIREBASE_SERVICE_ACCOUNT_JSON env variable to the correct path, "
            "or place firebase-service-account.json in the backend root directory."
        )

    try:
        cred = credentials.Certificate(sa_path)
        _firebase_app = firebase_admin.initialize_app(cred)
        logger.info("Firebase Admin SDK initialized from: %s", sa_path)
        return _firebase_app
    except Exception as exc:
        logger.error("Failed to initialize Firebase Admin SDK: %s", exc)
        raise RuntimeError(f"Firebase Admin SDK initialization failed: {exc}") from exc


def verify_firebase_token(id_token: str) -> dict:
    """
    Verify a Firebase ID token issued by the client SDK.
    Returns the decoded token payload (contains phone_number or email).
    Raises ValueError on any failure.
    """
    # DEBUG mock: allows local testing without a real Firebase token
    if settings.DEBUG and id_token == 'mock-token':
        logger.info("Using mock-token for OTP verification in DEBUG mode.")
        return {'phone_number': '+919999999999', 'uid': 'mock-uid-12345'}

    try:
        get_firebase_app()   # ensure SDK is initialized — raises RuntimeError if not
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except RuntimeError as exc:
        # Configuration error — surface it clearly
        raise ValueError(str(exc)) from exc
    except Exception as exc:
        logger.error("Firebase token verification failed: %s", exc)
        raise ValueError(f"Invalid Firebase Token: {exc}") from exc
