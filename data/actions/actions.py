# actions.py
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
import requests
import os
import logging
from dotenv import load_dotenv
import psycopg2

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Database connection parameters from environment variables
DB_CONFIG = {
    "dbname": os.getenv("PGDATABASE"),
    "user": os.getenv("PGUSER"),
    "password": os.getenv("PGPASSWORD"),
    "host": os.getenv("PGHOST"),
    "port": os.getenv("PGPORT"),
}

# Function to establish a database connection
def get_db_connection():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        logger.error(f"❌ Database connection error: {e}")
        return None

# Custom action to get hospital information
class ActionGetHospitalInfo(Action):
    def name(self):
        return "action_get_hospital_info"

    def run(self, dispatcher, tracker, domain):
        hospital_name = tracker.get_slot("hospital_name")
        
        if not hospital_name:
            dispatcher.utter_message(text="Та эмнэлгийн нэр оруулаагүй байна. Эмнэлгийн нэрээ оруулна уу.")
            return []
        
        conn = get_db_connection()

        if not conn:
            dispatcher.utter_message(text="Уучлаарай, датабейсэд холбогдох боломжгүй байна.")
            return []

        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT name, city, insurance_contract FROM hospitals WHERE name ILIKE %s", (f"%{hospital_name}%",))
                result = cursor.fetchone()
                
                if result:
                    name, city, insurance_contract = result
                    insurance_status = "гэрээтэй" if insurance_contract else "гэрээгүй"
                    response = f"🏥 {name} эмнэлэг нь {city} хотод байрладаг бөгөөд ЭМД-тай {insurance_status} байна."
                else:
                    response = f"{hospital_name} эмнэлгийн мэдээлэл олдсонгүй."
                
                dispatcher.utter_message(text=response)
        except Exception as e:
            logger.error(f"❌ Error fetching hospital info: {e}")
            dispatcher.utter_message(text="Мэдээлэл татахад алдаа гарлаа.")
        finally:
            if conn:
                conn.close()

        return []

# Custom action to get medicine information
class ActionGetMedicineInfo(Action):
    def name(self):
        return "action_get_medicine_info"

    def run(self, dispatcher, tracker, domain):
        tablet_name = tracker.get_slot("tablet_name")
        
        if not tablet_name:
            dispatcher.utter_message(text="Та эмийн нэр оруулаагүй байна. Эмийн нэрээ оруулна уу.")
            return []
        
        conn = get_db_connection()

        if not conn:
            dispatcher.utter_message(text="Уучлаарай, датабейсэд холбогдох боломжгүй байна.")
            return []

        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT tablet_name_sales, tablet_name_mon, icd10_name, unit_price, unit_discount 
                    FROM medicines 
                    WHERE tablet_name_sales ILIKE %s OR tablet_name_mon ILIKE %s 
                    LIMIT 5
                """, (f"%{tablet_name}%", f"%{tablet_name}%"))
                
                results = cursor.fetchall()
                
                if results:
                    response = f"💊 {tablet_name} эмийн мэдээлэл:\n\n"
                    
                    for i, (sales_name, mon_name, icd10_name, price, discount) in enumerate(results, 1):
                        discount_percent = int((discount / price) * 100) if price and discount else 0
                        response += f"{i}. {sales_name} ({mon_name})\n"
                        response += f"   Хэрэглэх: {icd10_name}\n"
                        response += f"   Үнэ: {int(price)}₮ | Хөнгөлөлт: {discount_percent}% ({int(discount)}₮)\n\n"
                else:
                    response = f"{tablet_name} эмийн мэдээлэл олдсонгүй."
                
                dispatcher.utter_message(text=response)
        except Exception as e:
            logger.error(f"❌ Error fetching medicine info: {e}")
            dispatcher.utter_message(text="Мэдээлэл татахад алдаа гарлаа.")
        finally:
            if conn:
                conn.close()

        return []

# Custom action to get insurance fee information
class ActionGetInsuranceFee(Action):
    def name(self):
        return "action_get_insurance_fee"

    def run(self, dispatcher, tracker, domain):
        current_year = 2025
        current_month = 3
        
        fee_data = {
            2019: {"monthly": 3200, "yearly": 38400},
            2020: {"monthly": 4200, "yearly": 50400},
            2021: {"monthly": 4200, "yearly": 50400},
            2022: {"monthly": 4200, "yearly": 50400},
            2023: {"monthly": 5500, "yearly": 66000},
            2024: {"monthly": 6600, "yearly": 79200},
            2025: {"monthly_q1": 13200, "monthly_q2plus": 15840}
        }
        
        response = "📊 Эрүүл мэндийн даатгалын шимтгэлийн хэмжээ:\n\n"
        
        for year in sorted(fee_data.keys()):
            fee = fee_data[year]
            if year == 2025:
                if current_year == 2025 and current_month <= 3:
                    response += f"**{year} он (Одоогийн)**: Сарын {fee['monthly_q1']}₮ (1-3 сар), 4-р сараас {fee['monthly_q2plus']}₮\n"
                else:
                    response += f"{year} он: Сарын {fee['monthly_q1']}₮ (1-3 сар), 4-р сараас {fee['monthly_q2plus']}₮\n"
            else:
                if year == current_year:
                    response += f"**{year} он (Одоогийн)**: Сарын {fee['monthly']}₮, жилийн {fee['yearly']}₮\n"
                else:
                    response += f"{year} он: Сарын {fee['monthly']}₮, жилийн {fee['yearly']}₮\n"
        
        dispatcher.utter_message(text=response)
        return []

# Custom action to get services information
class ActionGetServices(Action):
    def name(self):
        return "action_get_services"

    def run(self, dispatcher, tracker, domain):
        services = [
            "Хэвтүүлэн эмчлэх тусламж, үйлчилгээ",
            "Амбулаторийн тусламж, үйлчилгээ",
            "Өндөр өртөгтэй оношилгоо, шинжилгээ",
            "Яаралтай тусламж",
            "Түргэн тусламж",
            "Телемедицин",
            "Өдрийн эмчилгээ, үйлчилгээ",
            "Диализын тусламж, үйлчилгээ",
            "Хорт хавдрын хими, туяаны өдрийн эмчилгээ",
            "Сэргээн засах тусламж, үйлчилгээ",
            "Хөнгөвчлөх тусламж үйлчилгээ",
            "Уламжлалт анагаах ухааны тусламж, үйлчилгээ",
            "Эмийн үнийн хөнгөлөлт"
        ]
        
        response = "🏥 Эрүүл мэндийн даатгалаар авах боломжтой үйлчилгээнүүд:\n\n"
        
        for i, service in enumerate(services, 1):
            response += f"{i}. {service}\n"
        
        dispatcher.utter_message(text=response)
        return []

# Custom action to get general insurance information
class ActionGetInsuranceInfo(Action):
    def name(self):
        return "action_get_insurance_info"

    def run(self, dispatcher, tracker, domain):
        info = """📋 **Эрүүл Мэндийн Даатгал (ЭМД) гэж юу вэ?**

Эрүүл мэндийн даатгал нь иргэдийн эрүүл мэндийн улмаас үүссэн санхүүгийн эрсдэлийг хуваалцах эв санааны нэгдэл юм. Иргэд сар бүр тогтмол шимтгэл төлснөөр:

1️⃣ Өөрийн болон бусдын эрүүл мэндийн эрсдэлийг даатгуулдаг
2️⃣ Хөнгөлөлттэй эмчилгээ, оношилгоо, шинжилгээ хийлгэх боломжтой
3️⃣ 600 гаруй нэр төрлийн эмийг 30-100% хөнгөлөлттэй авах боломжтой
4️⃣ Гэрээт эмнэлгүүдээр үйлчлүүлэх эрхтэй

Даатгал нь таны болон таны гэр бүлийн эрүүл мэндийн асуудалд санхүүгийн дэмжлэг үзүүлж, амьдралын чанарыг тань сайжруулахад тусална."""
        
        dispatcher.utter_message(text=info)
        return []

# Custom action to save unanswered questions
class ActionSaveUnansweredQuestion(Action):
    def name(self):
        return "action_save_unanswered_question"

    def run(self, dispatcher, tracker, domain):
        question = tracker.latest_message.get('text')
        
        if not question:
            return []
        
        conn = get_db_connection()

        if not conn:
            logger.error("Could not connect to database to save unanswered question")
            return []

        try:
            with conn.cursor() as cursor:
                cursor.execute("INSERT INTO unanswered_questions (question) VALUES (%s)", (question,))
                conn.commit()
                logger.info(f"Saved unanswered question: {question}")
        except Exception as e:
            logger.error(f"❌ Error saving question: {e}")
            conn.rollback()
        finally:
            if conn:
                conn.close()

        return []