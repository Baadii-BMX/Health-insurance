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

# A dictionary of keywords to responses when Rasa server is not available
# This helps us provide relevant fallback responses based on the message content
FALLBACK_RESPONSES = {
    "greet": "Сайн байна уу! Эрүүл Мэндийн Даатгалын бот байна. Танд хэрхэн туслах вэ?",
    "hospital": "Эрүүл мэндийн даатгалын ерөнхий газартай гэрээт эрүүл мэндийн байгууллагын хаяг байршил, утасны дугаар, үйл ажиллагааны чиглэл www.emd.gov.mn сайтад гэрээт байгууллага цэс рүү нэвтрэн орж харах боломжтой.",
    "medicine": "ЭМД-ын хөнгөлөлттэй эмийн жагсаалтаар 600 нэр төрлийн эмийг 30-100 хувийн хөнгөлөлттэй үнээр авах боломжтой.",
    "fee": "ЭМД-ын шимтгэл 2025 оны 1-3 сар хүртэл сарын 13200 төгрөг, 4-р сараас эхлэн 15840 төгрөг болно.",
    "service": "Эрүүл мэндийн даатгалаар авах боломжтой тусламж үйлчилгээ: Хэвтүүлэн эмчлэх тусламж, амбулаторийн тусламж, өндөр өртөгтэй оношилгоо, яаралтай тусламж, түргэн тусламж, телемедицин, өдрийн эмчилгээ, диализ, хорт хавдрын хими, сэргээн засах тусламж, хөнгөвчлөх тусламж, уламжлалт анагаах ухааны тусламж, эмийн үнийн хөнгөлөлт.",
    "payment": "Эрүүл мэндийн даатгалаа дараах сувгуудаар төлөх боломжтой: И-Баримт гар утасны аппликейшн, И-Баримт веб сайтаар, E-Mongolia аппликейшн.", 
    "default": "Эрүүл мэндийн даатгалын талаар асуулт байвал би таньд туслахыг хичээнэ. Одоогоор би туршилтын горимд ажиллаж байна."
}

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
            
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
        logger.error(f"Could not connect to Rasa server: {e}")
        
        # Get the most appropriate fallback response based on message content
        message_lower = message_text.lower()
        
        # Check for different types of queries and return an appropriate response
        if "сайн" in message_lower or "мэнд" in message_lower:
            return {"text": FALLBACK_RESPONSES["greet"]}
        elif "эмнэлг" in message_lower or "эмнэлэг" in message_lower or "гэрээт" in message_lower:
            return {"text": FALLBACK_RESPONSES["hospital"]}
        elif "эм" in message_lower or "хөнгөлөлт" in message_lower:
            return {"text": FALLBACK_RESPONSES["medicine"]}
        elif "төлбөр" in message_lower or "шимтгэл" in message_lower or "хураамж" in message_lower:
            return {"text": FALLBACK_RESPONSES["fee"]}
        elif "үйлчилгээ" in message_lower or "тусламж" in message_lower or "авч болох" in message_lower:
            return {"text": FALLBACK_RESPONSES["service"]}
        elif "төлөх" in message_lower or "төлбөр" in message_lower or "төлөлт" in message_lower:
            return {"text": FALLBACK_RESPONSES["payment"]}
        else:
            return {"text": FALLBACK_RESPONSES["default"]}
    except Exception as e:
        logger.error(f"Error communicating with Rasa: {e}")
        return {"text": "Хариу өгөх үед алдаа гарлаа. Дахин оролдоно уу."}
