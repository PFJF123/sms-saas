# SMS AI Assistant (SaaS)

A SaaS application that provides AI chat capabilities via SMS with user management and subscription features.

## Features

- User registration and onboarding via SMS
- Timezone configuration
- Subscription management
- AI chat powered by OpenAI

## Environment Variables Required

- `OPENAI_API_KEY`: Your OpenAI API key
- `TWILIO_ACCOUNT_SID`: Your Twilio Account SID
- `TWILIO_AUTH_TOKEN`: Your Twilio Auth Token
- `TWILIO_PHONE_NUMBER`: Your Twilio phone number
- `DATABASE_URL`: PostgreSQL database URL (provided by Vercel)

## Development

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set up environment variables
4. Deploy to Vercel
5. Configure Twilio webhook URL to: `https://[your-vercel-url]/api/webhook`

## User Flow

1. User sends first message
2. System starts onboarding:
   - Asks for name
   - Configures timezone
   - Sets up trial/subscription
3. User can start chatting with AI