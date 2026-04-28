import os
import logging
from pathlib import Path
import firebase_admin
from firebase_admin import credentials, auth
from django.conf import settings
from decouple import config

logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK
_firebase_app = None

def get_firebase_app():
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app

    # Try to get path from environment or default to backend root
    service_account_path = config('FIREBASE_SERVICE_ACCOUNT_JSON', default='')
    
    if not service_account_path:
        # Default fallback
        base_dir = Path(__file__).resolve().parent.parent.parent
        service_account_path = os.path.join(base_dir, 'firebase-service-account.json')

    try:
        if os.path.exists(service_account_path):
            cred = credentials.Certificate(service_account_path)
            _firebase_app = firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin SDK initialized successfully.")
        else:
            # For development, if we don't have a JSON file, we might try default credentials
            # but we'll log a warning instead.
            logger.warning(
                f"Firebase service account JSON not found at {service_account_path}. "
                "OTP verification will fail unless configured."
            )
    except Exception as e:
        logger.error(f"Failed to initialize Firebase Admin SDK: {e}")
        
    return _firebase_app

def verify_firebase_token(id_token):
    """
    Verifies the client-side Firebase ID token.
    Returns the decoded token payload including the phone_number.
    """
    get_firebase_app()
    try:
        # verify_id_token requires the app to be initialized
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except Exception as e:
        logger.error(f"Firebase token verification failed: {e}")
        # In DEBUG mode, if token is 'mock-token', allow testing
        if settings.DEBUG and id_token == 'mock-token':
            logger.info("Using mock-token for OTP verification in DEBUG mode.")
            return {
                'phone_number': '+919999999999',
                'uid': 'mock-uid-12345'
            }
        raise ValueError(f"Invalid Firebase Token: {e}")
