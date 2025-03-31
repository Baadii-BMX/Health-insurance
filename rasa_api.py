import os
import json
import logging
import requests
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

# Rasa server configuration
RASA_URL = os.environ.get("RASA_URL", "http://localhost:5005")
RASA_WEBHOOK_URL = urljoin(RASA_URL, "/webhooks/rest/webhook")

def send_message(message_text):
    """
    Sends a message to the Rasa server and returns the response
    """
    try:
        payload = {"sender": "user", "message": message_text}
        headers = {"Content-Type": "application/json"}
        
        logger.debug(f"Sending message to Rasa: {message_text}")
        response = requests.post(RASA_WEBHOOK_URL, json=payload, headers=headers)
        
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
        raise e
    except Exception as e:
        logger.error(f"Error communicating with Rasa: {e}")
        return {"text": "Rasa серверт хандахад алдаа гарлаа."}
