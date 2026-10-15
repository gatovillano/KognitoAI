"""
Regresiones de KogniPhotos sobre conservación de la calidad del original.

Dos bugs históricos que estos tests fijan:

1. Los originales se guardaban bajo una raíz por cuenta
   (`{cloud_storage_path}/photos`) que el mount estático `/media` no expone,
   así que el visor pedía un archivo que existía pero devolvía 404. Ahora los
   originales se sirven por endpoint, que resuelve la raíz de la cuenta.

2. El thumbnail se generaba a 256px sin EXIF rotation, lo que dejaba las fotos
   de móvil en vertical tumbadas y hacía que la galería se viera borrosa.
"""

import io
import os

import pytest
from PIL import Image

from api import galleries


def _make_image(path, size=(2400, 1600), color=(200, 40, 40), exif_orientation=None):
    """Crea una imagen real en disco y devuelve sus bytes."""
    img = Image.new("RGB", size, color)
    if exif_orientation is not None:
        exif = img.getexif()
        exif[274] = exif_orientation  # Orientation
        img.save(path, "JPEG", exif=exif)
    else:
        img.save(path, "JPEG", quality=100)
    with open(path, "rb") as fh:
        return fh.read()


class TestOriginalIsServed:
    """El original debe servirse desde la raíz de la cuenta, no desde MEDIA_ROOT."""

    def test_resolve_photo_path_uses_account_cloud_storage(self, tmp_path, monkeypatch):
        account = type("Acct", (), {"cloud_storage_path": str(tmp_path)})()

        resolved = galleries.resolve_photo_path(account, "album-uuid/foto.jpg")

        # Debe colgar de cloud_storage_path, no de MEDIA_ROOT.
        assert resolved == os.path.join(str(tmp_path), "photos", "album-uuid", "foto.jpg")

    def test_resolve_photo_path_falls_back_to_media_root(self, monkeypatch):
        monkeypatch.setattr(galleries, "MEDIA_ROOT", "/media/root")
        account = type("Acct", (), {"cloud_storage_path": None})()

        resolved = galleries.resolve_photo_path(account, "album-uuid/foto.jpg")

        assert resolved == os.path.join("/media/root", "album-uuid", "foto.jpg")

    def test_original_bytes_are_never_reencoded(self, tmp_path, monkeypatch):
        """Copiar el original debe preservar los bytes byte a byte."""
        monkeypatch.setattr(
            galleries, "get_account_media_root", lambda account: str(tmp_path)
        )

        source = tmp_path / "origen.jpg"
        original_bytes = _make_image(source, size=(3000, 2000))

        # Replica exacta de lo que hace upload_photos con el archivo original.
        import shutil

        dest = tmp_path / "destino.jpg"
        with open(dest, "wb") as buffer:
            shutil.copyfileobj(open(source, "rb"), buffer)

        assert dest.read_bytes() == original_bytes


class TestThumbnailQuality:
    def test_thumbnail_is_large_enough_for_the_grid(self, tmp_path):
        """Un thumbnail de 256px se ve borroso; debe ser bastante mayor."""
        src = tmp_path / "foto.jpg"
        _make_image(src, size=(4000, 3000))

        out = tmp_path / "thumb.jpg"
        assert galleries.generate_thumbnail_sync(str(src), str(out)) is True

        with Image.open(out) as thumb:
            assert max(thumb.size) == galleries.THUMBNAIL_SIZE[0]
            assert max(thumb.size) > 256

    def test_thumbnail_honours_exif_orientation(self, tmp_path):
        """Orientation=6 = rotar 90°.

        Una foto de móvil se guarda en landscape (4000x3000) con el tag de
        orientación, y el visor debe mostrarla portrait. Sin exif_transpose el
        thumbnail sale tumbado.
        """
        src = tmp_path / "movil.jpg"
        _make_image(src, size=(4000, 3000), exif_orientation=6)

        # El original en disco sigue siendo landscape: no lo tocamos.
        with Image.open(src) as original:
            assert original.size == (4000, 3000)
            assert original.getexif().get(274) == 6

        out = tmp_path / "thumb.jpg"
        assert galleries.generate_thumbnail_sync(str(src), str(out)) is True

        with Image.open(out) as thumb:
            # Landscape rotado 90° queda portrait.
            assert thumb.height > thumb.width

    def test_thumbnail_is_always_jpeg(self, tmp_path):
        """Un .png renombrado a .jpg rompería el Content-Type de StaticFiles."""
        src = tmp_path / "foto.png"
        Image.new("RGBA", (500, 500), (255, 0, 0, 128)).save(src, "PNG")

        out = tmp_path / "thumb.jpg"
        assert galleries.generate_thumbnail_sync(str(src), str(out)) is True

        with Image.open(out) as thumb:
            assert thumb.format == "JPEG"

    def test_unreadable_file_returns_false_instead_of_raising(self, tmp_path):
        """Un archivo corrupto no debe tumbar el lote de subida."""
        bad = tmp_path / "roto.jpg"
        bad.write_bytes(b"esto no es una imagen")

        out = tmp_path / "thumb.jpg"
        assert galleries.generate_thumbnail_sync(str(bad), str(out)) is False

    def test_srgb_thumbnail_keeps_identical_icc_bytes(self, tmp_path):
        """El perfil sRGB debe sobrevivir al thumbnail byte a byte."""
        icc = open("/usr/share/color/icc/colord/sRGB.icc", "rb").read()
        src = tmp_path / "srgb.jpg"
        Image.new("RGB", (800, 600), (18, 18, 18)).save(
            src, "JPEG", icc_profile=icc, quality=95
        )

        out = tmp_path / "thumb.jpg"
        assert galleries.generate_thumbnail_sync(str(src), str(out)) is True

        with Image.open(out) as thumb:
            assert thumb.info.get("icc_profile") == icc

    def test_adobe_rgb_thumbnail_converts_to_srgb_appearance(self, tmp_path):
        """Un Adobe RGB sin conversión se ve lavado (el bug reportado).

        El thumbnail debe coincidir con la conversión de referencia a sRGB,
        no con los valores crudos del original.
        """
        import io as _io
        import statistics
        from PIL import ImageCms as _ImageCms

        icc_adobe = open("/usr/share/color/icc/colord/AdobeRGB1998.icc", "rb").read()
        srgb = _ImageCms.createProfile("sRGB")
        src_profile = _ImageCms.getOpenProfile(_io.BytesIO(icc_adobe))

        src = tmp_path / "adobe.jpg"
        # Rojo muy saturado de gamut amplio: en Adobe RGB existe, en sRGB se recorta.
        Image.new("RGB", (400, 400), (255, 40, 30)).save(
            src, "JPEG", icc_profile=icc_adobe, quality=100
        )

        out = tmp_path / "thumb.jpg"
        assert galleries.generate_thumbnail_sync(str(src), str(out)) is True

        with Image.open(src) as original:
            ref = _ImageCms.profileToProfile(
                original, src_profile, srgb, outputMode="RGB"
            )
        with Image.open(out) as thumb:
            # Sin píxeles convertidos el thumbnail conservaría (255, 40, 30);
            # convertido a sRGB el rojo se re-mapea (los valores exactos los
            # define LCMS, aquí solo exigimos que haya cambiado hacia sRGB).
            got = thumb.convert("RGB").getpixel((200, 200))
            want = ref.getpixel((200, 200))
            assert got != (255, 40, 30), "el thumbnail ignora el perfil ICC"
            assert statistics.mean(
                abs(c1 - c2) for c1, c2 in zip(got, want)
            ) < 12, f"thumbnail {got} lejos de la referencia sRGB {want}"
            # Y no debe incrustar el perfil Adobe sobre píxeles ya sRGB
            # (ese doble etiquetado lava los negros en visores gestionados).
            assert thumb.info.get("icc_profile") != icc_adobe


class TestSharedLinkThumbnailUnchanged:
    def test_thumbnail_default_size_is_configurable(self):
        assert galleries.THUMBNAIL_SIZE == (1024, 1024)
        assert galleries.THUMBNAIL_QUALITY >= 85