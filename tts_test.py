import requests
import base64
import json
import time
from config import Config

# ==========================================
# 1. 설정
# ==========================================
MODEL_NAME = "models/gemini-2.0-flash-exp"
TEST_TEXT = "This is a test for Gemini 2.0 Flash Experimental audio generation capabilities."
VOICE_NAME = "Aoede" # 여성 음성 중 하나
# ==========================================

def test_gemini_tts():
    print(f"🚀 Testing {MODEL_NAME} for Audio Generation...")
    
    # 키가 없으면 에러
    if not Config.GEMINI_KEYS:
        print("❌ No API Keys found in Config.")
        return

    # 키 로테이션 시도
    for i, api_key in enumerate(Config.GEMINI_KEYS):
        print(f"🔑 Trying Key #{i+1}...")
        
        url = f"https://generativelanguage.googleapis.com/v1beta/{MODEL_NAME}:generateContent?key={api_key}"
        
        payload = {
            "contents": [{
                "parts": [{"text": TEST_TEXT}]
            }],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "voiceConfig": {
                        "prebuiltVoiceConfig": {
                            "voiceName": VOICE_NAME
                        }
                    }
                }
            }
        }

        try:
            response = requests.post(url, json=payload, timeout=15)
            
            if response.status_code == 200:
                resp_json = response.json()
                if 'candidates' in resp_json and resp_json['candidates']:
                    part = resp_json['candidates'][0]['content']['parts'][0]
                    if 'inlineData' in part and 'data' in part['inlineData']:
                        b64_audio = part['inlineData']['data']
                        audio_data = base64.b64decode(b64_audio)
                        
                        filename = f"test_audio_result.mp3"
                        with open(filename, "wb") as f:
                            f.write(audio_data)
                        
                        print(f"✅ Success! Audio saved as '{filename}' using Key #{i+1}")
                        return
                
                print("❌ Model responded but no audio data found.")
                # print("Full Response:", json.dumps(resp_json, indent=2))
                
            elif response.status_code == 429:
                print(f"⚠️ Quota Exceeded for Key #{i+1}. Switching key...")
                continue # 다음 키 시도
            else:
                print(f"❌ API Error {response.status_code}")
                print("Reason:", response.text)

        except Exception as e:
            print(f"❌ Connection Error: {e}")
            
    print("❌ All keys exhausted or failed.")

if __name__ == "__main__":
    test_gemini_tts()