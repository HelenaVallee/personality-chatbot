# Personality Chatbot with Flask

This is a web-based chatbot application that uses Together.ai's API to create different AI personalities. It's built with Flask for a clean, user-friendly interface and includes image generation capabilities.

## Features

- Chat with 4 different AI personalities:
  1. Helpful Assistant
  2. Sassy 90s Teen
  3. Emotional Pirate
  4. Michael Jackson Therapist
- Web-based interface with Flask
- Secure API key handling
- Image generation capabilities
- Rate limit handling

## Setup

1. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

2. Set up your Together.ai API key:
   - Enter your API key directly in the web interface and click 'Test API Key'

3. Run the application:
   ```
   python chatbot_app.py
   ```

4. Open the provided URL in your browser (typically http://127.0.0.1:9007)

5. To reset the session and start fresh:
   - Visit http://127.0.0.1:9007/reset

## How It Works

The application uses Together.ai's API with the DeepSeek R1 model to generate responses based on different personality prompts. The web interface is built with Flask, allowing for an interactive chat experience. It also uses the DeepAI API for image generation when users request images.

## Requirements

- Python 3.7+
- Flask
- Requests
- Pillow (for image handling)
- python-dotenv
