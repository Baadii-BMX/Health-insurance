import os
import json
import logging
import requests
from urllib.parse import urljoin
import random

logger = logging.getLogger(__name__)

# Rasa server configuration
RASA_URL = os.environ.get("RASA_URL", "http://localhost:5005")
RASA_WEBHOOK_URL = urljoin(RASA_URL, "/webhooks/rest/webhook")

# Fallback responses when Rasa server is not available
FALLBACK_RESPONSES = [
    "Сайн байна уу! Эрүүл Мэндийн Даатгалын бот байна. Одоогоор би туршилтын горимд ажиллаж байна.",
    "Эрүүл мэндийн даатгалын талаар асуулт байвал би таньд туслахыг хичээнэ.",
    "ЭМД-ын шимтгэл 2025 оны 1-3 сар хүртэл сарын 13200 төгрөг, 4-р сараас эхлэн 15840 төгрөг болно.",
    "Эмнэлгийн даатгалаа и-баримт аппликейшнээр төлөх боломжтой.",
    "ЭМД-ын хөнгөлөлттэй эмийн жагсаалтаар 600 нэр төрлийн эмийг 30-100 хувийн хөнгөлөлттэй үнээр авах боломжтой.",
    "Эрүүл мэндийн даатгалаар авах боломжтой үйлчилгээнүүдэд хэвтүүлэн эмчлэх, амбулаторийн тусламж, өндөр өртөгтэй оношилгоо, яаралтай тусламж зэрэг багтана."
]

def send_message(message_text):
    """
    Sends a message to the Rasa server and returns the response.
    If Rasa server is not available, returns a fallback response.
    """
    try:
        payload = {"sender": "user", "message": message_text}
        headers = {"Content-Type": "application/json"}
        
        logger.debug(f"Sending message to Rasa: {message_text}")
        
        # Try to connect to Rasa server (comment this for testing with fallbacks)
        response = requests.post(RASA_WEBHOOK_URL, json=payload, headers=headers, timeout=3)
        
        if response.status_code == 200:
            response_data = response.json()
            logger.debug(f"Received response from Rasa: {response_data}")
            
            # Extract text from the first response (if any)
            if response_data and len(response_data) > 0:
                if "text" in response_data[0]:
                    return {"text": response_data[0]["text"]}
                elif "custom" in response_data[0]:
                    return response_data[0]["custom"]
            
            # Handle empty response
            return {"text": "Уучлаарай, би хариу өгөх боломжгүй байна."}
        else:
            logger.error(f"Rasa server returned status code {response.status_code}")
            return {"text": "Серверээс алдаа хариу ирлээ. Дахин оролдоно уу."}
            
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Could not connect to Rasa server: {e}")
        # Until Rasa server is set up, return a random fallback response
        return {"text": random.choice(FALLBACK_RESPONSES)}
    except requests.exceptions.Timeout:
        logger.error("Timeout connecting to Rasa server")
        return {"text": random.choice(FALLBACK_RESPONSES)}
    except Exception as e:
        logger.error(f"Error communicating with Rasa: {e}")
        return {"text": "Хариу өгөх үед алдаа гарлаа. Дахин оролдоно уу."}
