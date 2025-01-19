from flask import Flask, request, jsonify
from twilio.rest import Client
import openai
import os
import sys
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

app = Flask(__name__)

# Initialize OpenAI API key
openai.api_key = os.environ.get("OPENAI_API_KEY")

# Database setup
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///users.db")
engine = create_engine(DATABASE_URL)
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
Base.metadata.create_all(engine)

def get_or_create_user(phone_number):
    session = Session()
    user = session.query(User).filter_by(phone_number=phone_number).first()
    
    if not user:
        user = User(phone_number=phone_number)
        session.add(user)
        session.commit()
    
    return user

def update_user_interaction(user):
    session = Session()
    user.last_interaction = datetime.utcnow()
    session.commit()

def handle_onboarding(user, message):
    if not user.onboarding_complete:
        # Welcome message for new users
        return """Welcome to SMS Calendar Assistant! 🎉
Reply with:
1 - Start free trial
2 - Learn more
3 - Talk to support"""
    return None

@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "running"})

@app.route("/api/webhook", methods=["POST"])
def webhook():
    try:
        # Get message details
        incoming_msg = request.values.get("Body", "").strip()
        from_number = request.values.get("From", "")
        
        print(f"Received message: {incoming_msg} from {from_number}", file=sys.stderr)
        
        if not incoming_msg or not from_number:
            print("Missing message or sender information", file=sys.stderr)
            return jsonify({"error": "Missing message or sender"}), 400
        
        # Get or create user
        user = get_or_create_user(from_number)
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
            print(f"OpenAI response: {ai_response}", file=sys.stderr)
            
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
            
            print(f"Sent message: {message.sid}", file=sys.stderr)
            return jsonify({"status": "success", "message_sid": message.sid})
            
        except Exception as e:
            print(f"Processing error: {str(e)}", file=sys.stderr)
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
        print(f"Webhook error: {str(e)}", file=sys.stderr)
        return jsonify({"error": str(e)}), 500

# Required for Vercel
app.debug = True 