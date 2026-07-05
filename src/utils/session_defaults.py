"""Session cookie configuration helpers.

Standalone module with no Flask or app-level imports so it can be unit-tested
without triggering the full application initialization sequence.
"""
import os


def _default_session_cookie_secure() -> bool:
    """Return the value to use for SESSION_COOKIE_SECURE.

    If the environment variable is explicitly set, honor it. If unset, derive
    from BASE_URL: Secure only when the deployment is HTTPS. This prevents the
    silent login-bounce loop a Secure cookie causes over plain HTTP. Operators
    who terminate TLS at a proxy should set BASE_URL=https://... (which is
    already required for correct feed URLs) or set SESSION_COOKIE_SECURE
    explicitly.
    """
    explicit = os.environ.get('SESSION_COOKIE_SECURE')
    if explicit is not None:
        return explicit.lower() == 'true'
    base_url = os.environ.get('BASE_URL', '')
    return base_url.lower().startswith('https')
