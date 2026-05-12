from types import SimpleNamespace

import pytest

from utils import document_parser as dp


class _FakePixmap:
    def __init__(self, payload: bytes):
        self._payload = payload

    def tobytes(self, fmt: str) -> bytes:
        assert fmt == "jpg"
        return self._payload


class _FakePage:
    def __init__(self, payload: bytes):
        self._payload = payload

    def get_pixmap(self):
        return _FakePixmap(self._payload)


class _FakePdfDoc:
    def __init__(self, page_payloads: list[bytes]):
        self._pages = [_FakePage(payload) for payload in page_payloads]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def __iter__(self):
        return iter(self._pages)

    def __len__(self):
        return len(self._pages)


@pytest.mark.asyncio
async def test_extract_text_from_image_multimodal_processes_all_pdf_pages(monkeypatch):
    calls: list[str] = []

    class _FakeVisionLlm:
        async def ainvoke(self, messages):
            image_url = messages[0].content[1]["image_url"]["url"]
            payload = image_url.split(",", 1)[1]
            calls.append(payload)
            return SimpleNamespace(content=f"texto-{len(calls)}")

    monkeypatch.setattr(dp, "get_vision_llm", lambda: _FakeVisionLlm())
    monkeypatch.setattr(
        dp.fitz,
        "open",
        lambda stream, filetype: _FakePdfDoc([b"page-1", b"page-2", b"page-3"]),
    )

    extracted = await dp._extract_text_from_image_multimodal(b"fake-pdf", is_pdf=True)

    assert extracted == "texto-1\n\ntexto-2\n\ntexto-3"
    assert len(calls) == 3