import os
import time
from dotenv import load_dotenv
import warnings

warnings.filterwarnings("ignore")
load_dotenv()

class Config:
    # 키 로드
    GEMINI_KEYS = [os.getenv(f"GEMINI_API_KEY{'_'+str(i) if i>1 else ''}") for i in range(1, 6)]
    GEMINI_KEYS = [k for k in GEMINI_KEYS if k] # 빈 키 제거
    
    SERPER_KEY = os.getenv("SERPER_API_KEY")
    current_key_idx = 0
    
    # 텍스트 생성 모델 (유지)
    MODEL_NAME = "models/gemini-flash-latest"
    
    # [수정] TTS 모델명 변경 (여기가 문제였습니다!)
    # 기존 "preview-tts"는 없는 모델이라 404 에러가 났을 겁니다.
    # 현재 작동하는 "exp" 버전으로 교체합니다.
    TTS_MODEL_NAME = "models/gemini-2.0-flash-exp"

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
        time.sleep(2) # 교체 후 잠시 대기
        return cls.get_current_key()