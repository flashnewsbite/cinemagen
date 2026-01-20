import os
import json
import requests
import edge_tts
import asyncio
from PIL import Image
from config import Config
import random

class MediaAgent:
    def __init__(self):
        os.makedirs("images", exist_ok=True)
        os.makedirs("audio", exist_ok=True)

    # Gemini Voices
    GEMINI_VOICES = {
        "male": {"1": "Charon", "2": "Puck", "3": "Fenrir"},
        "female": {"1": "Aoede", "2": "Kore", "3": "Leda"}
    }
    # Edge TTS Voices
    EDGE_VOICES = {
        "male": {"1": "en-US-ChristopherNeural", "2": "en-US-GuyNeural", "3": "en-US-EricNeural"},
        "female": {"1": "en-US-MichelleNeural", "2": "en-US-JennyNeural", "3": "en-US-AriaNeural"}
    }

    def search_and_download_image(self, query, filename):
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

    def try_gemini_tts(self, text, filename, voice_name):
        """Gemini TTS 시도 (속도 조절 불가, 1.0x)"""
        max_retries = len(Config.GEMINI_KEYS)
        
        for attempt in range(max_retries):
            key = Config.get_current_key()
            try:
                # Gemini REST API 호출
                url = f"https://generativelanguage.googleapis.com/v1beta/{Config.TTS_MODEL_NAME}:generateContent?key={key}"
                
                payload = {
                    "contents": [{
                        "parts": [{"text": f"Please read this text clearly: {text}"}]
                    }],
                    "generationConfig": {
                        "responseMimeType": "audio/mp3",
                        "speechConfig": {
                            "voiceConfig": {
                                "prebuiltVoiceConfig": {
                                    "voiceName": voice_name
                                }
                            }
                        }
                    }
                }
                
                # REST API 요청
                response = requests.post(url, json=payload, timeout=10)
                
                # 쿼터 초과(429) 체크
                if response.status_code == 429:
                    print(f"   ⚠️ Gemini TTS Quota Limit (Key #{Config.current_key_idx+1}) -> Rotating...")
                    Config.rotate_key()
                    continue
                
                if response.status_code != 200:
                    # 기타 에러면 다음 키 시도 없이 바로 Edge로 넘어갈지 결정
                    # 여기서는 안전하게 Edge로 넘기기 위해 Exception 발생
                    raise Exception(f"API Error {response.status_code}: {response.text}")

                # 오디오 데이터 디코딩 (Base64 -> Binary)
                # *주의* Gemini TTS 응답 포맷은 모델 버전에 따라 다를 수 있음
                # 현재 Preview 기준: response.json()['candidates'][0]['content']['parts'][0]['inlineData']['data']
                try:
                    resp_json = response.json()
                    b64_audio = resp_json['candidates'][0]['content']['parts'][0]['inlineData']['data']
                    import base64
                    audio_data = base64.b64decode(b64_audio)
                    
                    with open(filename, "wb") as f:
                        f.write(audio_data)
                    return True
                except Exception as parse_err:
                    raise Exception(f"Parse Error: {parse_err}")

            except Exception as e:
                # print(f"   ⚠️ Gemini TTS Attempt Failed: {e}")
                if "429" in str(e) or "Quota" in str(e):
                    Config.rotate_key()
                else:
                    # 키 문제가 아닌 다른 문제면 바로 반복문 종료하고 Edge로
                    break
        
        return False

    def get_audio(self, data, gender="female", tone="2"):
        gemini_voice = self.GEMINI_VOICES.get(gender).get(tone, "Kore")
        edge_voice = self.EDGE_VOICES.get(gender).get(tone, "en-US-JennyNeural")
        
        # Edge TTS용 속도 (Gemini는 적용 불가)
        edge_rate = "+20%"
        
        print(f"🎙️ [Media] Audio Generation Strategy:")
        print(f"   1️⃣ Primary: Gemini TTS (1.0x Speed, Voice: {gemini_voice})")
        print(f"   2️⃣ Backup : Edge TTS (1.2x Speed, Voice: {edge_voice})")

        intro_txt = data.get('intro_narration', "Welcome.")
        outro_txt = data.get('outro_narration', "Subscribe.")
        scenes = data['script']['scenes']

        async def _run():
            async def generate_final(text, filename):
                # 1. Gemini 시도
                if self.try_gemini_tts(text, filename, gemini_voice):
                    print(f"   ✅ Gemini TTS Success (1.0x): {filename}")
                    return

                # 2. 실패 시 Edge TTS (1.2배속 적용)
                try:
                    communicate = edge_tts.Communicate(text, edge_voice, rate=edge_rate)
                    await communicate.save(filename)
                    print(f"   ✅ Edge TTS Success (1.2x): {filename}")
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