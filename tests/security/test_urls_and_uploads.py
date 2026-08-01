"""Walidacja adresów (YouTube, obrazki) i uploadu plików.

Uruchamiane osobno: `pytest tests/security`.
"""

import io

import pytest
from werkzeug.datastructures import FileStorage

from app.utils.embeds import extract_youtube_id
from app.utils.uploads import detect_image_format, is_allowed_image_url

# Minimalne, poprawne nagłówki plików graficznych.
PNG_HEADER = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
JPEG_HEADER = b"\xff\xd8\xff\xe0" + b"\x00" * 32
GIF_HEADER = b"GIF89a" + b"\x00" * 32
WEBP_HEADER = b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"\x00" * 32


class TestYouTubeValidation:
    @pytest.mark.parametrize(
        "url",
        [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtube.com/watch?v=dQw4w9WgXcQ&t=42",
            "https://youtu.be/dQw4w9WgXcQ",
            "https://www.youtube.com/embed/dQw4w9WgXcQ",
            "https://m.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://www.youtube.com/shorts/dQw4w9WgXcQ",
        ],
    )
    def test_valid_urls_accepted(self, url):
        assert extract_youtube_id(url) == "dQw4w9WgXcQ"

    @pytest.mark.parametrize(
        "url",
        [
            "https://youtube.com.evil.tld/watch?v=dQw4w9WgXcQ",
            "https://evil-youtube.com/watch?v=dQw4w9WgXcQ",
            "https://notyoutube.com/watch?v=dQw4w9WgXcQ",
            "https://youtube.evil.tld/watch?v=dQw4w9WgXcQ",
            "javascript:alert(1)",
            "data:text/html,<script>alert(1)</script>",
            "file:///etc/passwd",
            'https://youtube.com/watch?v=" onload="alert(1)',
            "https://youtube.com/watch?v=../../etc/passwd",
            "https://youtube.com/watch?v=short",
            "http://169.254.169.254/latest/meta-data/",
            "http://localhost:5000/admin",
            "",
            None,
        ],
    )
    def test_hostile_urls_rejected(self, url):
        assert extract_youtube_id(url) is None


class TestImageUrlWhitelist:
    def test_cloudinary_url_accepted(self, app):
        with app.app_context():
            assert is_allowed_image_url("https://res.cloudinary.com/demo/image/x.jpg")

    @pytest.mark.parametrize(
        "url",
        [
            "https://res.cloudinary.com.evil.tld/x.jpg",
            "https://evil.tld/x.jpg",
            "http://res.cloudinary.com/x.jpg",  # brak HTTPS
            "javascript:alert(1)",
            "http://169.254.169.254/latest/meta-data/",
            "http://localhost/secret.png",
            "",
            None,
        ],
    )
    def test_hostile_image_urls_rejected(self, app, url):
        with app.app_context():
            assert is_allowed_image_url(url) is False


class TestUploadTypeDetection:
    @pytest.mark.parametrize(
        ("payload", "expected"),
        [
            (PNG_HEADER, "png"),
            (JPEG_HEADER, "jpeg"),
            (GIF_HEADER, "gif"),
            (WEBP_HEADER, "webp"),
        ],
    )
    def test_real_images_detected(self, payload, expected):
        storage = FileStorage(stream=io.BytesIO(payload), filename="x.bin")
        assert detect_image_format(storage) == expected

    @pytest.mark.parametrize(
        "payload",
        [
            b"<?php system($_GET['c']); ?>",
            b"<script>alert(1)</script>",
            b"#!/bin/sh\nrm -rf /",
            b"GIF87a-but-not-really" and b"MZ\x90\x00",  # plik wykonywalny
            b"",
        ],
    )
    def test_non_images_rejected_regardless_of_filename(self, payload):
        """Rozszerzenie pliku pochodzi od klienta — liczy się zawartość."""
        storage = FileStorage(stream=io.BytesIO(payload), filename="innocent.jpg")
        assert detect_image_format(storage) not in ("png", "jpeg", "gif", "webp")

    def test_stream_position_restored(self):
        """Detekcja nie może zjeść nagłówka — plik musi dać się jeszcze wysłać."""
        storage = FileStorage(stream=io.BytesIO(PNG_HEADER), filename="x.png")
        detect_image_format(storage)
        assert storage.stream.read(8) == b"\x89PNG\r\n\x1a\n"
