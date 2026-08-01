from flask_talisman import Talisman

# Skąd wolno ładować obrazki. `data:` jest potrzebne, bo Quill renderuje
# ikony paska narzędzi jako inline SVG.
_IMG_SRC = ["'self'", "data:", "https://res.cloudinary.com"]

# Ramki: wyłącznie odtwarzacz YouTube w wariancie no-cookie. Nic więcej —
# `iframe` nie jest przyjmowany od użytkownika (patrz app/utils/embeds.py).
_FRAME_SRC = ["https://www.youtube-nocookie.com"]

CSP = {
    "default-src": "'self'",
    "script-src": "'self'",
    "style-src": ["'self'", "'unsafe-inline'"],
    "img-src": _IMG_SRC,
    "frame-src": _FRAME_SRC,
    "frame-ancestors": "'none'",
    "base-uri": "'self'",
    "form-action": "'self'",
    "object-src": "'none'",
}


def register(app):
    """Włącza nagłówki bezpieczeństwa.

    `style-src` dopuszcza 'unsafe-inline', bo Quill ustawia style inline na
    elementach paska narzędzi i na obszarze edycji. To dotyczy WYŁĄCZNIE
    stylów — `script-src` pozostaje bez 'unsafe-inline' i bez 'unsafe-eval',
    więc wstrzyknięty skrypt i tak się nie wykona. Cały JS panelu siedzi
    w osobnych plikach (app/static/js/), nie w atrybutach `on*`.
    """
    Talisman(
        app,
        content_security_policy=CSP,
        content_security_policy_nonce_in=None,
        force_https=not app.config.get("DEBUG", False),
        strict_transport_security=not app.config.get("DEBUG", False),
        session_cookie_secure=app.config.get("SESSION_COOKIE_SECURE", True),
        frame_options="DENY",
    )
