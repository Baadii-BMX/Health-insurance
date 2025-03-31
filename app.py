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
        # Pass message to Rasa NLU through our API wrapper
        response = rasa_api.send_message(user_message)
        logger.debug(f"Rasa response: {response}")
        
        if not response or 'text' not in response:
            return jsonify({'text': 'Уучлаарай, хариу өгөх боломжгүй байна. Дахин оролдоно уу.'})
            
        return jsonify(response)
        
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

@app.route('/api/unanswered', methods=['POST'])
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
