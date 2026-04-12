# src/mista_wispa/pipeline.py
import numpy as np
import torch
import mlx_whisper
from silero_vad import load_silero_vad, get_speech_timestamps, collect_chunks

WHISPER_MODEL = "mlx-community/whisper-large-v3-turbo"

_vad_model = None


def _get_vad_model():
    global _vad_model
    if _vad_model is None:
        _vad_model = load_silero_vad()
    return _vad_model


def trim_silence(audio: np.ndarray, sample_rate: int = 16000) -> np.ndarray | None:
    model = _get_vad_model()
    wav = torch.from_numpy(audio).float()
    timestamps = get_speech_timestamps(wav, model, sampling_rate=sample_rate)
    if not timestamps:
        return None
    speech = collect_chunks(timestamps, wav)
    return speech.numpy()


def transcribe(audio: np.ndarray) -> str:
    result = mlx_whisper.transcribe(audio, path_or_hf_repo=WHISPER_MODEL)
    return result["text"].strip()


def warmup():
    """Pre-load VAD and Whisper models so first dictation is fast."""
    _get_vad_model()
    # Transcribe a tiny silent clip to force Whisper model loading
    silent = np.zeros(1600, dtype=np.float32)
    mlx_whisper.transcribe(silent, path_or_hf_repo=WHISPER_MODEL)
