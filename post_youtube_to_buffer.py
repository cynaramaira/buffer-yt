import os
import requests
import feedparser

CHANNEL_ID = "UC-fKlWyY4bCAM8lugciQQEg"
RSS_URL = f"https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL_ID}"
STATE_FILE = "last_posted_video.txt"

BUFFER_ACCESS_TOKEN = os.environ.get("BUFFER_ACCESS_TOKEN")
BUFFER_PROFILE_IDS_RAW = os.environ.get("BUFFER_PROFILE_IDS", "")
PROFILE_IDS = [pid.strip() for pid in BUFFER_PROFILE_IDS_RAW.split(",") if pid.strip()]

BUFFER_GRAPHQL_URL = "https://api.buffer.com"

def get_last_posted_id():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as file:
            return file.read().strip()
    return ""

def save_last_posted_id(video_id):
    with open(STATE_FILE, "w", encoding="utf-8") as file:
        file.write(video_id)

def send_to_buffer(text):
    if not PROFILE_IDS:
        print("Erro: Nenhum ID de canal configurado na variável BUFFER_PROFILE_IDS.")
        return

    headers = {
        "Authorization": f"Bearer {BUFFER_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    mutation = """
    mutation CreateSinglePost($channelId: ID!, $text: String!) {
      createPost(input: {
        channelId: $channelId
        text: $text
        schedulingType: shareNow
      }) {
        ... on PostActionSuccess {
          post {
            id
            status
          }
        }
        ... on UserError {
          message
        }
      }
    }
    """

    for channel_id in PROFILE_IDS:
        payload = {
            "query": mutation,
            "variables": {
                "channelId": channel_id,
                "text": text
            }
        }
        response = requests.post(BUFFER_GRAPHQL_URL, json=payload, headers=headers)
        if response.status_code == 200:
            res_data = response.json()
            errors = res_data.get("errors")
            if errors:
                print(f"Erro GraphQL no canal {channel_id}: {errors}")
            else:
                print(f"Publicação enviada com sucesso ao canal {channel_id}.")
        else:
            print(f"Falha HTTP no canal {channel_id}: {response.status_code} - {response.text}")

def main():
    feed = feedparser.parse(RSS_URL)
    
    if not feed.entries:
        print("Nenhum item encontrado no feed RSS.")
        return

    latest_video = feed.entries[0]
    video_id = latest_video.yt_videoid
    video_title = latest_video.title
    video_link = latest_video.link

    last_id = get_last_posted_id()

    # Na primeira execução salva a referência e não dispara publicações antigas
    if not last_id:
        print("Primeira execução: gravando o último vídeo atual como referência.")
        save_last_posted_id(video_id)
        return

    if video_id != last_id:
        print(f"Novo vídeo detectado: {video_title}")
        
        # Limite seguro para não estourar os 280 caracteres do X
        if len(video_title) > 200:
            video_title = video_title[:197] + "..."
            
        post_text = f"{video_title}\n\nVeja o vídeo no YouTube: {video_link}"
        
        send_to_buffer(post_text)
        save_last_posted_id(video_id)
    else:
        print("Nenhum vídeo novo publicado desde a última checagem.")

if __name__ == "__main__":
    main()