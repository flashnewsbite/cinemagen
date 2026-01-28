import os
import time
from dotenv import load_dotenv
import warnings

warnings.filterwarnings("ignore")
load_dotenv()

class Config:
    # 기존 Gemini 키 로드
    GEMINI_KEYS = [os.getenv(f"GEMINI_API_KEY{'_'+str(i) if i>1 else ''}") for i in range(1, 6)]
    GEMINI_KEYS = [k for k in GEMINI_KEYS if k]
    
    SERPER_KEY = os.getenv("SERPER_API_KEY")
    
    # [수정] .env에서 불러오도록 변경 (보안 강화)
    PEXELS_KEY = os.getenv("PEXELS_API_KEY")

    current_key_idx = 0
    
    MODEL_NAME = "models/gemini-flash-latest"
    TTS_MODEL_NAME = "models/gemini-2.0-flash-exp"

    # [NEW] 해상도 설정
    VIDEO_DIMENSIONS = {
        "shorts": (720, 1280),
        "long": (1920, 1080)
    }

    SAFETY_SETTINGS = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]

    @classmethod
    def get_current_key(cls):
        if not cls.GEMINI_KEYS: return None
        return cls.GEMINI_KEYS[cls.current_key_idx]

    @classmethod
    def rotate_key(cls):
        if not cls.GEMINI_KEYS: return None
        cls.current_key_idx = (cls.current_key_idx + 1) % len(cls.GEMINI_KEYS)
        print(f"   🔄 API 키 교체 중... (Key #{cls.current_key_idx + 1})")
        time.sleep(2)
        return cls.get_current_key()