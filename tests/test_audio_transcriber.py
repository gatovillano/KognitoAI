import asyncio
from io import BytesIO
from types import SimpleNamespace

import pytest
from pydub.exceptions import CouldntDecodeError

from utils import audio_transcriber


def test_transcribe_audio_file_rejects_empty_audio(monkeypatch):
    async def fake_get_whisper_model():
        return object()

    monkeypatch.setattr(audio_transcriber, "get_whisper_model", fake_get_whisper_model)

    with pytest.raises(audio_transcriber.InvalidAudioFileError, match="vacío"):
        asyncio.run(audio_transcriber.transcribe_audio_file(BytesIO(b""), "webm"))


def test_transcribe_audio_file_rejects_invalid_audio(monkeypatch):
    async def fake_get_whisper_model():
        return object()

    monkeypatch.setattr(audio_transcriber, "get_whisper_model", fake_get_whisper_model)
    monkeypatch.setattr(
        audio_transcriber.AudioSegment,
        "from_file",
        lambda *args, **kwargs: (_ for _ in ()).throw(CouldntDecodeError("decode failed")),
    )

    with pytest.raises(audio_transcriber.InvalidAudioFileError, match="no es válido|incompleto"):
        asyncio.run(audio_transcriber.transcribe_audio_file(BytesIO(b"invalid-webm"), "webm"))


def test_transcribe_audio_file_returns_transcription(monkeypatch):
    class FakeAudioSegment:
        def export(self, target, format):
            target.write(b"fake wav")

    class FakeModel:
        def transcribe(self, wav_file, language, vad_filter, vad_parameters):
            assert wav_file.read() == b"fake wav"
            return iter([SimpleNamespace(text="hola mundo")]), SimpleNamespace(language="es")

    async def fake_get_whisper_model():
        return FakeModel()

    monkeypatch.setattr(audio_transcriber, "get_whisper_model", fake_get_whisper_model)
    monkeypatch.setattr(audio_transcriber.AudioSegment, "from_file", lambda *args, **kwargs: FakeAudioSegment())

    result = asyncio.run(audio_transcriber.transcribe_audio_file(BytesIO(b"valid-audio"), "webm"))

    assert result == "hola mundo"
