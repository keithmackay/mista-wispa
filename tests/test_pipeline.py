# tests/test_pipeline.py
import numpy as np
from unittest.mock import patch, MagicMock

from mista_wispa.pipeline import trim_silence, transcribe


def test_trim_silence_returns_none_for_silent_audio():
    # 1 second of silence
    silent = np.zeros((16000,), dtype=np.float32)
    with patch("mista_wispa.pipeline._vad_model") as mock_model:
        with patch("mista_wispa.pipeline.get_speech_timestamps", return_value=[]):
            result = trim_silence(silent, sample_rate=16000)
    assert result is None


def test_trim_silence_returns_speech_segments():
    audio = np.random.randn(32000).astype(np.float32) * 0.1
    speech_chunk = np.ones((8000,), dtype=np.float32) * 0.5

    with patch("mista_wispa.pipeline.get_speech_timestamps", return_value=[{"start": 0, "end": 8000}]):
        with patch("mista_wispa.pipeline.collect_chunks", return_value=MagicMock(numpy=MagicMock(return_value=speech_chunk))):
            result = trim_silence(audio, sample_rate=16000)
    assert result is not None
    assert len(result) == 8000


def test_transcribe_returns_text():
    audio = np.random.randn(16000).astype(np.float32)
    with patch("mista_wispa.pipeline.mlx_whisper") as mock_whisper:
        mock_whisper.transcribe.return_value = {"text": "Hello world"}
        result = transcribe(audio)
    assert result == "Hello world"


def test_transcribe_strips_whitespace():
    audio = np.random.randn(16000).astype(np.float32)
    with patch("mista_wispa.pipeline.mlx_whisper") as mock_whisper:
        mock_whisper.transcribe.return_value = {"text": "  Hello world  "}
        result = transcribe(audio)
    assert result == "Hello world"
