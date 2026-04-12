# src/mista_wispa/audio.py
import threading

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000
CHANNELS = 1
BLOCK_SIZE = 1024


class AudioRecorder:
    def __init__(self, sample_rate: int = SAMPLE_RATE):
        self._sample_rate = sample_rate
        self._stream: sd.InputStream | None = None
        self._frames: list[np.ndarray] = []
        self._lock = threading.Lock()
        self.is_recording = False

    def _audio_callback(self, indata: np.ndarray, frames: int, time_info, status):
        with self._lock:
            if self.is_recording:
                self._frames.append(indata[:, 0].copy())

    def start(self):
        with self._lock:
            self._frames.clear()
            self.is_recording = True
        self._stream = sd.InputStream(
            samplerate=self._sample_rate,
            channels=CHANNELS,
            blocksize=BLOCK_SIZE,
            dtype=np.float32,
            callback=self._audio_callback,
        )
        self._stream.start()

    def stop(self) -> np.ndarray | None:
        if not self.is_recording:
            return None
        self.is_recording = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        with self._lock:
            if not self._frames:
                return None
            audio = np.concatenate(self._frames)
            self._frames.clear()
        return audio

    def get_audio(self) -> np.ndarray | None:
        with self._lock:
            if not self._frames:
                return None
            return np.concatenate(self._frames)
