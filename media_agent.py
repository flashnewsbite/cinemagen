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
    # 1. 이미지 다운로드 (재시도 로직 추가)
    # =========================================================================
    def _download_logic(self, query, filename, min_width=800):
        """
        실제 검색 및 다운로드를 수행하는 내부 함수
        min_width: 최소 너비 제한 (1차 시도 800, 2차 시도 600)
        """
        url = "https://google.serper.dev/images"
        # [상향] 검색 후보를 15개 -> 30개로 대폭 늘림 (필터 탈락 방지)
        payload = json.dumps({"q": query, "num": 30}) 
        headers = {'X-API-KEY': Config.SERPER_KEY, 'Content-Type': 'application/json'}
        skip_keywords = ["stock", "getty", "alamy", "shutterstock", "istock", "dreamstime", "123rf", "depositphotos"]

        try:
            resp = requests.post(url, headers=headers, data=payload)
            results = resp.json().get("images", [])
            user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'
            ]
            
            for item in results:
                image_url = item['imageUrl']
                if any(k in image_url.lower() for k in skip_keywords):
                    # 워터마크 의심되면 로그 없이 조용히 스킵
                    continue

                try:
                    headers2 = {'User-Agent': random.choice(user_agents), 'Referer': 'https://www.google.com/', 'Accept': 'image/*'}
                    r = requests.get(image_url, headers=headers2, timeout=3)
                    
                    if r.status_code == 200:
                        file_content = r.content
                        try:
                            img = Image.open(io.BytesIO(file_content))
                            if img.mode != 'RGB': img = img.convert('RGB')
                            w, h = img.size
                            
                            # [유동적 필터] 인자로 받은 최소 너비 사용
                            if w < min_width: continue
                            # [필수] 가로형이 아니면 스킵 (영상 비율 문제)
                            if w <= h: continue
                            
                            img.save(filename, format='PNG')
                            if os.path.exists(filename) and os.path.getsize(filename) > 1000:
                                print(f"   ✅ [Saved] {w}x{h} (Query: {query[:15]}...)")
                                return True
                        except: continue
                except: continue
        except: pass
        return False

    def search_and_download_image(self, query, filename):
        """
        1차 시도 실패 시 검색어를 단순화하여 2차 시도를 하는 로직
        """
        # [Attempt 1] 원래 쿼리, 고화질(800px)
        if self._download_logic(query, filename, min_width=800):
            return True
        
        # [Attempt 2] 실패 시 -> 쿼리 단순화 + 기준 완화(600px)
        # 예: "Detailed view of Trump at Davos forum" -> "Trump Davos forum"
        short_query = " ".join(query.split()[:4]) + " news" # 앞 4단어 + news 키워드 조합
        print(f"   ⚠️ Primary search failed. Retrying with backup query: '{short_query}'")
        
        if self._download_logic(short_query, filename, min_width=600):
            return True

        return False

    def get_images(self, scenes):
        print(f"🎨 [Media] Downloading Images (Smart Retry Enabled)...")
        for i, scene in enumerate(scenes):
            idx = i + 1
            # 이미지 다운로드 시도
            success = self.search_and_download_image(scene['image_prompt'], f"images/image_{idx}.png")
            
            # 2차 시도까지 전부 실패했을 경우 (정말 드문 경우)
            if not success:
                print(f"   🚨 Scene {idx} Critical Fail. Searching Generic 'News' image...")
                # 최후의 수단: 그냥 'Global News'라는 아주 일반적인 키워드로 검색
                if not self._download_logic("Global World News Headlines", f"images/image_{idx}.png", min_width=500):
                     # 이것마저 안되면 어쩔 수 없이 검은 화면 (프로그램 에러 방지용)
                     Image.new('RGB', (1280, 720), (20,30,60)).save(f"images/image_{idx}.png")

    # =========================================================================
    # 2. TTS 엔진들 (속도 1.1배 적용)
    # =========================================================================
    
    # [Option A] Google Cloud TTS (1순위: 가성비 Neural2)
    def try_gcp_tts(self, text, filename, voice_name="en-US-Neural2-F"):
        if not self.has_gcp: return False
        try:
            client = texttospeech.TextToSpeechClient()
            input_text = texttospeech.SynthesisInput(text=text)
            voice = texttospeech.VoiceSelectionParams(language_code="en-US", name=voice_name)
            
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=1.1 
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
        gcp_voice = "en-US-Neural2-F" if gender == "female" else "en-US-Neural2-D" 
        gemini_voice = self.GEMINI_VOICES.get(gender).get(tone, "Kore")
        edge_voice = self.EDGE_VOICES.get(gender).get(tone, "en-US-JennyNeural")
        
        print(f"🎙️ [Media] Audio Strategy (Neural2 / 1.1x): 1.GCP -> 2.Gemini -> 3.Edge")

        intro_txt = data.get('intro_narration', "Welcome.")
        outro_txt = data.get('outro_narration', "Subscribe.")
        scenes = data['script']['scenes']

        async def _run():
            async def generate_final(text, filename):
                if self.try_gcp_tts(text, filename, gcp_voice):
                    print(f"   ✅ GCP TTS (Neural2): {filename}")
                    return

                print(f"   ⚠️ GCP failed. Switching to Gemini...")
                if self.try_gemini_tts(text, filename, gemini_voice):
                    print(f"   ✅ Gemini TTS: {filename}")
                    return
                
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