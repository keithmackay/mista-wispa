# tests/test_audio.py
import numpy as np
from unittest.mock import patch, MagicMock

from mista_wispa.audio import AudioRecorder


def test_recorder_initial_state():
    with patch("mista_wispa.audio.sd"):
        rec = AudioRecorder(sample_rate=16000)
        assert rec.is_recording is False
        assert rec.get_audio() is None


def test_start_sets_recording_flag():
    with patch("mista_wispa.audio.sd"):
        rec = AudioRecorder(sample_rate=16000)
        rec.start()
        assert rec.is_recording is True


def test_stop_returns_audio_array():
    with patch("mista_wispa.audio.sd") as mock_sd:
        rec = AudioRecorder(sample_rate=16000)
        rec.start()
        # Simulate some audio frames being captured
        fake_audio = np.zeros((1600,), dtype=np.float32)
        rec._frames.append(fake_audio)
        audio = rec.stop()
        assert isinstance(audio, np.ndarray)
        assert audio.dtype == np.float32
        assert len(audio) == 1600


def test_stop_when_not_recording_returns_none():
    with patch("mista_wispa.audio.sd"):
        rec = AudioRecorder(sample_rate=16000)
        assert rec.stop() is None


def test_stop_with_no_frames_returns_none():
    with patch("mista_wispa.audio.sd"):
        rec = AudioRecorder(sample_rate=16000)
        rec.start()
        audio = rec.stop()
        assert audio is None
