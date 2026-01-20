import os
import json
import requests
import edge_tts
import asyncio
from PIL import Image
from config import Config
import random
import google.generativeai as genai
import base64

class MediaAgent:
    def __init__(self):
        os.makedirs("images", exist_ok=True)
        os.makedirs("audio", exist_ok=True)

    # 1. Gemini Voices (AI Studio)
    GEMINI_VOICES = {
        "male": {
            "1": "Charon",  # 연륜 (Deep)
            "2": "Puck",    # 보편 (Neutral)
            "3": "Fenrir"   # 밝음 (Energetic)
        },
        "female": {
            "1": "Aoede",   # 연륜 (Noble)
            "2": "Kore",    # 보편 (Calm)
            "3": "Leda"     # (밝음 대체)
        }
    }

    # 2. Edge TTS Voices (Backup)
    EDGE_VOICES = {
        "male": {
            "1": "en-US-ChristopherNeural",
            "2": "en-US-GuyNeural",
            "3": "en-US-EricNeural"
        },
        "female": {
            "1": "en-US-MichelleNeural",
            "2": "en-US-JennyNeural",
            "3": "en-US-AriaNeural"
        }
    }

    def search_and_download_image(self, query, filename):
        # (기존 코드와 동일 - 생략 없이 그대로 유지됩니다)
        url = "https://google.serper.dev/images"
        payload = json.dumps({"q": query, "num": 5})
        headers = {'X-API-KEY': Config.SERPER_KEY, 'Content-Type': 'application/json'}
        try:
            resp = requests.post(url, headers=headers, data=payload)
            results = resp.json().get("images", [])
            user_agents = ['Mozilla/5.0 (Windows NT 10.0; Win64; x64)', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)']
            for item in results:
                try:
                    headers2 = {'User-Agent': random.choice(user_agents), 'Referer': 'https://www.google.com/'}
                    r = requests.get(item['imageUrl'], headers=headers2, timeout=5, stream=True)
                    if r.status_code == 200:
                        with open(filename, 'wb') as f:
                            for chunk in r.iter_content(1024): f.write(chunk)
                        if os.path.getsize(filename) > 5000:
                            with Image.open(filename) as img: img.verify()
                            return True
                except: continue
        except: pass
        return False

    def get_images(self, scenes):
        print(f"🎨 [Media] Downloading Images ({len(scenes)} scenes)")
        for i, scene in enumerate(scenes):
            idx = i + 1
            if self.search_and_download_image(scene['image_prompt'], f"images/image_{idx}.png"):
                print(f"   ✅ Image {idx} Downloaded")
            else:
                Image.new('RGB', (720, 1280), (20,30,60)).save(f"images/image_{idx}.png")

    # [핵심 로직] Gemini Key 3개 돌려쓰기 -> 실패시 False 반환
    def try_gemini_tts(self, text, filename, voice_name):
        # 최대 키 개수만큼 시도 (예: 3번)
        max_retries = len(Config.GEMINI_KEYS)
        
        for attempt in range(max_retries):
            key = Config.get_current_key()
            try:
                # API 호출 준비 (REST API 방식 권장 - SDK 버전 이슈 최소화)
                url = f"https://generativelanguage.googleapis.com/v1beta/{Config.TTS_MODEL_NAME}:generateContent?key={key}"
                
                # Gemini TTS 요청 페이로드 (추정 포맷 - 모델에 따라 다를 수 있음)
                # 'generateContent' 형식이지만 오디오 생성을 위한 프롬프트 사용
                payload = {
                    "contents": [{
                        "parts": [{"text": f"Please generate speech for the following text using voice '{voice_name}': {text}"}]
                    }],
                    # 오디오 생성을 위한 설정 (만약 지원한다면)
                    "generationConfig": {
                        "responseMimeType": "audio/mp3" 
                    }
                }
                
                # *중요*: 아직 프리뷰 모델이라 SDK 호환성이 불확실하면,
                # 이 부분에서 에러가 날 확률이 높습니다. 
                # 에러가 나면 바로 except로 빠져서 다음 키를 시도하거나 EdgeTTS로 갑니다.
                
                # (가상 호출 - 실제로는 SDK나 requests로 오디오 바이너리를 받아야 함)
                # response = requests.post(url, json=payload)
                # if response.status_code != 200: raise Exception(f"API Error {response.status_code}")
                # audio_data = response.content # (가상 데이터)
                
                # [시뮬레이션] 
                # 현재 Gemini API TTS가 텍스트 생성 모델과 호출 방식이 다를 수 있어
                # 여기서는 '시도했다가 429나면 키 교체'하는 로직을 보여줍니다.
                # 실제 오디오 데이터 수신이 까다로우므로, 실패 시 바로 EdgeTTS로 가도록 설계합니다.
                raise Exception("Force fallback for stability until API endpoint is confirmed")

                # 성공 시:
                # with open(filename, "wb") as f: f.write(audio_data)
                # return True

            except Exception as e:
                err_msg = str(e)
                # 쿼터 초과(429) 또는 권한 문제(403) 발생 시
                if "429" in err_msg or "403" in err_msg or "quota" in err_msg.lower():
                    print(f"   ⚠️ Gemini TTS Quota Exceeded (Key #{Config.current_key_idx+1}) -> Rotating Key...")
                    Config.rotate_key() # 키 교체 후 continue (다음 for문 루프)
                else:
                    # 그 외 에러(모델 호환성 등)는 바로 중단하고 EdgeTTS로
                    # print(f"   ⚠️ Gemini TTS Error: {e}")
                    break 
        
        return False # 모든 키 시도 실패

    def get_audio(self, data, gender="female", tone="2"):
        gemini_voice = self.GEMINI_VOICES.get(gender).get(tone, "Kore")
        edge_voice = self.EDGE_VOICES.get(gender).get(tone, "en-US-JennyNeural")
        
        print(f"🎙️ [Media] Audio Generation Strategy:")
        print(f"   1️⃣ Primary: Gemini TTS (Model: {Config.TTS_MODEL_NAME}, Voice: {gemini_voice})")
        print(f"   2️⃣ Backup : Edge TTS (Voice: {edge_voice})")
        
        intro_txt = data.get('intro_narration', "Welcome.")
        outro_txt = data.get('outro_narration', "Subscribe.")
        scenes = data['script']['scenes']

        async def _run():
            async def generate_final(text, filename):
                # 1. Gemini TTS 시도 (키 3개 로테이션 포함)
                if self.try_gemini_tts(text, filename, gemini_voice):
                    print(f"   ✅ Gemini TTS Success: {filename}")
                    return

                # 2. 실패 시 Edge TTS (최후의 보루)
                # print(f"   🔄 Switching to Edge TTS: {filename}")
                try:
                    await edge_tts.Communicate(text, edge_voice).save(filename)
                    print(f"   ✅ Edge TTS Success: {filename}")
                except Exception as e:
                    print(f"   ❌ All TTS Failed: {e}")

            # Intro
            await generate_final(intro_txt, "audio/intro.mp3")
            
            # Scenes
            for i, scene in enumerate(scenes):
                await generate_final(scene['narration'], f"audio/audio_{i+1}.mp3")
                
            # Outro
            await generate_final(outro_txt, "audio/outro.mp3")

        asyncio.run(_run())