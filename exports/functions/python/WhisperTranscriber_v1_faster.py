import logging
import subprocess

import psutil
import torch
from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)


class WhisperTranscriber:
    """
    Backend class for Whisper transcription logic using faster-whisper.
    Handles hardware detection (VRAM/RAM), model loading, and transcription.
    """

    MODEL_REQUIREMENTS = {
        "tiny": 0.3,
        "base": 0.5,
        "small": 1.0,
        "medium": 2.5,
        "large-v3": 3.5,
        "turbo": 2.0,
    }

    def __init__(self):
        self.model = None
        self.current_model_name = None
        self._hardware_info = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.last_warning = ""

    @staticmethod
    def _detect_vram_nvidia_smi():
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                vram_mb = float(result.stdout.strip().split("\n")[0])
                return round(vram_mb / 1024, 1)
        except Exception as e:
            logger.debug(f"nvidia-smi check failed: {e}")
        return 0.0

    def get_hardware_info(self):
        if self._hardware_info is not None:
            return self._hardware_info
        info = {"vram": 0.0, "ram": round(psutil.virtual_memory().total / (1024**3), 1)}
        info["vram"] = self._detect_vram_nvidia_smi()
        if info["vram"] == 0.0 and torch.cuda.is_available():
            info["vram"] = round(torch.cuda.get_device_properties(0).total_memory / (1024**3), 1)
        self._hardware_info = info
        return info

    def load_model(self, model_name="base", force_gpu=False):
        device = (
            "cuda"
            if force_gpu
            or (self.get_hardware_info()["vram"] >= self.MODEL_REQUIREMENTS.get(model_name, 1.0))
            else "cpu"
        )
        compute_type = "float16" if device == "cuda" else "int8"
        if self.model is None or self.current_model_name != model_name:
            self.model = WhisperModel(model_name, device=device, compute_type=compute_type)
            self.current_model_name = model_name
        return self.model

    def transcribe(self, path_or_io, model_name="base", force_gpu=False):
        self.load_model(model_name, force_gpu=force_gpu)
        segments, info = self.model.transcribe(path_or_io, beam_size=5)
        full_text = "".join([segment.text for segment in segments]).strip()
        return full_text
