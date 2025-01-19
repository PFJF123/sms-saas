# SMS Calendar Assistant (SaaS)

A SaaS application that provides an AI-powered calendar assistant via SMS, with user management and subscription features.

## Features

- SMS-based interaction with AI calendar assistant
- User management and onboarding flow
- Subscription handling (trial/paid)
- Database persistence for user data
- Secure environment configuration

## Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   ```
   OPENAI_API_KEY=your_openai_api_key
   TWILIO_ACCOUNT_SID=your_twilio_account_sid
   TWILIO_AUTH_TOKEN=your_twilio_auth_token
   TWILIO_PHONE_NUMBER=your_twilio_phone_number
   DATABASE_URL=your_database_url  # Optional, defaults to SQLite
   ```

4. Run locally:
   ```bash
   python api/webhook.py
   ```

## Deployment

The application is configured for deployment on Vercel:

1. Install Vercel CLI:
   ```bash
   npm i -g vercel
   ```

2. Deploy:
   ```bash
   vercel
   ```

3. Set environment variables in Vercel dashboard

## Development

- The main application logic is in `api/webhook.py`
- User management is handled through SQLAlchemy models
- Onboarding flow guides users through setup and trial activation
- OpenAI integration provides AI responses
- Twilio handles SMS communication

## License

MIT