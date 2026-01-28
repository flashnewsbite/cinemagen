import os
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# ====================================================
# 🟥 YouTube API Uploader (Health Playlist Integrated)
# ====================================================

BASE_DIR = os.getcwd()
CLIENT_SECRETS_FILE = os.path.join(BASE_DIR, "credentials", "client_secret.json")
TOKEN_FILE = os.path.join(BASE_DIR, "credentials", "token.json")

# [중요] 권한 설정: 업로드 + 계정 관리(재생목록 추가용)
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl" 
]

# 👇 사용자님이 제공한 Playlist ID (Health 추가 완료)
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
    "arts": "PLf2sQtl-qEjOGRMZSb-q-CSwvBFUulPx1",

    # [NEW] Health Playlist (업데이트됨)
    "health": "PLf2sQtl-qEjPXJ-rEHlZY4IlRypJVt2j4"
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
        print("      (Tip: Check if the Playlist ID is correct & token has permissions)")

def upload_video(video_path, category="ent", title="Video", description="#shorts"):
    print(f"🚀 [YouTube API] Uploading: {title[:30]}...")
    print(f"      📝 Description Length: {len(description)} chars") 

    youtube = get_authenticated_service()

    # YouTube 카테고리 ID 설정
    # 24:Ent, 25:News, 28:Tech, 17:Sport, 26:Howto/Style
    cat_lower = category.lower()
    
    if cat_lower == "world": cid = "25"      # News & Politics
    elif cat_lower in ["ent", "entertainment"]: cid = "24" # Entertainment
    elif cat_lower in ["fin", "finance"]: cid = "25"       # News & Politics
    elif cat_lower in ["tech", "science"]: cid = "28"      # Science & Technology
    elif cat_lower in ["sport", "sports"]: cid = "17"      # Sports
    elif cat_lower in ["art", "arts"]: cid = "1"           # Film & Animation (Art 대체)
    elif cat_lower == "health": cid = "25"                 # [NEW] News & Politics (뉴스 성격)
    else: cid = "24" # Default

    body = {
        "snippet": {
            "title": title,
            "description": description,
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
        target_playlist_id = PLAYLIST_IDS.get(cat_lower)
        
        if target_playlist_id:
            add_video_to_playlist(youtube, video_id, target_playlist_id)
        else:
            print(f"      ℹ️ Playlist ID missing or not set for '{cat_lower}'. Video uploaded but not added to playlist.")

        return True

    except Exception as e:
        print(f"❌ [YouTube API] Error: {e}")
        return False