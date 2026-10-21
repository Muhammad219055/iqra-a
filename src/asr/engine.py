"""
ASR Engine wrapping tarteel-ai/whisper-base-ar-quran using Hugging Face Transformers.
Runs local inference on Apple Silicon (MPS / CPU).
"""

from pathlib import Path
from typing import Optional, Union
import numpy as np
import soundfile as sf
import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, GenerationConfig, pipeline

MODEL_ID = "tarteel-ai/whisper-base-ar-quran"


class QuranASREngine:
    def __init__(self, model_id: str = MODEL_ID, device: Optional[str] = None):
        if device is None:
            if torch.backends.mps.is_available():
                self.device = "mps"
            elif torch.cuda.is_available():
                self.device = "cuda"
            else:
                self.device = "cpu"
        else:
            self.device = device

        print(f"Loading ASR model {model_id} onto device: {self.device}...")
        self.processor = AutoProcessor.from_pretrained(model_id)
        self.model = AutoModelForSpeechSeq2Seq.from_pretrained(
            model_id,
            dtype=torch.float32,
            low_cpu_mem_usage=True,
        ).to(self.device)

        # Standardize generation config to ensure compatibility with modern transformers
        try:
            gen_config = GenerationConfig.from_pretrained("openai/whisper-base")
            gen_config.language = "ar"
            gen_config.task = "transcribe"
            gen_config.no_timestamps_token_id = 50363
            self.model.generation_config = gen_config
        except Exception as e:
            print(f"Warning: Could not fetch openai/whisper-base generation config: {e}")

        # Standard pipeline for audio transcription with chunking for long-form audio
        self.pipe = pipeline(
            "automatic-speech-recognition",
            model=self.model,
            tokenizer=self.processor.tokenizer,
            feature_extractor=self.processor.feature_extractor,
            device=self.device,
            chunk_length_s=25,
            return_timestamps=True,
        )
        print("ASR Model loaded successfully.")

    def transcribe(self, audio_input: Union[str, Path, np.ndarray], sample_rate: int = 16000) -> dict:
        """
        Transcribes audio (file path or numpy array of float32 samples at 16kHz).
        Returns a dict:
        {
            "text": str
        }
        """
        if isinstance(audio_input, (str, Path)):
            audio_path = str(audio_input)
            result = self.pipe(
                audio_path,
                generate_kwargs={"language": "ar", "task": "transcribe"},
            )
        elif isinstance(audio_input, np.ndarray):
            result = self.pipe(
                {"raw": audio_input, "sampling_rate": sample_rate},
                generate_kwargs={"language": "ar", "task": "transcribe"},
            )
        else:
            raise ValueError(f"Unsupported audio input type: {type(audio_input)}")

        return {
            "text": result.get("text", "").strip(),
        }
