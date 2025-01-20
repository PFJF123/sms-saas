from flask import Flask, request, jsonify
from twilio.rest import Client
import openai
import os
import sys
import logging
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize OpenAI API key
openai.api_key = os.environ.get("OPENAI_API_KEY")

# Database setup
def init_database():
    try:
        # Try to get the Supabase connection URL
        db_url = os.environ.get('POSTGRES_URL_NON_POOLING')
        if not db_url:
            logger.warning("Database URL not found, attempting to construct from components...")
            db_host = os.environ.get('POSTGRES_HOST', 'localhost')
            db_user = os.environ.get('POSTGRES_USER', 'postgres')
            db_password = os.environ.get('POSTGRES_PASSWORD')
            db_name = os.environ.get('POSTGRES_DATABASE', 'verceldb')
            
            if not db_password:
                raise RuntimeError("Database password not found in environment variables")
            
            db_url = f"postgresql://{db_user}:{db_password}@{db_host}/{db_name}"
        
        logger.info("Connecting to database...")
        engine = create_engine(db_url)
        
        # Test connection
        with engine.connect() as conn:
            conn.execute("SELECT 1")
            logger.info("Database connection successful")
        
        return engine
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        return None

# Initialize database connection
engine = init_database()
if not engine:
    logger.error("Failed to initialize database, using SQLite fallback")
    engine = create_engine("sqlite:///users.db")

Base = declarative_base()
Session = sessionmaker(bind=engine)

# User model
class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    phone_number = Column(String, unique=True, nullable=False)
    is_active = Column(Boolean, default=False)
    subscription_status = Column(String, default='trial')
    onboarding_complete = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_interaction = Column(DateTime)

# Create tables
try:
    Base.metadata.create_all(engine)
    logger.info("Database tables created successfully")
except Exception as e:
    logger.error(f"Failed to create database tables: {str(e)}")

def get_or_create_user(phone_number):
    session = Session()
    try:
        user = session.query(User).filter_by(phone_number=phone_number).first()
        logger.info(f"Found existing user: {phone_number}")
        
        if not user:
            logger.info(f"Creating new user: {phone_number}")
            user = User(phone_number=phone_number)
            session.add(user)
            session.commit()
        
        return user
    except Exception as e:
        logger.error(f"Error in get_or_create_user: {str(e)}")
        session.rollback()
        return None
    finally:
        session.close()

def update_user_interaction(user):
    if not user:
        logger.error("Cannot update interaction for None user")
        return
    
    session = Session()
    try:
        user.last_interaction = datetime.utcnow()
        session.commit()
        logger.info(f"Updated last interaction for user: {user.phone_number}")
    except Exception as e:
        logger.error(f"Error updating user interaction: {str(e)}")
        session.rollback()
    finally:
        session.close()

def handle_onboarding(user, message):
    if not user:
        logger.error("Cannot handle onboarding for None user")
        return None
    
    if not user.onboarding_complete:
        logger.info(f"Starting onboarding for user: {user.phone_number}")
        return """Welcome to SMS Calendar Assistant! 🎉
Reply with:
1 - Start free trial
2 - Learn more
3 - Talk to support"""
    return None

@app.route("/", methods=["GET"])
def home():
    status = {
        "status": "running",
        "database": {
            "connected": bool(engine),
            "url_configured": bool(os.environ.get('POSTGRES_URL_NON_POOLING')),
            "components_configured": {
                "host": bool(os.environ.get('POSTGRES_HOST')),
                "user": bool(os.environ.get('POSTGRES_USER')),
                "password": bool(os.environ.get('POSTGRES_PASSWORD')),
                "database": bool(os.environ.get('POSTGRES_DATABASE'))
            }
        }
    }
    return jsonify(status)

@app.route("/api/webhook", methods=["POST"])
def webhook():
    try:
        # Get message details
        incoming_msg = request.values.get("Body", "").strip()
        from_number = request.values.get("From", "")
        
        logger.info(f"Received message: {incoming_msg} from {from_number}")
        
        if not incoming_msg or not from_number:
            logger.error("Missing message or sender information")
            return jsonify({"error": "Missing message or sender"}), 400
        
        # Get or create user
        user = get_or_create_user(from_number)
        if not user:
            logger.error("Failed to get or create user")
            return jsonify({"error": "Database error"}), 500
            
        update_user_interaction(user)
        
        # Check for onboarding
        onboarding_response = handle_onboarding(user, incoming_msg)
        if onboarding_response:
            # Send onboarding message via Twilio
            twilio_client = Client(
                os.environ.get("TWILIO_ACCOUNT_SID"),
                os.environ.get("TWILIO_AUTH_TOKEN")
            )
            
            message = twilio_client.messages.create(
                body=onboarding_response,
                from_=os.environ.get("TWILIO_PHONE_NUMBER"),
                to=from_number
            )
            
            logger.info(f"Sent onboarding message to {from_number}")
            return jsonify({"status": "success", "message_sid": message.sid})
        
        try:
            # Get OpenAI response
            completion = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful calendar assistant responding via SMS. Keep responses concise and friendly."},
                    {"role": "user", "content": incoming_msg}
                ]
            )
            
            ai_response = completion.choices[0].message["content"]
            logger.info(f"OpenAI response: {ai_response}")
            
            # Send response via Twilio client
            twilio_client = Client(
                os.environ.get("TWILIO_ACCOUNT_SID"),
                os.environ.get("TWILIO_AUTH_TOKEN")
            )
            
            message = twilio_client.messages.create(
                body=ai_response,
                from_=os.environ.get("TWILIO_PHONE_NUMBER"),
                to=from_number
            )
            
            logger.info(f"Sent message: {message.sid}")
            return jsonify({"status": "success", "message_sid": message.sid})
            
        except Exception as e:
            logger.error(f"Processing error: {str(e)}")
            # Send error message via Twilio client
            twilio_client = Client(
                os.environ.get("TWILIO_ACCOUNT_SID"),
                os.environ.get("TWILIO_AUTH_TOKEN")
            )
            
            message = twilio_client.messages.create(
                body="I apologize, but I am having trouble generating a response. Please try again.",
                from_=os.environ.get("TWILIO_PHONE_NUMBER"),
                to=from_number
            )
            
            return jsonify({"status": "error", "error": str(e)}), 500
            
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Required for Vercel
app.debug = True 