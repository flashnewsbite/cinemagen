import os
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# ====================================================
# 🟥 YouTube API Uploader (Playlist Fixed)
# ====================================================

BASE_DIR = os.getcwd()
CLIENT_SECRETS_FILE = os.path.join(BASE_DIR, "credentials", "client_secret.json")
TOKEN_FILE = os.path.join(BASE_DIR, "credentials", "token.json")

# [중요] 권한 설정: 업로드 + 계정 관리(재생목록 추가용)
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl" 
]

# 👇 사용자님이 제공한 Playlist ID (매핑 강화)
PLAYLIST_IDS = {
    # World News
    "world": "PLf2sQtl-qEjOuz7-HGAx2VX6d0hCEAZO2",
    "us": "PLf2sQtl-qEjOuz7-HGAx2VX6d0hCEAZO2",
    
    # Entertainment
    "ent": "PLf2sQtl-qEjOy_xcnwBL7UDAXndx6meVv",
    "entertainment": "PLf2sQtl-qEjOy_xcnwBL7UDAXndx6meVv",
    
    # Finance
    "fin": "PLf2sQtl-qEjNbj6I14zWuaxUv2zwKtRho",
    "finance": "PLf2sQtl-qEjNbj6I14zWuaxUv2zwKtRho",
    
    # Tech & Science
    "tech": "PLf2sQtl-qEjNiVDyYYOtZcIelIvWQXDjw",
    "science": "PLf2sQtl-qEjNiVDyYYOtZcIelIvWQXDjw",
    
    # Sports
    "sport": "PLf2sQtl-qEjODiHT7A-xw1FNJBAi0DRno",
    "sports": "PLf2sQtl-qEjODiHT7A-xw1FNJBAi0DRno",
    
    # Art
    "art": "PLf2sQtl-qEjOGRMZSb-q-CSwvBFUulPx1",
    "arts": "PLf2sQtl-qEjOGRMZSb-q-CSwvBFUulPx1"
}

def get_authenticated_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRETS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    return googleapiclient.discovery.build("youtube", "v3", credentials=creds)

def add_video_to_playlist(youtube, video_id, playlist_id):
    """업로드된 영상을 재생목록에 추가"""
    print(f"      📋 Attempting to add video {video_id} to playlist {playlist_id}...")
    try:
        request = youtube.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": playlist_id,
                    "resourceId": {
                        "kind": "youtube#video",
                        "videoId": video_id
                    }
                }
            }
        )
        response = request.execute()
        print(f"      ✅ Success! Added to playlist: {response['snippet']['title']}")
    except Exception as e:
        print(f"      ❌ Failed to add to playlist. Reason: {e}")
        print("      (Tip: Did you delete token.json and re-login with ALL checkboxes checked?)")

def upload_video(video_path, category="ent", title="Video", description="#shorts"):
    print(f"🚀 [YouTube API] Uploading: {title[:30]}...")
    print(f"      📝 Description Length: {len(description)} chars") # 설명 길이 확인용

    youtube = get_authenticated_service()

    # YouTube 카테고리 ID (24:Ent, 25:News, 28:Tech, 17:Sport)
    cat_lower = category.lower()
    if cat_lower == "world": cid = "25"
    elif cat_lower in ["ent", "entertainment"]: cid = "24"
    elif cat_lower in ["fin", "finance"]: cid = "25"
    elif cat_lower in ["tech", "science"]: cid = "28"
    elif cat_lower in ["sport", "sports"]: cid = "17"
    elif cat_lower in ["art", "arts"]: cid = "1"
    else: cid = "24"

    body = {
        "snippet": {
            "title": title,
            "description": description, # 여기가 핵심입니다.
            "tags": ["shorts", "news", "AI", category],
            "categoryId": cid
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False
        }
    }

    try:
        # 1. 영상 업로드
        request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=googleapiclient.http.MediaFileUpload(video_path, chunksize=-1, resumable=True)
        )
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"      📤 Uploading... {int(status.progress() * 100)}%")
        
        video_id = response.get('id')
        print(f"      ✅ Upload Complete! Video ID: {video_id}")

        # 2. 재생목록 추가
        # 입력된 카테고리를 키로 사용하여 ID 조회
        target_playlist_id = PLAYLIST_IDS.get(cat_lower)
        
        if target_playlist_id:
            add_video_to_playlist(youtube, video_id, target_playlist_id)
        else:
            print(f"      ℹ️ No playlist ID found for category '{cat_lower}'. Skipping playlist.")

        return True

    except Exception as e:
        print(f"❌ [YouTube API] Error: {e}")
        return False