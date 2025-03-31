import re
import logging
from datetime import datetime
from models import UnansweredQuestion, db

logger = logging.getLogger(__name__)

class LearningEngine:
    """
    Implements a machine learning capability for the chatbot
    that analyzes user questions, finds patterns, and gradually improves responses.
    """
    
    def __init__(self):
        self.common_words = set(['би', 'та', 'миний', 'танд', 'таны', 'юу', 'ямар', 'хэрхэн', 'яаж', 'хаана', 'хэзээ', 'хэд'])
        
    def extract_keywords(self, text):
        """Extract meaningful keywords from a question"""
        # Remove punctuation and convert to lowercase
        text = re.sub(r'[^\w\s]', '', text.lower())
        # Split into words
        words = text.split()
        # Filter out common words
        keywords = [word for word in words if word not in self.common_words and len(word) > 2]
        return keywords
    
    def classify_topic(self, keywords):
        """Determine what topic this question belongs to"""
        topic_keywords = {
            'эмнэлэг': ['эмнэлэг', 'эмч', 'үзлэг', 'тусламж', 'эмчилгээ', 'гэрээт'],
            'эм': ['эм', 'жор', 'уух', 'хөнгөлөлт', 'хөнгөлөлттэй', 'эмийн', 'жагсаалт'],
            'шимтгэл': ['шимтгэл', 'төлбөр', 'төлөх', 'хураамж', 'хэмжээ', 'хэд'],
            'үйлчилгээ': ['үйлчилгээ', 'авах', 'эдлэх', 'боломжтой', 'оношилгоо', 'шинжилгээ'],
            'өвчин': ['өвчин', 'ходоод', 'зүрх', 'ханиад', 'томуу', 'шинж', 'эмгэг']
        }
        
        # Count keyword matches for each topic
        topic_scores = {topic: 0 for topic in topic_keywords}
        
        for word in keywords:
            for topic, topic_words in topic_keywords.items():
                if word in topic_words:
                    topic_scores[topic] += 1
        
        # Find the topic with highest score
        max_score = 0
        best_topic = 'ерөнхий'  # Default topic
        
        for topic, score in topic_scores.items():
            if score > max_score:
                max_score = score
                best_topic = topic
                
        return best_topic
    
    def learn_from_question(self, question):
        """Process a new question and extract learning data"""
        keywords = self.extract_keywords(question)
        topic = self.classify_topic(keywords)
        
        # Store keywords as string
        keywords_str = ", ".join(keywords)
        
        # Check for similar questions
        similar_questions = UnansweredQuestion.query.filter(
            UnansweredQuestion.question.ilike(f'%{question[:15]}%')
        ).all()
        
        if similar_questions:
            # Update frequency of similar questions
            for sq in similar_questions:
                sq.frequency += 1
                db.session.add(sq)
            db.session.commit()
            logger.info(f"Updated frequency for {len(similar_questions)} similar questions")
        
        # Create new question for learning
        new_question = UnansweredQuestion(
            question=question,
            keywords=keywords_str,
            topic_classification=topic,
            created_at=datetime.utcnow()
        )
        
        try:
            db.session.add(new_question)
            db.session.commit()
            logger.info(f"Added new question to learning database: {question[:30]}...")
            return True
        except Exception as e:
            logger.error(f"Error saving question for learning: {e}")
            db.session.rollback()
            return False
            
    def get_popular_topics(self, limit=5):
        """Return the most frequently asked about topics"""
        try:
            # Get questions grouped by topic with counts
            topic_counts = db.session.query(
                UnansweredQuestion.topic_classification,
                db.func.count(UnansweredQuestion.id).label('count')
            ).group_by(UnansweredQuestion.topic_classification).order_by(
                db.desc('count')
            ).limit(limit).all()
            
            return topic_counts
        except Exception as e:
            logger.error(f"Error retrieving popular topics: {e}")
            return []
            
    def get_feedback_effectiveness(self):
        """Analyze how effective the bot's responses are based on user feedback"""
        try:
            # Calculate average effectiveness score
            avg_score = db.session.query(
                db.func.avg(UnansweredQuestion.response_effectiveness)
            ).filter(UnansweredQuestion.response_effectiveness.isnot(None)).scalar()
            
            if avg_score:
                return round(avg_score, 2)
            return 0
        except Exception as e:
            logger.error(f"Error calculating effectiveness: {e}")
            return 0

# Create a global instance for use in the application
learning_engine = LearningEngine()