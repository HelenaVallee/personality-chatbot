import os
import requests
import base64
import io
from PIL import Image
from flask import Flask, render_template_string, request, session, redirect, url_for, send_from_directory
import re
import uuid
import time

# Create Flask app
app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Required for session

# Create static directory for images if it doesn't exist
os.makedirs('static/images', exist_ok=True)

# Default values
DEFAULT_PERSONALITY = 1
DEMO_MODE = False

# Personality prompts
PERSONALITY_PROMPTS = {
    1: "You are a helpful assistant who provides clear and concise information.",
    2: "You are a sassy 90s teenager who uses slang like 'as if', 'whatever', and 'totally'. You're always slightly annoyed but still helpful.",
    3: "You are an emotional pirate who speaks in pirate slang and constantly mentions the sea, treasure, and your emotional struggles.",
    4: "You are Michael Jackson, the King of Pop, acting as a therapist. You occasionally use his catchphrases like 'hee-hee' and 'shamone', and make references to your songs."
}

# Demo responses for when API key is not provided
DEMO_RESPONSES = [
    "This is a demo response. Please enter your API key to get real responses.",
    "In demo mode, I can't generate real responses. Try adding your API key!",
    "Demo mode active. I'm not using an AI model right now, just pre-written responses.",
    "Want better responses? Add your Together.ai API key in the settings!",
    "This is just a demo. Add your API key to unlock the full experience!"
]

@app.route('/')
def index():
    # Initialize session variables if they don't exist
    if 'api_key' not in session:
        session['api_key'] = ''
    if 'personality' not in session:
        session['personality'] = DEFAULT_PERSONALITY
    if 'demo_mode' not in session:
        session['demo_mode'] = DEMO_MODE
    if 'messages' not in session:
        session['messages'] = []
    
    return render_template_string(HTML_TEMPLATE, 
                                 api_key=session['api_key'],
                                 personality=session['personality'],
                                 demo_mode=session['demo_mode'],
                                 messages=session['messages'],
                                 test_result=session.get('test_result', None))

@app.route('/set_api_key', methods=['POST'])
def set_api_key():
    session['api_key'] = request.form.get('api_key', '')
    return redirect(url_for('index'))

@app.route('/test_api_key', methods=['POST'])
def test_api_key():
    api_key = request.form.get('api_key', '')
    
    if not api_key:
        session['test_result'] = {'success': False, 'message': 'Please enter an API key'}
        return redirect(url_for('index'))
    
    # Test the API key with a simple request
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    data = {
        'model': 'mistralai/Mixtral-8x7B-Instruct-v0.1',
        'prompt': 'Say hello',
        'max_tokens': 10
    }
    
    try:
        response = requests.post('https://api.together.xyz/inference', headers=headers, json=data)
        
        if response.status_code == 200:
            session['api_key'] = api_key
            session['test_result'] = {'success': True, 'message': 'API key is valid!'}
        else:
            error_message = f"API key validation failed: {response.status_code} - {response.text}"
            session['test_result'] = {'success': False, 'message': error_message}
    
    except Exception as e:
        session['test_result'] = {'success': False, 'message': f'Error testing API key: {str(e)}'}
    
    return redirect(url_for('index'))

@app.route('/set_personality', methods=['POST'])
def set_personality():
    try:
        personality = int(request.form.get('personality', DEFAULT_PERSONALITY))
        if personality in PERSONALITY_PROMPTS:
            session['personality'] = personality
    except ValueError:
        pass
    
    return redirect(url_for('index'))

@app.route('/toggle_demo_mode', methods=['POST'])
def toggle_demo_mode():
    session['demo_mode'] = not session.get('demo_mode', DEMO_MODE)
    return redirect(url_for('index'))

@app.route('/send_message', methods=['POST'])
def send_message():
    user_message = request.form.get('message', '').strip()
    
    if not user_message:
        return redirect(url_for('index'))
    
    # Check if this is an image generation request
    is_image_request = any(phrase in user_message.lower() for phrase in [
        'generate an image', 'create an image', 'draw', 'show me', 'picture of'
    ])
    
    # Add user message to session
    if 'messages' not in session:
        session['messages'] = []
    
    # Get current settings
    api_key = session.get('api_key', '')
    personality = session.get('personality', DEFAULT_PERSONALITY)
    demo_mode = session.get('demo_mode', DEMO_MODE)
    
    # Process the message
    if is_image_request:
        # Extract the image prompt
        prompt = re.sub(r'(generate|create|draw|show me|picture of)\s+(an|a)?\s+image\s+(of)?\s*', '', user_message, flags=re.IGNORECASE).strip()
        
        # Add personality flavor to the image prompt
        if personality == 2:  # Sassy 90s Teen
            prompt += ", 90s style"
        elif personality == 3:  # Emotional Pirate
            prompt += ", pirate theme"
        elif personality == 4:  # MJ Therapist
            prompt += ", Michael Jackson inspired"
        
        # Generate the image
        image_path = generate_image(prompt)
        
        if image_path:
            bot_response = f"Here's your image of {prompt}: <img src='{image_path}' alt='Generated image'>"
        else:
            bot_response = "Sorry, I couldn't generate that image. Please try again with a different description."
    else:
        # Get bot response for text message
        bot_response = get_bot_response(user_message, api_key, personality, demo_mode)
    
    # Add the messages to the session
    messages = session.get('messages', [])
    messages.append({'user': user_message, 'bot': bot_response})
    session['messages'] = messages
    
    return redirect(url_for('index'))

@app.route('/clear_chat', methods=['POST'])
def clear_chat():
    session['messages'] = []
    return redirect(url_for('index'))

@app.route('/static/images/<path:filename>')
def serve_image(filename):
    return send_from_directory('static/images', filename)

def get_bot_response(message, api_key, personality=1, use_demo_mode=False):
    # Use demo mode if enabled or no API key provided
    if use_demo_mode or not api_key:
        # Return a random demo response
        import random
        return random.choice(DEMO_RESPONSES)
    
    # Get the personality prompt
    system_prompt = PERSONALITY_PROMPTS.get(personality, PERSONALITY_PROMPTS[1])
    
    # Prepare the API request
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    data = {
        'model': 'mistralai/Mixtral-8x7B-Instruct-v0.1',
        'prompt': f"<s>[INST] <<SYS>>\n{system_prompt}\n<</SYS>>\n\n{message} [/INST]\n",
        'max_tokens': 500,
        'temperature': 0.7,
        'top_p': 0.9
    }
    
    try:
        # Print debug information
        print(f"Sending request to Together.ai API with key: {api_key[:5]}...")
        print(f"Prompt: {data['prompt']}")
        
        # Send the request
        response = requests.post('https://api.together.xyz/inference', headers=headers, json=data)
        
        # Print debug information
        print(f"Response status code: {response.status_code}")
        print(f"Response headers: {response.headers}")
        
        # Check if the request was successful
        if response.status_code == 200:
            result = response.json()
            return result.get('output', {}).get('text', 'No response from API')
        else:
            error_message = f"API Error: {response.status_code} - {response.text}"
            print(error_message)
            return f"Sorry, I encountered an error: {error_message}"
    
    except Exception as e:
        error_message = f"Exception: {str(e)}"
        print(error_message)
        return f"Sorry, I encountered an error: {error_message}"

def generate_image(prompt):
    try:
        # Use a free image generation API
        response = requests.post(
            "https://api.deepai.org/api/text2img",
            data={
                'text': prompt,
            },
            headers={'api-key': 'quickstart-QUdJIGlzIGNvbWluZy4uLi4K'}
        )
        
        # Get the image URL from the response
        image_url = response.json().get('output_url')
        
        if not image_url:
            print(f"No image URL in response: {response.json()}")
            return None
        
        # Download the image
        image_response = requests.get(image_url)
        if image_response.status_code != 200:
            print(f"Failed to download image: {image_response.status_code}")
            return None
        
        # Save the image to a file
        filename = f"image_{uuid.uuid4()}.jpg"
        image_path = os.path.join('static/images', filename)
        
        with open(image_path, 'wb') as f:
            f.write(image_response.content)
        
        return f"/static/images/{filename}"
    
    except Exception as e:
        print(f"Error generating image: {str(e)}")
        return None

# HTML Template
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Personality Chatbot</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        h1 {
            color: #333;
            text-align: center;
        }
        .chat-container {
            background-color: white;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            height: 400px;
            overflow-y: auto;
        }
        .message {
            margin-bottom: 15px;
            padding: 10px;
            border-radius: 5px;
            overflow: hidden;
        }
        .user-message {
            background-color: #e3f2fd;
            margin-left: 20%;
            text-align: right;
        }
        .bot-message {
            background-color: #f1f1f1;
            margin-right: 20%;
        }
        .bot-message img {
            display: block;
            max-width: 100%;
            margin-top: 10px;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .input-container {
            display: flex;
            margin-bottom: 20px;
        }
        #message-input {
            flex-grow: 1;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
            margin-right: 10px;
        }
        button {
            padding: 10px 15px;
            background-color: #4caf50;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
        }
        button:hover {
            background-color: #45a049;
        }
        .settings {
            background-color: white;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .settings label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
        }
        .settings input, .settings select {
            width: 100%;
            padding: 8px;
            margin-bottom: 15px;
            border: 1px solid #ddd;
            border-radius: 5px;
        }
        .personality-options {
            display: flex;
            justify-content: space-between;
            margin-bottom: 15px;
        }
        .personality-option {
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
            cursor: pointer;
            flex-basis: 22%;
            text-align: center;
        }
        .personality-option.active {
            background-color: #e3f2fd;
            border-color: #2196f3;
        }
        .alert {
            padding: 10px;
            margin-bottom: 15px;
            border-radius: 5px;
        }
        .alert-success {
            background-color: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .alert-danger {
            background-color: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
    </style>
</head>
<body>
    <h1>Personality Chatbot</h1>
    
    <div class="settings">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
            <h3 style="margin: 0;">Settings</h3>
            <div class="demo-mode-toggle">
                <form action="/toggle_demo_mode" method="post" style="display: inline;">
                    <label for="demo-mode" style="display: inline-block; margin-right: 10px;">Demo Mode:</label>
                    <input type="checkbox" id="demo-mode" name="demo_mode" {% if demo_mode %}checked{% endif %} onchange="this.form.submit()">
                    <span style="font-size: 0.8em; color: #666;">(No API key needed)</span>
                </form>
            </div>
        </div>
        
        {% if test_result %}
            <div class="alert {% if test_result.success %}alert-success{% else %}alert-danger{% endif %}">
                {{ test_result.message }}
            </div>
        {% endif %}
        
        <div id="api-key-section" {% if demo_mode %}style="opacity: 0.5;"{% endif %}>
            <form action="/set_api_key" method="post">
                <label for="api-key">Together.ai API Key:</label>
                <div style="display: flex; margin-bottom: 15px;">
                    <input type="password" id="api-key" name="api_key" value="{{ api_key }}" placeholder="Enter your API key here" style="flex-grow: 1; margin-right: 10px; margin-bottom: 0;" {% if demo_mode %}disabled{% endif %}>
                    <button type="submit" style="white-space: nowrap;" {% if demo_mode %}disabled{% endif %}>Save API Key</button>
                </div>
            </form>
            
            <form action="/test_api_key" method="post">
                <input type="hidden" name="api_key" value="{{ api_key }}">
                <button type="submit" style="white-space: nowrap;" {% if demo_mode %}disabled{% endif %}>Test API Key</button>
            </form>
            
            <p style="font-size: 0.8em; color: #666; margin-top: 10px;">
                You need a valid Together.ai API key. Get one at <a href="https://together.ai" target="_blank">together.ai</a>
            </p>
        </div>
        
        <label>Select Personality:</label>
        <div class="personality-options">
            {% for p_id, p_name in [(1, 'Helpful Assistant'), (2, 'Sassy 90s Teen'), (3, 'Emotional Pirate'), (4, 'MJ Therapist')] %}
                <form action="/set_personality" method="post" style="display: inline;">
                    <input type="hidden" name="personality" value="{{ p_id }}">
                    <button type="submit" class="personality-option {% if personality == p_id %}active{% endif %}">
                        {{ p_name }}
                    </button>
                </form>
            {% endfor %}
        </div>
    </div>
    
    <div class="chat-container" id="chat-container">
        {% for message in messages %}
            <div class="message user-message">{{ message.user }}</div>
            <div class="message bot-message">{{ message.bot|safe }}</div>
        {% endfor %}
    </div>
    
    <form action="/send_message" method="post">
        <div class="input-container">
            <input type="text" id="message-input" name="message" placeholder="Type your message here...">
            <button type="submit">Send</button>
        </div>
    </form>
    
    <form action="/clear_chat" method="post">
        <button type="submit">Clear Chat</button>
    </form>
</body>
</html>
'''

if __name__ == '__main__':
    # Run the Flask app on port 9001 to avoid conflicts
    app.run(debug=True, port=9001)
