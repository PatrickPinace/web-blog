from urllib.parse import urlparse

import cloudinary
import cloudinary.uploader
from flask import current_app

ALLOWED_IMAGE_FORMATS = frozenset({"jpeg", "png", "webp", "gif"})

# Transformacje zapewniające automatyczny format (WebP/AVIF) i kompresję —
# ograniczają zużycie darmowego kredytu Cloudinary (plan, sekcja 10).
DELIVERY_TRANSFORMATION = "f_auto,q_auto"


class UploadError(Exception):
    """Odrzucenie pliku na etapie walidacji — komunikat jest pokazywany adminowi."""


def configure(app):
    """Konfiguruje SDK Cloudinary z env — wariant URL-owy albo trzy osobne klucze."""
    if app.config.get("CLOUDINARY_URL"):
        cloudinary.config(cloudinary_url=app.config["CLOUDINARY_URL"])
    elif app.config.get("CLOUDINARY_CLOUD_NAME"):
        cloudinary.config(
            cloud_name=app.config["CLOUDINARY_CLOUD_NAME"],
            api_key=app.config["CLOUDINARY_API_KEY"],
            api_secret=app.config["CLOUDINARY_API_SECRET"],
            secure=True,
        )


def _sniff_format(head):
    """Rozpoznaje format obrazu po sygnaturze bajtowej.

    Własna implementacja zamiast `imghdr` ze stdlib, bo ten moduł został
    usunięty w Pythonie 3.13 — projekt ma być template'em do reużycia, więc
    nie wbudowujemy w niego zależności z datą ważności.
    """
    if head.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if head.startswith(b"GIF87a") or head.startswith(b"GIF89a"):
        return "gif"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "webp"
    return None


def detect_image_format(file_storage):
    """Rozpoznaje format po ZAWARTOŚCI pliku, nie po rozszerzeniu.

    Rozszerzenie i Content-Type pochodzą od klienta i można je dowolnie
    podmienić — `evil.php.jpg` czy `image/png` na pliku HTML to standardowe
    obejścia. Czytamy nagłówek pliku i przywracamy pozycję strumienia.
    """
    head = file_storage.stream.read(512)
    file_storage.stream.seek(0)
    return _sniff_format(head)


def upload_image(file_storage, folder="blog"):
    """Waliduje i wysyła obraz na Cloudinary. Zwraca (public_id, url).

    Pliki NIE lądują na dysku instancji — jest efemeryczny, więc zdjęcia
    zniknęłyby przy restarcie (plan, sekcja 7).
    """
    if file_storage is None or not file_storage.filename:
        raise UploadError("Nie wybrano pliku.")

    detected = detect_image_format(file_storage)
    if detected not in ALLOWED_IMAGE_FORMATS:
        raise UploadError(
            "Dozwolone są wyłącznie obrazy JPEG, PNG, WebP lub GIF "
            f"(wykryty typ: {detected or 'nieznany'})."
        )

    result = cloudinary.uploader.upload(
        file_storage,
        folder=folder,
        resource_type="image",
        transformation=DELIVERY_TRANSFORMATION,
    )
    return result["public_id"], result["secure_url"]


def is_allowed_image_url(url):
    """Sprawdza, czy URL obrazka pochodzi z dozwolonej domeny.

    Serwer NIGDY nie pobiera zasobu spod tego adresu — trafia on wprost do
    `img src`, a pobiera go dopiero przeglądarka czytelnika. Pobieranie po
    stronie serwera byłoby wektorem SSRF.
    """
    if not url:
        return False

    try:
        parsed = urlparse(url.strip())
    except ValueError:
        return False

    if parsed.scheme != "https":
        return False

    host = (parsed.hostname or "").lower()
    allowed = current_app.config.get("ALLOWED_IMAGE_HOSTS", ())
    # Dopasowanie dokładne albo jako poddomena — nigdy przez `in`/`endswith`
    # na gołym stringu, bo `res.cloudinary.com.evil.tld` by przeszło.
    return any(host == a or host.endswith(f".{a}") for a in allowed)
