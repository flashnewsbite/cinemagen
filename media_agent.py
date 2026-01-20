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

    def search_and_download_image(self, query, filename):
        """Serper 이미지 검색 + 봇 차단 우회 다운로드"""
        url = "https://google.serper.dev/images"
        payload = json.dumps({"q": query, "num": 5})
        headers = {'X-API-KEY': Config.SERPER_KEY, 'Content-Type': 'application/json'}
        
        try:
            resp = requests.post(url, headers=headers, data=payload)
            results = resp.json().get("images", [])
            
            # [핵심] 이미지 다운로드용 위장 헤더 리스트
            user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/119.0.0.0 Safari/537.36'
            ]

            for item in results:
                image_url = item['imageUrl']
                try:
                    # [핵심] 구글에서 검색해서 클릭한 척 위장 (Referer 속이기)
                    download_headers = {
                        'User-Agent': random.choice(user_agents),
                        'Referer': 'https://www.google.com/' 
                    }
                    
                    # stream=True로 설정하여 대용량 이미지도 안전하게 처리
                    r = requests.get(image_url, headers=download_headers, timeout=5, stream=True)
                    
                    if r.status_code == 200:
                        with open(filename, 'wb') as f:
                            for chunk in r.iter_content(1024):
                                f.write(chunk)
                        
                        # 파일이 너무 작거나(깨진 파일), 다운로드가 덜 된 경우 체크
                        if os.path.getsize(filename) > 5000: # 5KB 이상만 인정
                            try:
                                # 이미지 파일이 진짜 열리는지 최종 확인 (Pillow)
                                with Image.open(filename) as img:
                                    img.verify() 
                                return True
                            except:
                                continue # 이미지 깨짐 -> 다음 후보로
                except: 
                    continue # 다운로드 실패 -> 다음 후보로
        except: pass
        return False

    def get_images(self, scenes):
        print(f"🎨 [Media] 이미지 수집 시작 ({len(scenes)}장)")
        for i, scene in enumerate(scenes):
            idx = i + 1
            prompt = scene['image_prompt']
            filename = f"images/image_{idx}.png"
            
            # 1. 이미지 검색 및 다운로드
            if self.search_and_download_image(prompt, filename):
                print(f"   ✅ Scene {idx}: 이미지 확보 완료")
            else:
                print(f"   ⚠️ Scene {idx}: 다운로드 실패 -> 기본 이미지 사용")
                # 실패 시 검은 화면 대신 기본 그래픽 생성
                img = Image.new('RGB', (720, 1280), color=(20, 30, 60))
                img.save(filename)

    def get_audio(self, scenes):
        print(f"🎙️ [Media] 성우 녹음 시작 ({len(scenes)}문장)")
        voice = "ko-KR-SunHiNeural"
        
        async def _run():
            for i, scene in enumerate(scenes):
                idx = i + 1
                text = scene['narration']
                filename = f"audio/audio_{idx}.mp3"
                try:
                    communicate = edge_tts.Communicate(text, voice)
                    await communicate.save(filename)
                    print(f"   ✅ Audio {idx} 완료")
                except Exception as e:
                    print(f"   ❌ Audio {idx} 실패: {e}")
        
        asyncio.run(_run())