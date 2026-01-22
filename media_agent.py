import os
import json
import requests
import edge_tts
import asyncio
from PIL import Image
from config import Config
import random
import base64
import io
# Google Cloud TTS 라이브러리
from google.cloud import texttospeech

class MediaAgent:
    def __init__(self):
        os.makedirs("images", exist_ok=True)
        os.makedirs("audio", exist_ok=True)
        
        # [설정] Google Cloud 인증 키 연결
        if os.path.exists("google_key.json"):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "google_key.json"
            self.has_gcp = True
            print("✅ [Media] Google Cloud TTS Ready.")
        else:
            self.has_gcp = False
            print("⚠️ [Media] 'google_key.json' not found. GCP TTS disabled.")

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

    # =========================================================================
    # 1. 이미지 다운로드 (스마트 필터링 유지)
    # =========================================================================
    def search_and_download_image(self, query, filename):
        url = "https://google.serper.dev/images"
        payload = json.dumps({"q": query, "num": 15}) 
        headers = {'X-API-KEY': Config.SERPER_KEY, 'Content-Type': 'application/json'}
        skip_keywords = ["stock", "getty", "alamy", "shutterstock", "istock", "dreamstime", "123rf", "depositphotos"]

        try:
            resp = requests.post(url, headers=headers, data=payload)
            results = resp.json().get("images", [])
            user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            ]
            
            for item in results:
                image_url = item['imageUrl']
                if any(k in image_url.lower() for k in skip_keywords):
                    print(f"   🚫 [Skip] Watermark: {image_url[:30]}...")
                    continue

                try:
                    headers2 = {'User-Agent': random.choice(user_agents), 'Referer': 'https://www.google.com/', 'Accept': 'image/*'}
                    r = requests.get(image_url, headers=headers2, timeout=5)
                    
                    if r.status_code == 200:
                        file_content = r.content
                        try:
                            img = Image.open(io.BytesIO(file_content))
                            if img.mode != 'RGB': img = img.convert('RGB')
                            w, h = img.size
                            
                            if w < 800:
                                print(f"   ⚠️ [Skip] Low Res: {w}x{h}")
                                continue
                            if w <= h:
                                print(f"   ⚠️ [Skip] Portrait: {w}x{h}")
                                continue
                            
                            img.save(filename, format='PNG')
                            if os.path.exists(filename) and os.path.getsize(filename) > 1000:
                                print(f"   ✅ [Saved] {w}x{h}")
                                return True
                        except: continue
                except: continue
        except: pass
        return False

    def get_images(self, scenes):
        print(f"🎨 [Media] Downloading Images...")
        for i, scene in enumerate(scenes):
            idx = i + 1
            if not self.search_and_download_image(scene['image_prompt'], f"images/image_{idx}.png"):
                print(f"   ⚠️ Scene {idx} Failed. Placeholder used.")
                Image.new('RGB', (1280, 720), (20,30,60)).save(f"images/image_{idx}.png")

    # =========================================================================
    # 2. TTS 엔진들 (속도 1.2배 적용)
    # =========================================================================
    
    # [Option A] Google Cloud TTS (1순위: 고품질)
    def try_gcp_tts(self, text, filename, voice_name="en-US-Journey-F"):
        if not self.has_gcp: return False
        try:
            client = texttospeech.TextToSpeechClient()
            input_text = texttospeech.SynthesisInput(text=text)
            voice = texttospeech.VoiceSelectionParams(language_code="en-US", name=voice_name)
            
            # [수정] speaking_rate=1.2 (1.2배 속도)
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=1.2 
            )
            
            response = client.synthesize_speech(input=input_text, voice=voice, audio_config=audio_config)
            
            with open(filename, "wb") as out:
                out.write(response.audio_content)
            
            if os.path.exists(filename) and os.path.getsize(filename) > 0:
                return True
        except Exception as e:
            print(f"   ⚠️ GCP TTS Failed: {e}")
        return False

    # [Option B] Gemini TTS (2순위: 백업)
    def try_gemini_tts(self, text, filename, voice_name):
        max_retries = len(Config.GEMINI_KEYS)
        for attempt in range(max_retries):
            key = Config.get_current_key()
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/{Config.TTS_MODEL_NAME}:generateContent?key={key}"
                payload = {
                    "contents": [{"parts": [{"text": text}]}],
                    "generationConfig": {
                        "responseModalities": ["AUDIO"],
                        "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice_name}}}
                    }
                }
                response = requests.post(url, json=payload, timeout=10)
                
                if response.status_code == 429:
                    print(f"   ⚠️ Gemini Quota (Key #{Config.current_key_idx+1}) -> Rotating...")
                    Config.rotate_key(); continue
                
                if response.status_code == 200:
                    data = response.json()['candidates'][0]['content']['parts'][0]['inlineData']['data']
                    with open(filename, "wb") as f: f.write(base64.b64decode(data))
                    return True
            except Exception:
                Config.rotate_key()
        return False

    # [Option C] Edge TTS (3순위: 최후의 보루)
    async def try_edge_tts(self, text, filename, voice_name):
        try:
            # [수정] rate="+10%" (1.1배 속도)
            communicate = edge_tts.Communicate(text, voice_name, rate="+10%")
            await communicate.save(filename)
            if os.path.exists(filename) and os.path.getsize(filename) > 0:
                return True
        except Exception as e:
            print(f"   ⚠️ Edge TTS Failed: {e}")
        return False

    # =========================================================================
    # 3. 통합 오디오 생성 (우선순위: GCP -> Gemini -> Edge)
    # =========================================================================
    def get_audio(self, data, gender="female", tone="2"):
        # 목소리 설정
        gcp_voice = "en-US-Journey-F" if gender == "female" else "en-US-Journey-D" 
        gemini_voice = self.GEMINI_VOICES.get(gender).get(tone, "Kore")
        edge_voice = self.EDGE_VOICES.get(gender).get(tone, "en-US-JennyNeural")
        
        print(f"🎙️ [Media] Audio Strategy (Speed 1.2x): 1.GCP -> 2.Gemini -> 3.Edge")

        intro_txt = data.get('intro_narration', "Welcome.")
        outro_txt = data.get('outro_narration', "Subscribe.")
        scenes = data['script']['scenes']

        async def _run():
            async def generate_final(text, filename):
                # 1순위: GCP TTS (최고품질)
                if self.try_gcp_tts(text, filename, gcp_voice):
                    print(f"   ✅ GCP TTS: {filename}")
                    return

                # 2순위: Gemini TTS (GCP 실패 시)
                print(f"   ⚠️ GCP failed. Switching to Gemini...")
                if self.try_gemini_tts(text, filename, gemini_voice):
                    print(f"   ✅ Gemini TTS: {filename}")
                    return
                
                # 3순위: Edge TTS (최후의 수단)
                print(f"   ⚠️ Gemini failed. Switching to Edge...")
                if await self.try_edge_tts(text, filename, edge_voice):
                    print(f"   ✅ Edge TTS: {filename}")
                    return

                print(f"   ❌ All TTS Failed for {filename}")

            await generate_final(intro_txt, "audio/intro.mp3")
            for i, scene in enumerate(scenes):
                await generate_final(scene['narration'], f"audio/audio_{i+1}.mp3")
            await generate_final(outro_txt, "audio/outro.mp3")

        asyncio.run(_run())