import google.generativeai as genai
import os
from dotenv import load_dotenv

# 1. .env 파일 로드
load_dotenv()

def check_available_models():
    # .env 파일에서 키 찾기 (1번 키부터 5번 키까지 순서대로 확인)
    api_key = os.getenv("GEMINI_API_KEY")
    
    # 1번 키가 없으면 2~5번 키도 찾아봄
    if not api_key:
        for i in range(2, 6):
            key_name = f"GEMINI_API_KEY_{i}" # 혹은 .env 저장 방식에 따라 수정
            temp = os.getenv(key_name)
            if temp:
                api_key = temp
                print(f"ℹ️ {key_name}를 사용합니다.")
                break
    
    if not api_key:
        print("❌ 오류: .env 파일에서 API Key를 찾을 수 없습니다.")
        print("   팁: .env 파일이 같은 폴더에 있는지 확인해주세요.")
        return

    print(f"🔍 API Key 로드 완료 ({api_key[:5]}*****...)")
    
    try:
        genai.configure(api_key=api_key)
        
        print("📡 구글 서버에 사용 가능한 모델 목록 요청 중...")
        available_models = []
        
        # 모델 리스트 조회
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"   ✅ 발견: {m.name}")
                available_models.append(m.name)
        
        if not available_models:
            print("⚠️ 사용 가능한 모델을 찾지 못했습니다. (키 권한 또는 지역 제한 확인 필요)")
            return

        # 2. 파일로 저장
        output_file = "models_list.txt"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("=== Available Gemini Models ===\n")
            for model_name in available_models:
                f.write(f"{model_name}\n")
        
        print("\n" + "="*40)
        print(f"🎉 성공! '{output_file}' 파일에 저장되었습니다.")
        print("="*40)
        
        # 3. 모델 이름 분석 및 추천
        print("\n[내 키로 쓸 수 있는 최신 모델]")
        
        # 1.5 Flash 확인
        if "models/gemini-1.5-flash" in available_models:
            print("⚡ gemini-1.5-flash (추천: 가장 빠름)")
        elif "models/gemini-1.5-flash-001" in available_models:
            print("⚡ gemini-1.5-flash-001 (추천: 가장 빠름)")
            
        # 1.5 Pro 확인
        if "models/gemini-1.5-pro" in available_models:
            print("🧠 gemini-1.5-pro (고지능)")
        elif "models/gemini-1.5-pro-001" in available_models:
             print("🧠 gemini-1.5-pro-001 (고지능)")

    except Exception as e:
        print(f"\n❌ 에러 발생: {e}")
        print("👉 팁: 'pip install python-dotenv' 가 설치되어 있는지 확인해보세요.")

if __name__ == "__main__":
    check_available_models()