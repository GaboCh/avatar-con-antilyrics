import os
import pickle
import requests
import xml.etree.ElementTree as ET

SCOPES = ['https://www.googleapis.com/auth/youtube.upload',
          'https://www.googleapis.com/auth/youtube.readonly']


def obtener_tags_trending(youtube, pais='EC', categoria_yt='17', extra_tags=None):
    """
    Combina tags de Google Trends + YouTube Trending.
    Sin instalar nada nuevo — usa requests y la YouTube API ya configurada.
    categoria_yt 17 = Deportes
    """
    tags = set()

    # --- Google Trends RSS (sin pytrends, solo requests) ---
    try:
        r = requests.get(
            f'https://trends.google.com/trending/rss?geo={pais}',
            timeout=10,
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        root = ET.fromstring(r.content)
        for item in root.findall('./channel/item'):
            title = item.findtext('title', '')
            if title:
                for word in title.split():
                    w = word.strip('.,!?#@').lower()
                    if len(w) > 2:
                        tags.add(w)
        print(f"   📈 Google Trends: {len(tags)} tags obtenidos")
    except Exception as e:
        print(f"   ⚠️ Google Trends falló: {e}")

    # --- YouTube Trending (API ya configurada) ---
    try:
        resp = youtube.videos().list(
            part='snippet',
            chart='mostPopular',
            regionCode=pais,
            videoCategoryId=categoria_yt,
            maxResults=10
        ).execute()
        for item in resp.get('items', []):
            snippet = item.get('snippet', {})
            for tag in snippet.get('tags', []):
                tags.add(tag.lower())
            title = snippet.get('title', '')
            for word in title.split():
                w = word.strip('.,!?#@').lower()
                if len(w) > 2:
                    tags.add(w)
        print(f"   📺 YouTube Trending: tags combinados = {len(tags)}")
    except Exception as e:
        print(f"   ⚠️ YouTube Trending falló: {e}")

    if extra_tags:
        for t in extra_tags:
            tags.add(t.strip().lower())

    # YouTube acepta máx 500 chars en tags, máx 30 tags
    tags_list = list(tags)[:30]
    print(f"   🏷️ Tags finales: {tags_list}")
    return tags_list


def autenticar_youtube(credenciales_dir):
    """
    Autentica con la YouTube Data API v3 usando OAuth2.
    Abre el navegador la primera vez. Guarda el token para reusar.
    """
    try:
        from googleapiclient.discovery import build
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
    except ImportError:
        print("❌ Faltan paquetes. Ejecuta:")
        print("   pip install google-api-python-client google-auth-oauthlib google-auth-httplib2")
        return None

    client_secrets = os.path.join(credenciales_dir, 'client_secrets.json')
    token_path     = os.path.join(credenciales_dir, 'token.pickle')

    if not os.path.exists(client_secrets):
        print(f"❌ No se encontró client_secrets.json en: {credenciales_dir}")
        print("   Descárgalo de Google Cloud Console → Credenciales → OAuth 2.0.")
        return None

    creds = None
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow  = InstalledAppFlow.from_client_secrets_file(client_secrets, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)

    return build('youtube', 'v3', credentials=creds)


def subir_video(youtube, video_path, titulo, descripcion, categoria='22', privacidad='public', tags=None, progress_fn=None):
    """
    Sube un video a YouTube con subida resumible (chunk por chunk).
    categoria 22 = 'People & Blogs'
    privacidad: 'public', 'unlisted', 'private'
    progress_fn: callback opcional fn(msg) para reportar progreso
    """
    from googleapiclient.http import MediaFileUpload

    body = {
        'snippet': {
            'title':       titulo[:100],
            'description': descripcion or '',
            'categoryId':  categoria,
            'tags':        tags or [],
        },
        'status': {
            'privacyStatus':          privacidad,
            'selfDeclaredMadeForKids': False,
        }
    }

    media   = MediaFileUpload(video_path, mimetype='video/mp4', resumable=True, chunksize=5 * 1024 * 1024)
    request = youtube.videos().insert(part='snippet,status', body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            progreso = int(status.progress() * 100)
            msg = f"   📤 Subiendo... {progreso}%"
            if progress_fn:
                progress_fn(msg)
            else:
                print(msg)

    return response
