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
        os.makedirs("videos", exist_ok=True)
        os.makedirs("audio", exist_ok=True)
        
        if os.path.exists("google_key.json"):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "google_key.json"
            self.has_gcp = True
            print("✅ [Media] Google Cloud TTS Ready.")
        else:
            self.has_gcp = False
            print("⚠️ [Media] 'google_key.json' not found. GCP TTS disabled.")

    GEMINI_VOICES = {
        "male": {"1": "Charon", "2": "Puck", "3": "Fenrir"},
        "female": {"1": "Aoede", "2": "Kore", "3": "Leda"}
    }
    EDGE_VOICES = {
        "male": {"1": "en-US-ChristopherNeural", "2": "en-US-GuyNeural", "3": "en-US-EricNeural"},
        "female": {"1": "en-US-MichelleNeural", "2": "en-US-JennyNeural", "3": "en-US-AriaNeural"}
    }

    def _download_logic(self, query, filename, min_width=800):
        url = "https://google.serper.dev/images"
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
                if any(k in image_url.lower() for k in skip_keywords): continue

                try:
                    headers2 = {'User-Agent': random.choice(user_agents), 'Referer': 'https://www.google.com/', 'Accept': 'image/*'}
                    r = requests.get(image_url, headers=headers2, timeout=3)
                    
                    if r.status_code == 200:
                        file_content = r.content
                        try:
                            img = Image.open(io.BytesIO(file_content))
                            if img.mode != 'RGB': img = img.convert('RGB')
                            w, h = img.size
                            if w < min_width: continue
                            if w <= h: continue 
                            img.save(filename, format='PNG')
                            if os.path.exists(filename) and os.path.getsize(filename) > 1000:
                                print(f"   ✅ [Image] Saved: {filename}")
                                return True
                        except: continue
                except: continue
        except: pass
        return False

    def search_and_download_image(self, query, filename):
        if self._download_logic(query, filename, min_width=800): return True
        short_query = " ".join(query.split()[:4]) + " news"
        if self._download_logic(short_query, filename, min_width=600): return True
        return False

    def get_images(self, scenes):
        print(f"🎨 [Media] Downloading Images for Shorts...")
        for i, scene in enumerate(scenes):
            idx = i + 1
            if not self.search_and_download_image(scene['image_prompt'], f"images/image_{idx}.png"):
                 Image.new('RGB', (1280, 720), (20,30,60)).save(f"images/image_{idx}.png")

    # =========================================================================
    # [UPGRADED] 1.5 비디오 다운로드 (고화질 검색어 추가)
    # =========================================================================
    def search_and_download_video(self, query, filename, min_duration=5):
        if not Config.PEXELS_KEY:
            print("⚠️ Pexels Key missing.")
            return False

        # [핵심] 고화질 검색어 자동 추가 (품질 향상)
        enhanced_query = f"{query} 4k cinematic photorealistic high quality"
        print(f"   🎥 [Pexels] Searching: '{enhanced_query}'")
        
        url = "https://api.pexels.com/videos/search"
        headers = {"Authorization": Config.PEXELS_KEY}
        params = {"query": enhanced_query, "orientation": "landscape", "per_page": 5, "size": "medium"}

        try:
            r = requests.get(url, headers=headers, params=params, timeout=10)
            data = r.json()
            videos = data.get('videos', [])
            
            if not videos: return False

            target_url = None
            for video in videos:
                if video['duration'] < min_duration: continue
                files = video.get('video_files', [])
                # HD 우선 (1280 이상)
                hd = [f for f in files if f['width'] >= 1280 and f['quality'] == 'hd']
                if hd: target_url = hd[0]['link']; break
                # 차선책
                sd = [f for f in files if f['width'] >= 960]
                if sd: target_url = sd[0]['link']; break
            
            if not target_url and videos:
                target_url = videos[0]['video_files'][0]['link']

            if target_url:
                v_content = requests.get(target_url, timeout=30).content
                with open(filename, 'wb') as f: f.write(v_content)
                if os.path.exists(filename) and os.path.getsize(filename) > 1000:
                    print(f"      ✅ [Video] Saved: {filename}")
                    return True
        except Exception as e:
            print(f"   ❌ Pexels Error: {e}")
        return False

    def get_mixed_media(self, scenes):
        print(f"🎨 [Media] Downloading Mixed Assets (Video + Image)...")
        
        for i, scene in enumerate(scenes):
            idx = i + 1
            v_type = scene.get('visual_type', 'image') 
            prompt = scene.get('visual_prompt', scene.get('image_prompt', 'news'))
            
            if v_type == 'video':
                v_filename = f"videos/video_{idx}.mp4"
                if self.search_and_download_video(prompt, v_filename):
                    continue 
                else:
                    print(f"      ⚠️ Video failed. Fallback to Image for Scene {idx}")
                    v_type = 'image'

            if v_type == 'image':
                i_filename = f"images/image_{idx}.png"
                if not self.search_and_download_image(prompt, i_filename):
                     Image.new('RGB', (1920, 1080), (20,30,60)).save(i_filename)

    def try_gcp_tts(self, text, filename, voice_name="en-US-Neural2-F"):
        if not self.has_gcp: return False
        try:
            client = texttospeech.TextToSpeechClient()
            input_text = texttospeech.SynthesisInput(text=text)
            voice = texttospeech.VoiceSelectionParams(language_code="en-US", name=voice_name)
            audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3, speaking_rate=1.1)
            response = client.synthesize_speech(input=input_text, voice=voice, audio_config=audio_config)
            with open(filename, "wb") as out: out.write(response.audio_content)
            if os.path.exists(filename) and os.path.getsize(filename) > 0: return True
        except Exception as e: print(f"   ⚠️ GCP TTS Failed: {e}")
        return False

    def try_gemini_tts(self, text, filename, voice_name):
        max_retries = len(Config.GEMINI_KEYS)
        for attempt in range(max_retries):
            key = Config.get_current_key()
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/{Config.TTS_MODEL_NAME}:generateContent?key={key}"
                payload = {
                    "contents": [{"parts": [{"text": text}]}],
                    "generationConfig": {"responseModalities": ["AUDIO"],"speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice_name}}}}
                }
                response = requests.post(url, json=payload, timeout=10)
                if response.status_code == 200:
                    data = response.json()['candidates'][0]['content']['parts'][0]['inlineData']['data']
                    with open(filename, "wb") as f: f.write(base64.b64decode(data))
                    return True
                elif response.status_code == 429: Config.rotate_key()
            except: Config.rotate_key()
        return False

    async def try_edge_tts(self, text, filename, voice_name):
        try:
            communicate = edge_tts.Communicate(text, voice_name, rate="+10%")
            await communicate.save(filename)
            return True
        except: return False

    def get_audio(self, data, gender="female", tone="2"):
        gcp_voice = "en-US-Neural2-F" if gender == "female" else "en-US-Neural2-D" 
        gemini_voice = self.GEMINI_VOICES.get(gender).get(tone, "Kore")
        edge_voice = self.EDGE_VOICES.get(gender).get(tone, "en-US-JennyNeural")
        
        print(f"🎙️ [Media] Audio Strategy: 1.GCP -> 2.Gemini -> 3.Edge")

        intro_txt = data.get('intro_narration', "").replace("*", "")
        outro_txt = data.get('outro_narration', "").replace("*", "")
        scenes = data['script']['scenes']

        async def _run():
            async def generate_final(text, filename):
                if not text: return
                if self.try_gcp_tts(text, filename, gcp_voice): return
                if self.try_gemini_tts(text, filename, gemini_voice): return
                await self.try_edge_tts(text, filename, edge_voice)

            if intro_txt: await generate_final(intro_txt, "audio/intro.mp3")
            for i, scene in enumerate(scenes):
                clean_narration = scene['narration'].replace("*", "")
                await generate_final(clean_narration, f"audio/audio_{i+1}.mp3")
            if outro_txt: await generate_final(outro_txt, "audio/outro.mp3")

        asyncio.run(_run())