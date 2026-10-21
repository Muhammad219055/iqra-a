"""
Voice Activity Detection (VAD) module.
Processes 16 kHz 16-bit mono PCM chunks.
Calculates energy and speech activity to gate audio buffers and monitor silence.
"""

from typing import Union
import numpy as np


class SimpleVAD:
    def __init__(self, energy_threshold: float = 0.015):
        self.energy_threshold = energy_threshold

    def is_speech(self, pcm_chunk: Union[bytes, np.ndarray]) -> bool:
        """
        Determines whether the given 16kHz mono audio chunk contains active speech.
        """
        if isinstance(pcm_chunk, bytes):
            samples = np.frombuffer(pcm_chunk, dtype=np.int16).astype(np.float32) / 32768.0
        elif isinstance(pcm_chunk, np.ndarray):
            if pcm_chunk.dtype == np.int16:
                samples = pcm_chunk.astype(np.float32) / 32768.0
            else:
                samples = pcm_chunk
        else:
            return False

        if len(samples) == 0:
            return False

        rms = np.sqrt(np.mean(samples ** 2))
        return bool(rms > self.energy_threshold)

    def calculate_rms(self, pcm_chunk: bytes) -> float:
        """Returns normalized RMS volume (0.0 to 1.0) for live UI waveforms."""
        if not pcm_chunk:
            return 0.0
        samples = np.frombuffer(pcm_chunk, dtype=np.int16).astype(np.float32) / 32768.0
        return float(np.sqrt(np.mean(samples ** 2)))
