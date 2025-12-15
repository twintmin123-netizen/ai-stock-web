# utils/papago.py
# Naver Papago Translation API

import os
import requests
from typing import Optional


def translate_with_papago(
    text: str,
    source: str = "auto",  # Support auto-detection
    target: str = "ko"
) -> Optional[str]:
    """
    Translate text using Naver Papago API.
    
    Args:
        text: Text to translate
        source: Source language code (auto, ko, en, ja, zh-CN, etc.)
        target: Target language code (ko, en, ja, zh-CN, etc.)
    
    Returns:
        Translated text or None if translation fails
    """
    client_id = os.getenv("PAPAGO_CLIENT_ID")
    client_secret = os.getenv("PAPAGO_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        print("[Papago] API credentials not found in .env")
        return None
    
    if not text or not text.strip():
        return text
    
    url = "https://naveropenapi.apigw.ntruss.com/nmt/v1/translation"
    
    headers = {
        "X-NCP-APIGW-API-KEY-ID": client_id,
        "X-NCP-APIGW-API-KEY": client_secret,
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
    }
    
    data = {
        "source": source,
        "target": target,
        "text": text
    }
    
    try:
        response = requests.post(url, headers=headers, data=data, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        translated_text = result.get("message", {}).get("result", {}).get("translatedText")
        
        if translated_text:
            print(f"[Papago] Translated '{text}' -> '{translated_text}'")
            return translated_text
        else:
            print(f"[Papago] No translation result for '{text}'")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"[Papago] API request failed: {e}")
        return None
    except Exception as e:
        print(f"[Papago] Translation error: {e}")
        return None
