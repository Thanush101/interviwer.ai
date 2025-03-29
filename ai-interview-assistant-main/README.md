# AI Interview Assistant

An AI-powered interview assistant that uses ElevenLabs for voice synthesis and real-time conversation.

## Features

- Real-time voice conversation with AI interviewer
- 7-question interview limit
- Glowing avatar animation during conversation
- Cancel interview functionality
- Modern web interface with responsive design
- WebSocket-based real-time communication

## Demo

[Live Demo](https://ai-interview-assistant.vercel.app)

## Setup

1. Clone the repository:
```bash
git clone https://github.com/Thanush101/ai-interview-assistant.git
cd ai-interview-assistant
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python 11labs_v3.py
```

## Environment Variables

Make sure to set up the following environment variables:
- ELEVENLABS_API_KEY
- OPENAI_API_KEY

## Technologies Used

- Python
- Flask
- ElevenLabs API
- WebSocket
- HTML/CSS/JavaScript