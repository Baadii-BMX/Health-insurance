import os
import json
import logging
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import requests
from models import db, Hospital, Medicine, UnansweredQuestion
import rasa_api

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "emd_chatbot_secret_key")

# Configure database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/emd_chatbot")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Enable CORS for API requests
CORS(app)

# Initialize database
db.init_app(app)

# Create tables on startup
with app.app_context():
    db.create_all()
    # Import pre-defined data if tables are empty
    if Hospital.query.count() == 0:
        try:
            with open('data/hospitals.json', 'r', encoding='utf-8') as f:
                hospitals = json.load(f)
                for hospital in hospitals:
                    db.session.add(Hospital(
                        name=hospital['name'],
                        city=hospital['city'],
                        insurance_contract=hospital['insurance_contract']
                    ))
                db.session.commit()
                logger.info("Imported hospital data successfully")
        except Exception as e:
            logger.error(f"Error importing hospital data: {e}")
    
    if Medicine.query.count() == 0:
        try:
            with open('data/icd10_tablets.json', 'r', encoding='utf-8') as f:
                medicines = json.load(f)
                count = 0
                for medicine in medicines:
                    if count > 1000:  # Limit initial import to avoid memory issues
                        break
                    db.session.add(Medicine(
                        icd10_code=medicine['icd10_code'],
                        icd10_name=medicine['icd10_name'],
                        tablet_id=medicine['tablet_id'],
                        tablet_name_mon=medicine['tablet_name_mon'],
                        tablet_name_sales=medicine['tablet_name_sales'],
                        unit_price=medicine['unit_price'],
                        unit_discount=medicine['unit_discount']
                    ))
                    count += 1
                db.session.commit()
                logger.info(f"Imported {count} medicine records successfully")
        except Exception as e:
            logger.error(f"Error importing medicine data: {e}")

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message', '')
    
    if not user_message:
        return jsonify({'text': 'Уучлаарай, таны мессежийг хүлээн авах боломжгүй байна.'})
    
    try:
        # Log the user message for debugging
        logger.debug(f"User message: '{user_message}'")
        
        # Direct pattern matching for common questions
        message_lower = user_message.lower()
        
        # Handle specific patterns directly without relying on Rasa
        if "дэвтэргүй" in message_lower or "дэвтэр" in message_lower:
            return jsonify({'text': "Эрүүл мэндийн даатгалын цахим системд шилжсэнээс хойш эрүүл мэндийн даатгалын дэвтэр шаардлагагүй болсон. Регистрийн дугаараар болон хурууны хээгээ уншуулж эрүүл мэндийн тусламж үйлчилгээ авах боломжтой."})
        elif "ходоод" in message_lower and "өвчин" in message_lower:
            return jsonify({'text': "Ходоодны өвчний үед Эрүүл мэндийн даатгалын гэрээт эмнэлэгт үзүүлэх боломжтой. Улсын гуравдугаар төв эмнэлэг, Улсын нэгдүгээр төв эмнэлэг, Гастроэнтерологийн төв зэрэг ходоодны өвчнөөр мэргэшсэн эмнэлгүүд байдаг. Эмнэлгийн дэлгэрэнгүй жагсаалтыг emd.gov.mn сайтын 'Гэрээт байгууллага' цэснээс харах боломжтой."})
        elif "ханиад" in message_lower or "томуу" in message_lower or ("эм" in message_lower and "ууж" in message_lower):
            return jsonify({'text': "Ханиад, томууны үед хэрэглэх хөнгөлөлттэй эмэнд Парацетамол, Ибупрофен, Аспирин, Амоксициллин зэрэг орж, 40-70% хөнгөлөлттэй. Эмч Танд өвчний онцлогт тохирсон эм бичиж өгөх болно. Өрхийн эмнэлэгт үзүүлээд, эмийн жор авах нь хамгийн зөв."})
        elif "парацетамол" in message_lower:
            return jsonify({'text': "Парацетамол нь Эрүүл мэндийн даатгалын хөнгөлөлттэй эмийн жагсаалтад орсон бөгөөд 50% хөнгөлөлттэй. Эмчийн бичсэн жороор өрхийн эмнэлэг болон эмийн сангуудаас авах боломжтой."})
        elif ("гэрээт" in message_lower and "эмнэлг" in message_lower) or ("эмнэлэг" in message_lower and "гэрээ" in message_lower) or ("эмнэлгүүд" in message_lower) or ("эмд-тэй" in message_lower) or ("жагсаалт" in message_lower and "эмнэлг" in message_lower) or ("хөнгөлөлттэй эмчлүүлж" in message_lower):
            return jsonify({'text': "Эрүүл мэндийн даатгалын ерөнхий газар нь бүх аймаг, дүүргийн нэгдсэн эмнэлэг, төв эмнэлэг, өрхийн эмнэлэг болон 150 гаруй хувийн эмнэлэгтэй гэрээтэй. Энэ гэрээт эмнэлгүүдэд ЭМД-тай иргэд хөнгөлөлттэй үнээр эмчлүүлэх боломжтой. Бүх гэрээт эмнэлгийн жагсаалтыг emd.gov.mn сайтын 'Гэрээт байгууллага' цэснээс харах боломжтой."})
        elif "шимтгэл" in message_lower or "төлбөр" in message_lower or "хураамж" in message_lower or "хэмжээ" in message_lower or "хэд вэ" in message_lower:
            return jsonify({'text': "ЭМД-ын шимтгэлийн хэмжээ: 2025 оны 1-3 сар хүртэл сарын 13200 төгрөг, 4-р сараас эхлэн 15840 төгрөг болно. Ажил олгогч, даатгуулагч тус тус 2:1 харьцаагаар хуваан төлнө. Хувиараа хөдөлмөр эрхлэгч нь бүрэн дүнгээр төлнө."})
        elif "дутуу сар" in message_lower or "шалгах" in message_lower:
            return jsonify({'text': "Эрүүл мэндийн даатгалын шимтгэлийн дутуу саруудаа дараах сувгуудаар шалгах боломжтой: 1) www.emd.gov.mn сайтаар, 2) www.e-mongolia.mn сайт болон аппликейшнээр, 3) Ибаримт аппликейшн ашиглаж шалгах боломжтой."})
        elif ("хөнгөлөлт" in message_lower and "эм" in message_lower) or ("эмийн жагсаалт" in message_lower) or ("эмийн" in message_lower and "хөнгөлөлт" in message_lower) or ("өвчин" in message_lower and "эм" in message_lower):
            return jsonify({'text': "ЭМД-ын хөнгөлөлттэй эмийн жагсаалтад 600 гаруй нэр төрлийн эм орсон бөгөөд 30-100% хүртэлх хөнгөлөлттэй үнээр авах боломжтой. Эмч таны өвчнийг оношлон, тохирох эмийн жор бичиж өгөх бөгөөд, хөнгөлөлттэй эмүүдийг эмчийн жороор авах боломжтой. Бүрэн жагсаалтыг emd.gov.mn сайтаас харах боломжтой."})
        elif ("үйлчилгээ" in message_lower and "болох" in message_lower) or ("тусламж" in message_lower and "авах" in message_lower) or ("авч болох" in message_lower) or ("үйлчилгээ" in message_lower and "авах" in message_lower):
            return jsonify({'text': "Эрүүл мэндийн даатгалаар авах боломжтой үйлчилгээнүүд: 1) Хэвтүүлэн эмчлэх тусламж үйлчилгээ, 2) Амбулаторийн тусламж үйлчилгээ, 3) Өндөр өртөгтэй оношилгоо, шинжилгээ, 4) Яаралтай тусламж, 5) Түргэн тусламж, 6) Телемедицин, 7) Өдрийн эмчилгээ үйлчилгээ, 8) Эмийн үнийн хөнгөлөлт."})
        elif "төлөх" in message_lower or "сувг" in message_lower or "хаанаас" in message_lower:
            return jsonify({'text': "Эрүүл мэндийн даатгалаа дараах сувгуудаар төлөх боломжтой: 1) И-Баримт гар утасны апп, 2) И-Баримт вэб сайтаар, 3) E-Mongolia аппликейшн, 4) Банкны салбар, 5) Банкны автомат машин (ATM), 6) Интернет банк."})
        elif "заавал" in message_lower or "нөхөн төлөх" in message_lower:
            return jsonify({'text': "Эрүүл мэндийн даатгалын тухай хуулиар Монгол улсын иргэн бүр эрүүл мэндийн албан журмын даатгалд заавал даатгуулах үүрэгтэй. Энэхүү даатгал нь эмнэлгийн зардлын төлбөрийг хөнгөвчилдөг."})
        elif "битүүмж" in message_lower:
            return jsonify({'text': "Битүүмж нь тухайн эрүүл мэндийн байгууллагад иргэн даатгуулагчийн үйлчлүүлж байгааг илэрхийлсэн мэдээлэл бөгөөд нээх, хаах нь тухайн эрүүл мэндийн байгууллагын хариуцах асуудал юм."})
        elif "сайн" in message_lower or "өдрийн мэнд" in message_lower:
            return jsonify({'text': "Сайн байна уу! Би Эрүүл Мэндийн Даатгалын бот байна. Танд хэрхэн туслах вэ?"})
        # If no direct match, use a general response about EMD
        else:
            return jsonify({'text': "Эрүүл мэндийн даатгал нь даатгуулагчийн эрүүл мэндийн улмаас учирч болзошгүй санхүүгийн эрсдэлийг хуваалцах зорилготой. emd.gov.mn сайтаас дэлгэрэнгүй мэдээлэл авах боломжтой. Тодорхой асуулт байвал надаас асууна уу."})
        
    except requests.exceptions.ConnectionError:
        logger.error("Could not connect to Rasa server")
        return jsonify({'text': 'Сервертэй холбогдож чадсангүй. Rasa сервер ажиллаж байгаа эсэхийг шалгана уу.'})
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        return jsonify({'text': 'Алдаа гарлаа. Дахин оролдоно уу.'})

@app.route('/api/hospitals', methods=['GET'])
def get_hospitals():
    try:
        hospitals = Hospital.query.all()
        return jsonify([{
            'name': h.name,
            'city': h.city,
            'insurance_contract': h.insurance_contract
        } for h in hospitals])
    except Exception as e:
        logger.error(f"Error fetching hospitals: {e}")
        return jsonify({'error': 'Эмнэлгийн мэдээлэл авах үед алдаа гарлаа.'}), 500

@app.route('/api/medicines', methods=['GET'])
def get_medicines():
    icd10_code = request.args.get('icd10_code')
    tablet_name = request.args.get('tablet_name')
    
    try:
        query = Medicine.query
        
        if icd10_code:
            query = query.filter(Medicine.icd10_code == icd10_code)
        
        if tablet_name:
            query = query.filter(Medicine.tablet_name_sales.ilike(f'%{tablet_name}%') | 
                                Medicine.tablet_name_mon.ilike(f'%{tablet_name}%'))
        
        medicines = query.limit(30).all()  # Limit results to avoid large responses
        
        return jsonify([{
            'icd10_code': m.icd10_code,
            'icd10_name': m.icd10_name,
            'tablet_name_mon': m.tablet_name_mon,
            'tablet_name_sales': m.tablet_name_sales,
            'unit_price': m.unit_price,
            'unit_discount': m.unit_discount
        } for m in medicines])
    except Exception as e:
        logger.error(f"Error fetching medicines: {e}")
        return jsonify({'error': 'Эмийн мэдээлэл авах үед алдаа гарлаа.'}), 500

@app.route('/api/save-unanswered', methods=['POST'])
def save_unanswered():
    data = request.json
    question = data.get('question', '')
    
    if not question:
        return jsonify({'success': False, 'error': 'Асуулт хоосон байна.'}), 400
    
    try:
        unanswered = UnansweredQuestion(question=question)
        db.session.add(unanswered)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error saving unanswered question: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('index.html'), 404

@app.errorhandler(500)
def server_error(e):
    logger.error(f"Server error: {e}")
    return jsonify({'error': 'Серверийн алдаа гарлаа. Дахин оролдоно уу.'}), 500
