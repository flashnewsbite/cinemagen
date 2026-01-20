import os
import time
from dotenv import load_dotenv
import warnings

warnings.filterwarnings("ignore")
load_dotenv()

class Config:
    # Gemini 키 로드
    GEMINI_KEYS = [os.getenv(f"GEMINI_API_KEY{'_'+str(i) if i>1 else ''}") for i in range(1, 6)]
    GEMINI_KEYS = [k for k in GEMINI_KEYS if k]
    
    # [중요] Serper 키 로드
    SERPER_KEY = os.getenv("SERPER_API_KEY")
    
    current_key_idx = 0
    MODEL_NAME = "gemini-1.5-flash"

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
        time.sleep(10)
        return cls.get_current_key()