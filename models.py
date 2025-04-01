from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

db = SQLAlchemy()

# Define models
class Hospital(db.Model):
    __tablename__ = 'hospitals'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    city = Column(String(100), nullable=False)
    insurance_contract = Column(Boolean, default=False)
    address = Column(String(255))
    phone = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Hospital {self.name}>"

class Medicine(db.Model):
    __tablename__ = 'medicines'
    
    id = Column(Integer, primary_key=True)
    icd10_code = Column(String(20), nullable=False, index=True)
    icd10_name = Column(String(255), nullable=False)
    tablet_id = Column(Integer)
    tablet_name_mon = Column(String(255))
    tablet_name_sales = Column(String(255))
    unit_price = Column(Float)
    unit_discount = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Medicine {self.tablet_name_sales} for {self.icd10_code}>"

class UnansweredQuestion(db.Model):
    __tablename__ = 'unanswered_questions'
    
    id = Column(Integer, primary_key=True)
    question = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_processed = Column(Boolean, default=False)
    # Add fields for machine learning
    keywords = Column(Text, nullable=True)
    frequency = Column(Integer, default=1)
    topic_classification = Column(String(100), nullable=True)
    response_effectiveness = Column(Integer, nullable=True)  # User feedback on how good the answer was
    
    def __repr__(self):
        return f"<UnansweredQuestion {self.question[:30]}...>"
