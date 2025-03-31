import os
import json
import logging
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import requests
from models import db, Hospital, Medicine, UnansweredQuestion
import rasa_api
from learning_engine import learning_engine

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
        
        # Temporarily disable learning engine until database is migrated
        # learning_engine.learn_from_question(user_message)
        # Just log the message for now
        logger.info(f"Future learning data: {user_message}")
        
        # Direct pattern matching for common questions
        message_lower = user_message.lower()
        
        # Handle specific patterns directly without relying on Rasa
        if "дэвтэргүй" in message_lower or "дэвтэр" in message_lower:
            return jsonify({'text': "Эрүүл мэндийн даатгалын цахим системд шилжсэнээс хойш эрүүл мэндийн даатгалын дэвтэр шаардлагагүй болсон. Регистрийн дугаараар болон хурууны хээгээ уншуулж эрүүл мэндийн тусламж үйлчилгээ авах боломжтой."})
        elif "ходоод" in message_lower and "өвчин" in message_lower:
            return jsonify({'text': "Ходоодны өвчний үед дараах эмнэлгүүдэд үзүүлэх боломжтой: 1) Улсын гуравдугаар төв эмнэлэг, 2) Улсын нэгдүгээр төв эмнэлэг, 3) Гастроэнтерологийн төв, 4) Интермед эмнэлэг, 5) Гранд-Мед дүүргийн эмнэлгүүд. Эдгээр эмнэлгүүд гастроэнтеролог нарийн мэргэжлийн эмчтэй бөгөөд дуран шинжилгээ, компьютер томограф, соронзон резонансын шинжилгээнүүдийг ЭМД-аар 70-90% хөнгөлөлттэй хийлгэх боломжтой. Эмнэлгийн магадлагаатай бол үзлэгийн төлбөр мөн хөнгөлөлттэй."})
        elif "ханиад" in message_lower or "томуу" in message_lower or ("эм" in message_lower and "ууж" in message_lower):
            return jsonify({'text': "Ханиад, томууны үед хэрэглэх хөнгөлөлттэй эмэнд Парацетамол, Ибупрофен, Аспирин, Амоксициллин зэрэг орж, 40-70% хөнгөлөлттэй. Эмч Танд өвчний онцлогт тохирсон эм бичиж өгөх болно. Өрхийн эмнэлэгт үзүүлээд, эмийн жор авах нь хамгийн зөв."})
        elif "парацетамол" in message_lower:
            return jsonify({'text': "Парацетамол нь Эрүүл мэндийн даатгалын хөнгөлөлттэй эмийн жагсаалтад орсон бөгөөд 50% хөнгөлөлттэй. Эмчийн бичсэн жороор өрхийн эмнэлэг болон эмийн сангуудаас авах боломжтой."})
        elif message_lower == "гэрээт эмнэлгүүд" or message_lower == "эмд-ын гэрээт эмнэлгүүд":
            return jsonify({'text': "Эрүүл мэндийн даатгалын ерөнхий газар нь бүх аймаг, дүүргийн нэгдсэн эмнэлэг, төв эмнэлэг, өрхийн эмнэлэг болон 150 гаруй хувийн эмнэлэгтэй гэрээтэй. Энэ гэрээт эмнэлгүүдэд ЭМД-тай иргэд хөнгөлөлттэй үнээр эмчлүүлэх боломжтой. Улаанбаатар хотын болон орон нутгийн гэрээт эмнэлгүүдийн талаарх дэлгэрэнгүй мэдээллийг асууж болно."})
        elif message_lower == "улаанбаатар хотын эмнэлгүүд":
            return jsonify({'text': "Улаанбаатарт байршилтай гэрээт эмнэлгүүд: 1) Улсын 1-р төв эмнэлэг, 2) Улсын 2-р төв эмнэлэг, 3) Улсын 3-р төв эмнэлэг, 4) УНТЭ, 5) Ач Эмнэлэг, 6) Гранд Мед Эмнэлэг, 7) УБ Сонгдо, 8) Интермед, 9) SOS Медика, 10) ХСҮТ, 11) Хавдар судлалын үндэсний төв, 12) Эх, хүүхдийн эрүүл мэндийн үндэсний төв. Эдгээр эмнэлгүүдэд ЭМД-ын хөнгөлөлттэй үнээр үйлчлүүлэх боломжтой."})
        elif message_lower == "орон нутгийн эмнэлгүүд":
            return jsonify({'text': "Орон нутаг дахь ЭМД-ын гэрээт эмнэлгүүд: 1) Орхон аймгийн БОЭТ, 2) Увс аймгийн нэгдсэн эмнэлэг, 3) Дорноговь аймгийн нэгдсэн эмнэлэг, 4) Хэнтий аймгийн нэгдсэн эмнэлэг, 5) Дархан-Уул аймгийн нэгдсэн эмнэлэг, 6) Сэлэнгэ аймгийн нэгдсэн эмнэлэг, 7) Завхан аймгийн нэгдсэн эмнэлэг. Бүх аймгуудын нэгдсэн эмнэлгүүд болон сум дундын эмнэлгүүд ЭМД-тай гэрээтэй тул хөнгөлөлттэй үйлчилгээ авах боломжтой."})  
        elif message_lower == "хувийн эмнэлгүүд":
            return jsonify({'text': "ЭМД-тай гэрээт хувийн эмнэлгүүд: 1) ХСИС эмнэлэг, 2) Гранд Мед, 3) СОС Медика, 4) Интермед эмнэлэг, 5) Уу Сонгдо, 6) АЧ эмнэлэг, 7) Ди-Эм-Ди эмнэлэг, 8) Нарантуул эмнэлэг, 9) Мэдипас эмнэлэг, 10) Буурал Баг эмнэлэг, 11) Эмпати эмнэлэг, 12) Энхсүрэн эмнэлэг. Эдгээр эмнэлгүүд нь тодорхой нөхцлөөр ЭМД-ын хөнгөлөлттэй үйлчилгээ үзүүлдэг."})
        elif ("гэрээт" in message_lower and "эмнэлг" in message_lower) or ("эмнэлэг" in message_lower and "гэрээ" in message_lower) or ("эмнэлгүүд" in message_lower) or ("эмд-тэй" in message_lower) or ("жагсаалт" in message_lower and "эмнэлг" in message_lower) or ("хөнгөлөлттэй эмчлүүлж" in message_lower):
            return jsonify({'text': "Эрүүл мэндийн даатгалын ерөнхий газар нь бүх аймаг, дүүргийн нэгдсэн эмнэлэг, төв эмнэлэг, өрхийн эмнэлэг болон 150 гаруй хувийн эмнэлэгтэй гэрээтэй. Энэ гэрээт эмнэлгүүдэд ЭМД-тай иргэд хөнгөлөлттэй үнээр эмчлүүлэх боломжтой. Бүх гэрээт эмнэлгийн жагсаалтыг emd.gov.mn сайтын 'Гэрээт байгууллага' цэснээс харах боломжтой."})
        elif message_lower.find("дутуу сар") >= 0 or (message_lower.find("шалгах") >= 0 and message_lower.find("яаж") >= 0):
            return jsonify({'text': "Эрүүл мэндийн даатгалын шимтгэлийн дутуу саруудаа дараах сувгуудаар шалгах боломжтой: 1) www.emd.gov.mn сайтаар, 2) www.e-mongolia.mn сайт болон аппликейшнээр, 3) Ибаримт аппликейшн ашиглаж шалгах боломжтой."})
        elif "шимтгэл" in message_lower or "төлбөр" in message_lower or "хураамж" in message_lower or "хэмжээ" in message_lower or "хэд вэ" in message_lower:
            return jsonify({'text': "ЭМД-ын шимтгэлийн хэмжээ: 2025 оны 1-3 сар хүртэл сарын 13200 төгрөг, 4-р сараас эхлэн 15840 төгрөг болно. Ажил олгогч, даатгуулагч тус тус 2:1 харьцаагаар хуваан төлнө. Хувиараа хөдөлмөр эрхлэгч нь бүрэн дүнгээр төлнө."})
        elif message_lower == "эмийн үнийн хөнгөлөлт" or message_lower.find("эмийн үнийн хөнгөлөлт") >= 0:
            return jsonify({'text': "ЭМД-ын хөнгөлөлттэй эмийн хөнгөлөлтийн хувь хэмжээ: 1) A, B, C, D төрлийн эмнэлэгт чихрийн шижин, астма, сэтгэцийн эмгэг, хавдрын эмүүдэд 80-100% хөнгөлөлт үзүүлнэ, 2) Зүрх судасны, таталтын эсрэг, ревматоид артрит, глаукомын эмүүдэд 70% хөнгөлөлт үзүүлнэ, 3) Бусад халдварт өвчин, үрэвслийн эсрэг эмүүдэд 30-50% хөнгөлөлт үзүүлнэ. Хөнгөлөлтийн хувь хэмжээ нь эмийн үнэ болон оношоос хамаарна."})
        elif message_lower == "хөнгөлөлттэй эмийн жагсаалт" or message_lower.find("жагсаалт") >= 0 and message_lower.find("эм") >= 0:
            return jsonify({'text': "ЭМД-ын хөнгөлөлттэй эмийн жагсаалтын дагуу дараах эмүүд хамрагдана: 1) Зүрх судасны эмүүд - Эналаприл 70%, Берлиприл 70%, Энап 70%, 2) Халдварт өвчний эмүүд - Эритромицин 30%, 3) Уналт таталтын эсрэг эмүүд - Клоназепам 70%, Каннабидиол 70%, Клобазам 70%, 4) Глаукомын эмүүд - 50-70%, 5) Чихрийн шижин, хавдрын эмүүд - 80-100% хөнгөлөлттэй. Эмч танд зөв эмийн жор бичиж өгснөөр хөнгөлөлт эдлэх боломжтой."})
        elif message_lower == "зүрх судасны эмийн хөнгөлөлт":
            return jsonify({'text': "Зүрх судасны өвчний үед хэрэглэх хөнгөлөлттэй эмүүд: 1) Эналаприл - 70% хөнгөлөлттэй, 2) Энап - 70% хөнгөлөлттэй, 3) Берлиприл - 70% хөнгөлөлттэй, 4) Эналаприл Денк - 70% хөнгөлөлттэй, 5) Энам - 70% хөнгөлөлттэй, 6) Верапамил - 50% хөнгөлөлттэй, 7) Амлодипин - 50% хөнгөлөлттэй. Эмч танд зөв эмийн жор бичиж өгснөөр хөнгөлөлт эдлэх боломжтой."})
        elif message_lower == "чихрийн шижингийн эмийн хөнгөлөлт":
            return jsonify({'text': "Чихрийн шижин өвчний үед хэрэглэх хөнгөлөлттэй эмүүд: 1) Метформин - 90% хөнгөлөлттэй, 2) Глибенкламид - 90% хөнгөлөлттэй, 3) Диабетон MR - 90% хөнгөлөлттэй, 4) Глюкофаж - 90% хөнгөлөлттэй, 5) Глюкофаж XR - 90% хөнгөлөлттэй, 6) Инсулин - 100% хөнгөлөлттэй. Эмч танд зөв эмийн жор бичиж өгснөөр хөнгөлөлт эдлэх боломжтой."})
        elif message_lower == "астма, уушгины эмийн хөнгөлөлт":
            return jsonify({'text': "Астма, уушгины өвчний үед хэрэглэх хөнгөлөлттэй эмүүд: 1) Беклометазон - 80% хөнгөлөлттэй, 2) Флутиказон - 80% хөнгөлөлттэй, 3) Сальбутамол - 80% хөнгөлөлттэй, 4) Будесонид - 80% хөнгөлөлттэй, 5) Формотерол - 80% хөнгөлөлттэй, 6) Зафирон - 80% хөнгөлөлттэй, 7) Смбикорт - 80% хөнгөлөлттэй. Эмч танд зөв эмийн жор бичиж өгснөөр хөнгөлөлт эдлэх боломжтой."})
        elif ("хөнгөлөлт" in message_lower and "эм" in message_lower) or ("эмийн" in message_lower and "хөнгөлөлт" in message_lower) or ("өвчин" in message_lower and "эм" in message_lower):
            return jsonify({'text': "ЭМД-ын хөнгөлөлттэй эмийн жагсаалтад 600 гаруй нэр төрлийн эм орсон бөгөөд 30-100% хүртэлх хөнгөлөлттэй үнээр авах боломжтой. Эмч таны өвчнийг оношлон, тохирох эмийн жор бичиж өгөх бөгөөд, хөнгөлөлттэй эмүүдийг эмчийн жороор авах боломжтой. Жорд бичигдсэн хөнгөлөлттэй эмийг аливаа гэрээт эмийн сангаас авч болно."})
        elif message_lower.find("үйлчилгээ") >= 0 and (message_lower.find("юу") >= 0 or message_lower.find("ямар") >= 0 or message_lower.find("авах") >= 0 or message_lower.find("авч") >= 0 or message_lower.find("болох") >= 0):
            return jsonify({'text': "Эрүүл мэндийн даатгалаар дараах тусламж, үйлчилгээнүүдийг авах боломжтой: 1) Хэвтүүлэн эмчлэх тусламж үйлчилгээ (70-90% хөнгөлөлттэй), 2) Амбулаторийн тусламж үйлчилгээ (50% хөнгөлөлттэй), 3) Өндөр өртөгтэй оношилгоо, шинжилгээ (30-80% хөнгөлөлттэй), 4) Яаралтай тусламж (бүрэн хөнгөлөлттэй), 5) Түргэн тусламж (бүрэн хөнгөлөлттэй), 6) Телемедицин үйлчилгээ (50% хөнгөлөлттэй), 7) Өдрийн эмчилгээ үйлчилгээ (70% хөнгөлөлттэй), 8) Уламжлалт анагаах ухааны тусламж (40% хөнгөлөлттэй), 9) Сэргээн засах тусламж (40-70% хөнгөлөлттэй), 10) Хөнгөвчлөх тусламж (80% хөнгөлөлттэй), 11) Эмийн үнийн хөнгөлөлт (30-100% хөнгөлөлттэй)."})
        elif message_lower.find("тусламж") >= 0 and (message_lower.find("юу") >= 0 or message_lower.find("ямар") >= 0 or message_lower.find("авах") >= 0 or message_lower.find("авч") >= 0 or message_lower.find("болох") >= 0):
            return jsonify({'text': "Эрүүл мэндийн даатгалаар дараах тусламж, үйлчилгээнүүдийг авах боломжтой: 1) Хэвтүүлэн эмчлэх тусламж үйлчилгээ (70-90% хөнгөлөлттэй), 2) Амбулаторийн тусламж үйлчилгээ (50% хөнгөлөлттэй), 3) Өндөр өртөгтэй оношилгоо, шинжилгээ (30-80% хөнгөлөлттэй), 4) Яаралтай тусламж (бүрэн хөнгөлөлттэй), 5) Түргэн тусламж (бүрэн хөнгөлөлттэй), 6) Телемедицин үйлчилгээ (50% хөнгөлөлттэй), 7) Өдрийн эмчилгээ үйлчилгээ (70% хөнгөлөлттэй), 8) Уламжлалт анагаах ухааны тусламж (40% хөнгөлөлттэй), 9) Сэргээн засах тусламж (40-70% хөнгөлөлттэй), 10) Хөнгөвчлөх тусламж (80% хөнгөлөлттэй), 11) Эмийн үнийн хөнгөлөлт (30-100% хөнгөлөлттэй)."})
        elif "төлөх" in message_lower or "сувг" in message_lower or "хаанаас" in message_lower:
            return jsonify({'text': "Эрүүл мэндийн даатгалаа дараах сувгуудаар төлөх боломжтой: 1) И-Баримт гар утасны апп, 2) И-Баримт вэб сайтаар, 3) E-Mongolia аппликейшн, 4) Банкны салбар, 5) Банкны автомат машин (ATM), 6) Интернет банк."})
        elif "заавал" in message_lower or "нөхөн төлөх" in message_lower:
            return jsonify({'text': "Эрүүл мэндийн даатгалын тухай хуулиар Монгол улсын иргэн бүр эрүүл мэндийн албан журмын даатгалд заавал даатгуулах үүрэгтэй. Энэхүү даатгал нь эмнэлгийн зардлын төлбөрийг хөнгөвчилдөг."})
        elif "битүүмж" in message_lower:
            return jsonify({'text': "Битүүмж нь тухайн эрүүл мэндийн байгууллагад иргэн даатгуулагчийн үйлчлүүлж байгааг илэрхийлсэн мэдээлэл бөгөөд нээх, хаах нь тухайн эрүүл мэндийн байгууллагын хариуцах асуудал юм."})
        elif "сайн" in message_lower or "өдрийн мэнд" in message_lower:
            return jsonify({'text': "Сайн байна уу! Би Эрүүл Мэндийн Даатгалын бот байна. Танд хэрхэн туслах вэ?"})
        elif "даатгал гэж юу" in message_lower or "даатгал" in message_lower and "юу" in message_lower:
            return jsonify({'text': "Эрүүл мэндийн даатгал гэдэг нь иргэдийн эрүүл мэндийн тусламж үйлчилгээний зардлыг хуваалцах зорилготой нийгмийн даатгалын нэг хэлбэр юм. Энэ нь өвчин эмгэг, гэмтэл бэртлийн улмаас үүсэх эмнэлгийн тусламж үйлчилгээний зардлыг даатгуулагчид хөнгөвчлөх үүрэгтэй. Эрүүл мэндийн даатгалд хамрагдсан иргэд эмнэлэгт үзүүлэх, шинжилгээ өгөх, эмчилгээ хийлгэх, эм авах үеийн зардлаа хөнгөлөлттэйгөөр төлөх боломжтой."})
        elif "чадваргүй" in message_lower and "иргэд" in message_lower or "хөнгөлөлт үзүүлж" in message_lower:
            return jsonify({'text': "Эрүүл мэндийн даатгалын хуулийн дагуу дараах иргэдийн ЭМД-ыг төрөөс хариуцан төлдөг: 1) 0-18 насны хүүхэд, 2) Тэтгэврээс өөр тогтмол орлогогүй иргэн, 3) Нийгмийн халамжийн дэмжлэг шаардлагатай өрхийн гишүүн, 4) Хүүхдээ 2 нас (ихэр бол 3 нас) хүртэл өсгөж буй эцэг/эх, 5) Ял эдэлж буй ялтан. Эдгээр иргэд ЭМД төлөлгүйгээр эрүүл мэндийн тусламж үйлчилгээг авах боломжтой."})
        elif "оношилгоо" in message_lower or "шинжилгээ" in message_lower:
            return jsonify({'text': "Эрүүл мэндийн даатгалаар дараах оношилгоо, шинжилгээнүүдийг авах боломжтой: 1) Цусны ерөнхий шинжилгээ, 2) Шээсний шинжилгээ, 3) Биохимийн шинжилгээ, 4) Рентген, 5) Компьютер томограф (СТ), 6) Соронзон резонанст томограф (MRI), 7) Эхо кардиограф, 8) Дуран шинжилгээ. ЭМД-тай иргэд эдгээр шинжилгээнүүдийг 40-90% хөнгөлөлттэй хийлгэх боломжтой бөгөөд өрхийн эмчээс эмнэлгийн магадлагаа авсан байх шаардлагатай."})
        # If no direct match, use a comprehensive response
        else:
            return jsonify({'text': "Эрүүл мэндийн даатгал нь доорх тохиолдлуудад хамаардаг: 1) Эмнэлгийн тусламж, 2) Оношилгоо, шинжилгээ, 3) Эмчилгээний зардал, 4) Эмийн хөнгөлөлт. Иргэн та эмнэлгийн магадлагаатай бол ЭМД-тай гэрээт эмнэлгээр үйлчлүүлж, хөнгөлөлт эдлэх боломжтой. Тусламж шаардлагатай бол надаас тодорхой асуулт асууна уу."})
        
    except requests.exceptions.ConnectionError:
        logger.error("Could not connect to Rasa server")
        return jsonify({'text': 'Сервертэй холбогдож чадсангүй. Rasa сервер ажиллаж байгаа эсэхийг шалгана уу.'})
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        # Try to respond anyway even if there was an error with the learning component
        message_lower = user_message.lower()
        
        if "сайн" in message_lower or "өдрийн мэнд" in message_lower:
            return jsonify({'text': "Сайн байна уу! Би Эрүүл Мэндийн Даатгалын бот байна. Танд хэрхэн туслах вэ?"})
        elif "даатгал гэж юу" in message_lower:
            return jsonify({'text': "Эрүүл мэндийн даатгал гэдэг нь иргэдийн эрүүл мэндийн тусламж үйлчилгээний зардлыг хуваалцах зорилготой нийгмийн даатгалын нэг хэлбэр юм. Энэ нь өвчин эмгэг, гэмтэл бэртлийн улмаас үүсэх эмнэлгийн тусламж үйлчилгээний зардлыг даатгуулагчид хөнгөвчлөх үүрэгтэй."})
        elif "эмнэлгүүд" in message_lower or "хөнгөлөлттэй эмчлүүлж" in message_lower:
            return jsonify({'text': "Эрүүл мэндийн даатгалын ерөнхий газар нь бүх аймаг, дүүргийн нэгдсэн эмнэлэг, төв эмнэлэг, өрхийн эмнэлэг болон 150 гаруй хувийн эмнэлэгтэй гэрээтэй. Энэ гэрээт эмнэлгүүдэд ЭМД-тай иргэд хөнгөлөлттэй үнээр эмчлүүлэх боломжтой."})
        else:
            return jsonify({'text': "Эрүүл мэндийн даатгал нь доорх тохиолдлуудад хамаардаг: 1) Эмнэлгийн тусламж, 2) Оношилгоо, шинжилгээ, 3) Эмчилгээний зардал, 4) Эмийн хөнгөлөлт. Иргэн та эмнэлгийн магадлагаатай бол ЭМД-тай гэрээт эмнэлгээр үйлчлүүлж, хөнгөлөлт эдлэх боломжтой. Тусламж шаардлагатай бол надаас тодорхой асуулт асууна уу."})

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
        # Simplify to avoid DB schema errors - just save the question
        unanswered = UnansweredQuestion(question=question)
        db.session.add(unanswered)
        db.session.commit()
        
        # Log for future machine learning training purposes
        logger.info(f"Saved question for future learning: {question}")
        
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
