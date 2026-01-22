import os
from google.cloud import texttospeech

# 1. 서비스 계정 키 환경변수 설정
# (다운로드 받은 JSON 파일명을 정확히 입력하세요)
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "google_key.json"

def run_quickstart():
    # 2. 클라이언트 인스턴스 생성
    client = texttospeech.TextToSpeechClient()

    # 3. 변환할 텍스트 입력
    text_input = texttospeech.SynthesisInput(text="Hello! This is a test of Google Cloud Text to Speech. The quality is amazing.")

    # 4. 목소리 설정
    # language_code: 언어 (en-US, ko-KR 등)
    # name: 구체적인 목소리 모델 (WaveNet, Neural2, Studio 등)
    # 예시: 'en-US-Journey-F' (매우 자연스러운 최신 모델), 'en-US-Studio-M'
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        name="en-US-Journey-F" 
    )

    # 5. 오디오 파일 설정 (MP3)
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )

    # 6. API 호출 (음성 합성 요청)
    print("📢 requesting speech synthesis...")
    response = client.synthesize_speech(
        input=text_input, voice=voice, audio_config=audio_config
    )

    # 7. 파일 저장
    filename = "output_gcp.mp3"
    with open(filename, "wb") as out:
        out.write(response.audio_content)
        print(f"✅ Audio content written to file '{filename}'")

if __name__ == "__main__":
    try:
        run_quickstart()
    except Exception as e:
        print(f"❌ Error: {e}")
        print("💡 팁: google_key.json 경로가 맞는지, API가 활성화되었는지 확인하세요.")