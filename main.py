import os
import requests
import base64
import io
from PIL import Image
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, send_from_directory
from dotenv import load_dotenv
import re
import uuid
import json
import time

# Load environment variables from .env file
load_dotenv()

# Simple system prompts for each chatbot mode
system_prompts = {
    1: "You are a helpful assistant.",
    2: "You are a sassy 90s teen who answers with attitude.",
    3: "You are a pirate who loves talking about emotions.",
    4: "You are a therapist chatbot who only speaks in Michael Jackson quotes."
}

# Get API key from environment variable
default_api_key = os.getenv("TOGETHER_API_KEY", "")

app = Flask(__name__)
app.secret_key = os.urandom(24)  # For session management

# Demo responses for when no API key is available
demo_responses = {
    1: [  # Helpful Assistant
        "I'd be happy to help with that! Let me know if you need more information.",
        "That's an interesting question. Here's what I know about it...",
        "I can certainly assist with that. Here are some suggestions...",
        "Great question! The answer depends on several factors...",
    ],
    2: [  # Sassy 90s Teen
        "Ugh, whatever! As if I would know that. But fine, I guess...",
        "That is SO lame. But here's the deal...",
        "*eye roll* Seriously? OK, if you MUST know...",
        "Dude, that's actually kinda cool. Don't tell anyone I said that though!",
    ],
    3: [  # Emotional Pirate
        "Arr, me heart swells with joy at yer question! I be feelin' excited to share...",
        "Blimey! That question brings a tear to me eye. I be feelin' nostalgic about...",
        "Shiver me timbers! I be overwhelmed with emotion! Let me tell ye...",
        "By Davy Jones' locker, I be feelin' anxious about that! But here's what I know...",
    ],
    4: [  # MJ Therapist
        "You are not alone. Remember, you've got to be starting something!",
        "Don't stop 'til you get enough information about this topic. Here's what I know...",
        "It doesn't matter if you're black or white, the answer to your question is...",
        "Heal the world with this knowledge: the way you make me feel is that...",
    ]
}

def generate_image(prompt):
    """Generate an image using a public API"""
    try:
        # Using a free public API for image generation
        api_url = "https://api.deepai.org/api/text2img"
        headers = {
            'api-key': 'quickstart-QUdJIGlzIGNvbWluZy4uLi4K'  # Free API key for testing
        }
        data = {
            'text': prompt,
        }
        
        print(f"DEBUG - Sending image generation request for prompt: {prompt}")
        response = requests.post(api_url, headers=headers, data=data)
        response.raise_for_status()
        
        # Get the image URL from the response
        result = response.json()
        if 'output_url' in result:
            image_url = result['output_url']
            print(f"DEBUG - Image generated successfully: {image_url}")
            
            # Download the image
            img_response = requests.get(image_url)
            img_response.raise_for_status()
            
            # Save the image with a unique filename
            filename = f"generated_{uuid.uuid4()}.jpg"
            filepath = os.path.join(IMAGE_DIR, filename)
            
            with open(filepath, 'wb') as f:
                f.write(img_response.content)
            
            # Return the local path to the image
            return f"/static/images/{filename}"
        else:
            print(f"DEBUG - Image generation failed: {result}")
            return None
    except Exception as e:
        print(f"DEBUG - Error generating image: {str(e)}")
        return None

def check_for_image_request(message):
    """Check if the message is requesting an image generation"""
    # List of patterns that might indicate an image generation request
    image_request_patterns = [
        r"(?i)generate an image",
        r"(?i)create an image",
        r"(?i)make an image",
        r"(?i)draw",
        r"(?i)show me",
        r"(?i)picture of",
        r"(?i)image of"
    ]
    
    for pattern in image_request_patterns:
        if re.search(pattern, message):
            # Extract the image description - everything after the matched pattern
            match = re.search(pattern, message)
            start_idx = match.end()
            image_description = message[start_idx:].strip()
            
            # If no specific description, use the whole message
            if not image_description:
                image_description = message
                
            return True, image_description
            
    return False, None

def get_bot_response(message, api_key, personality=1, use_demo_mode=False):
    """Get response from Together.ai API or use demo mode"""
    # Log the inputs for debugging
    print(f"DEBUG - Message: {message}")
    print(f"DEBUG - API Key provided: {'Yes' if api_key else 'No'}")
    print(f"DEBUG - Personality: {personality}")
    print(f"DEBUG - Demo mode: {use_demo_mode}")
    
    # Check if this is an image generation request
    is_image_request, image_description = check_for_image_request(message)
    
    # Handle image generation requests
    if is_image_request:
        print(f"DEBUG - Image generation request detected: {image_description}")
        
        # Generate personality-specific prompt prefix
        prompt_prefix = ""
        if personality == 2:  # Sassy 90s Teen
            prompt_prefix = "A 90s style image of "
        elif personality == 3:  # Emotional Pirate
            prompt_prefix = "A pirate-themed image of "
        elif personality == 4:  # MJ Therapist
            prompt_prefix = "A Michael Jackson inspired image of "
            
        # Generate the image
        full_prompt = prompt_prefix + image_description
        image_path = generate_image(full_prompt)
        
        if image_path:
            # Create a personality-appropriate response with the image
            if personality == 1:  # Helpful Assistant
                return f"I've generated an image based on your request: <img-{image_path}>"
            elif personality == 2:  # Sassy 90s Teen
                return f"Whatever, I made your image. As if it was hard or something: <img-{image_path}>"
            elif personality == 3:  # Emotional Pirate
                return f"Arr! Me heart be swellin' with pride at this treasure I've created for ye! *wipes tear* <img-{image_path}>"
            elif personality == 4:  # MJ Therapist
                return f"This is it! The image you've been looking for. Remember, it doesn't matter if you're black or white: <img-{image_path}>"
            else:
                return f"Here's the image you requested: <img-{image_path}>"
        else:
            return "I'm sorry, I couldn't generate an image at this time. Could you try a different description?"
    
    # Use demo mode if requested or if no API key is provided
    if use_demo_mode or not api_key:
        if not api_key:
            print("DEBUG - No API key provided, using demo mode")
            
        # Ensure personality is an integer and valid
        try:
            personality_num = int(personality)
            if personality_num not in demo_responses:
                personality_num = 1
        except:
            personality_num = 1
            
        # Return a random response from the demo responses
        import random
        responses = demo_responses[personality_num]
        return random.choice(responses)
    
    # If we have an API key, try to use the Together.ai API
    # Ensure personality is an integer and valid
    try:
        personality_num = int(personality)
        if personality_num not in system_prompts:
            personality_num = 1
    except:
        personality_num = 1
    
    # Set up the API request
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "mistralai/Mixtral-8x7B-Instruct-v0.1",
        "prompt": f"<s>[INST] <<SYS>>{system_prompts[personality_num]} <</SYS>> {message} [/INST]",
        "max_tokens": 200,
        "temperature": 0.7,
    }
    
    try:
        print(f"DEBUG - Sending request to Together.ai API")
        response = requests.post("https://api.together.xyz/v1/completions", headers=headers, json=data)
        
        # Print the full response for debugging
        print(f"DEBUG - API Response status code: {response.status_code}")
        print(f"DEBUG - API Response headers: {response.headers}")
        print(f"DEBUG - API Response text: {response.text[:500]}...") # Print first 500 chars to avoid huge logs
        
        response.raise_for_status()
        
        # Parse the JSON response
        response_json = response.json()
        print(f"DEBUG - Response JSON keys: {response_json.keys()}")
        
        # Handle different response formats
        if 'choices' in response_json:
            # New API format
            output = response_json['choices'][0]['text']
        elif 'output' in response_json and 'choices' in response_json['output']:
            # Original format
            output = response_json['output']['choices'][0]['text']
        else:
            # Unknown format - dump the response for debugging
            print(f"DEBUG - Unknown response format: {response_json}")
            return f"Error: Unexpected API response format. Please check server logs."
        
        return output.strip()
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        print(f"DEBUG - Exception occurred: {error_msg}")
        return error_msg

# Global variables
demo_mode = False

# Create a directory for storing generated images
IMAGE_DIR = 'static/images'
os.makedirs(IMAGE_DIR, exist_ok=True)

@app.route('/')
def index():
    # Initialize the session if needed
    if 'messages' not in session:
        session['messages'] = []
    if 'api_key' not in session:
        session['api_key'] = default_api_key
    if 'personality' not in session:
        session['personality'] = 1
    if 'demo_mode' not in session:
        session['demo_mode'] = demo_mode
    
    return render_template('index.html', 
                           messages=session['messages'],
                           api_key=session['api_key'],
                           personality=session['personality'],
                           demo_mode=session['demo_mode'])

@app.route('/static/images/<path:filename>')
def serve_image(filename):
    return send_from_directory(IMAGE_DIR, filename)

@app.route('/test_api_key', methods=['POST'])
def test_api_key():
    data = request.json
    api_key = data.get('api_key', '')
    
    if not api_key:
        return jsonify({
            'status': 'error',
            'message': 'API key is required'
        }), 400
    
    # Test the API key with a simple request
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        # Make a minimal request to test the API key
        test_data = {
            "model": "mistralai/Mixtral-8x7B-Instruct-v0.1",
            "prompt": "<s>[INST] Say hello [/INST]",
            "max_tokens": 5,
            "temperature": 0.7,
        }
        
        print(f"DEBUG - Testing API key: {api_key[:5]}...")  # Only print first few chars for security
        response = requests.post("https://api.together.xyz/v1/completions", headers=headers, json=test_data)
        
        # Print response details for debugging
        print(f"DEBUG - Test API Response status code: {response.status_code}")
        print(f"DEBUG - Test API Response headers: {response.headers}")
        print(f"DEBUG - Test API Response text: {response.text[:500]}...")  # Print first 500 chars
        
        response.raise_for_status()
        
        # Parse the JSON response to verify it's valid
        response_json = response.json()
        print(f"DEBUG - Test Response JSON keys: {response_json.keys()}")
        
        # Check if the response has a valid format
        valid_response = False
        if 'choices' in response_json:
            valid_response = True
        elif 'output' in response_json and 'choices' in response_json['output']:
            valid_response = True
            
        if not valid_response:
            print(f"DEBUG - Unexpected response format: {response_json}")
            return jsonify({
                'status': 'error',
                'message': 'API key appears valid but the response format is unexpected'
            }), 400
        
        # If we get here, the API key is valid
        session['api_key'] = api_key
        return jsonify({
            'status': 'success',
            'message': 'API key is valid'
        })
    except Exception as e:
        error_msg = f'API key validation failed: {str(e)}'
        print(f"DEBUG - Exception during API key test: {error_msg}")
        return jsonify({
            'status': 'error',
            'message': error_msg
        }), 400

@app.route('/send_message', methods=['POST'])
def send_message():
    data = request.json
    message = data.get('message', '')
    api_key = data.get('api_key', session.get('api_key', ''))
    personality = data.get('personality', session.get('personality', 1))
    use_demo = data.get('demo_mode', session.get('demo_mode', False))
    
    # Save settings to session
    session['personality'] = personality
    session['api_key'] = api_key
    session['demo_mode'] = use_demo
    
    # Get bot response
    bot_response = get_bot_response(message, api_key, personality, use_demo)
    
    # Add to message history
    if 'messages' not in session:
        session['messages'] = []
    
    session['messages'].append({
        'user': message,
        'bot': bot_response
    })
    session.modified = True
    
    return jsonify({
        'response': bot_response
    })

@app.route('/clear_chat', methods=['POST'])
def clear_chat():
    session['messages'] = []
    return jsonify({'status': 'success'})

@app.route('/set_personality', methods=['POST'])
def set_personality():
    data = request.json
    personality = data.get('personality', 1)
    session['personality'] = int(personality)
    return jsonify({'status': 'success', 'personality': personality})

@app.route('/toggle_demo_mode', methods=['POST'])
def toggle_demo_mode():
    data = request.json
    demo_mode = data.get('demo_mode', False)
    session['demo_mode'] = demo_mode
    return jsonify({'status': 'success', 'demo_mode': demo_mode})

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    
    # Create the HTML template
    with open('templates/index.html', 'w') as f:
        f.write("""<!DOCTYPE html>
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
    </style>
</head>
<body>
    <h1>Personality Chatbot</h1>
    
    <div class="settings">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
            <h3 style="margin: 0;">Settings</h3>
            <div class="demo-mode-toggle">
                <label for="demo-mode" style="display: inline-block; margin-right: 10px;">Demo Mode:</label>
                <input type="checkbox" id="demo-mode" {% if demo_mode %}checked{% endif %} onclick="toggleDemoMode()">
                <span style="font-size: 0.8em; color: #666;">(No API key needed)</span>
            </div>
        </div>
        
        <div id="api-key-section" {% if demo_mode %}style="opacity: 0.5;"{% endif %}>
            <label for="api-key">Together.ai API Key:</label>
            <div style="display: flex; margin-bottom: 15px;">
                <input type="password" id="api-key" value="{{ api_key }}" placeholder="Enter your API key here" style="flex-grow: 1; margin-right: 10px; margin-bottom: 0;" {% if demo_mode %}disabled{% endif %}>
                <button id="test-api-key" style="white-space: nowrap;" {% if demo_mode %}disabled{% endif %} onclick="testApiKey()">Test API Key</button>
            </div>
            <p style="font-size: 0.8em; color: #666; margin-top: -10px;">
                You need a valid Together.ai API key. Get one at <a href="https://together.ai" target="_blank">together.ai</a>
            </p>
        </div>
        
        <label>Select Personality:</label>
        <div class="personality-options">
            <div class="personality-option{% if personality == 1 %} active{% endif %}" data-personality="1" onclick="setPersonality(1)">
                Helpful Assistant
            </div>
            <div class="personality-option{% if personality == 2 %} active{% endif %}" data-personality="2" onclick="setPersonality(2)">
                Sassy 90s Teen
            </div>
            <div class="personality-option{% if personality == 3 %} active{% endif %}" data-personality="3" onclick="setPersonality(3)">
                Emotional Pirate
            </div>
            <div class="personality-option{% if personality == 4 %} active{% endif %}" data-personality="4" onclick="setPersonality(4)">
                MJ Therapist
            </div>
        </div>
    </div>
    
    <div class="chat-container" id="chat-container">
        {% for message in messages %}
        <div class="message user-message">{{ message.user }}</div>
        <div class="message bot-message">{{ message.bot }}</div>
        {% endfor %}
    </div>
    
    <div class="input-container">
        <input type="text" id="message-input" placeholder="Type your message here..." onkeypress="if(event.key === 'Enter') sendMessage()">
        <button id="send-button" onclick="sendMessage()">Send</button>
    </div>
    
    <button id="clear-button" onclick="clearChat()">Clear Chat</button>
    
    <script>
        // Get DOM elements
        const chatContainer = document.getElementById('chat-container');
        const messageInput = document.getElementById('message-input');
        const sendButton = document.getElementById('send-button');
        const clearButton = document.getElementById('clear-button');
        const apiKeyInput = document.getElementById('api-key');
        const personalityOptions = document.querySelectorAll('.personality-option');
        
        // Current settings
        let currentPersonality = {{ personality }};
        let demoMode = {% if demo_mode %}true{% else %}false{% endif %};
        
        // Function to add a message to the chat
        function addMessage(message, isUser) {
            const messageElement = document.createElement('div');
            messageElement.classList.add('message');
            messageElement.classList.add(isUser ? 'user-message' : 'bot-message');
            
            // Check if the message contains an image tag
            const imgRegex = /<img-(/static/images/[^>]+)>/;
            const match = message.match(imgRegex);
            
            if (match) {
                // Replace the image tag with an actual image element
                const imgPath = match[1];
                const textPart = message.replace(imgRegex, '').trim();
                
                // Add text part if it exists
                if (textPart) {
                    const textElement = document.createElement('p');
                    textElement.textContent = textPart;
                    messageElement.appendChild(textElement);
                }
                
                // Add the image
                const imgElement = document.createElement('img');
                imgElement.src = imgPath;
                imgElement.alt = 'Generated image';
                imgElement.style.maxWidth = '100%';
                imgElement.style.borderRadius = '5px';
                imgElement.style.marginTop = '10px';
                messageElement.appendChild(imgElement);
            } else {
                // Regular text message
                messageElement.textContent = message;
            }
            
            chatContainer.appendChild(messageElement);
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }
        
        // Function to test API key
        async function testApiKey() {
        // Function to send a message
        async function sendMessage() {
            const message = messageInput.value.trim();
            if (!message) return;
            
            // Add user message to chat
            addMessage(message, true);
            messageInput.value = '';
            
            // Get API key
            const apiKey = apiKeyInput.value.trim();
            
            // Only check for API key if not in demo mode
            if (!demoMode && !apiKey) {
                addMessage('Error: Please enter your Together.ai API key in the settings section or enable Demo Mode.', false);
                return;
            }
            
            try {
                // Send message to server
                const response = await fetch('/send_message', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        message: message,
                        api_key: apiKey,
                        personality: currentPersonality,
                        demo_mode: demoMode
                    })
                });
                
                const data = await response.json();
                
                // Add bot response to chat
                addMessage(data.response, false);
            } catch (error) {
                console.error('Error sending message:', error);
                addMessage('Error: Could not get a response from the server.', false);
            }
        }
        
        // Function to clear the chat
        async function clearChat() {
            chatContainer.innerHTML = '';
            
            try {
                await fetch('/clear_chat', {
                    method: 'POST'
                });
            } catch (error) {
                console.error('Error clearing chat:', error);
            }
        }
        
        // Make sure all DOM elements are properly loaded before adding event listeners
        document.addEventListener('DOMContentLoaded', () => {
            console.log('DOM fully loaded');
            
            // Re-fetch elements to ensure they're available
            const sendButton = document.getElementById('send-button');
            const messageInput = document.getElementById('message-input');
            const clearButton = document.getElementById('clear-button');
            const testApiKeyButton = document.getElementById('test-api-key');
            const demoModeCheckbox = document.getElementById('demo-mode');
            const personalityOptions = document.querySelectorAll('.personality-option');
            
            // Add event listeners
            if (sendButton) {
                console.log('Send button found, adding listener');
                sendButton.addEventListener('click', sendMessage);
            }
            
            if (messageInput) {
                console.log('Message input found, adding listener');
                messageInput.addEventListener('keypress', (e) => {
                    if (e.key === 'Enter') {
                        sendMessage();
                    }
                });
            }
            
            if (clearButton) {
                console.log('Clear button found, adding listener');
                clearButton.addEventListener('click', clearChat);
            }
            
            if (testApiKeyButton) {
                console.log('Test API key button found, adding listener');
                testApiKeyButton.addEventListener('click', testApiKey);
            }
            
            if (demoModeCheckbox) {
                console.log('Demo mode checkbox found, adding listener');
                demoModeCheckbox.addEventListener('change', toggleDemoMode);
            }
            
            // Add personality selection listeners
            personalityOptions.forEach(option => {
                console.log('Adding listener to personality option');
                option.addEventListener('click', () => {
                    setPersonality(parseInt(option.dataset.personality));
                });
            });
        });
        
        // Immediate event listeners as a fallback
        const sendButton = document.getElementById('send-button');
        const messageInput = document.getElementById('message-input');
        const clearButton = document.getElementById('clear-button');
        const testApiKeyButton = document.getElementById('test-api-key');
        const demoModeCheckbox = document.getElementById('demo-mode');
        
        if (sendButton) sendButton.addEventListener('click', sendMessage);
        if (messageInput) messageInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') sendMessage(); });
        if (clearButton) clearButton.addEventListener('click', clearChat);
        if (testApiKeyButton) testApiKeyButton.addEventListener('click', testApiKey);
        if (demoModeCheckbox) demoModeCheckbox.addEventListener('change', toggleDemoMode);
        
        // Personality selection
        personalityOptions.forEach(option => {
            option.addEventListener('click', () => {
                setPersonality(parseInt(option.dataset.personality));
            });
        });
        
        // Scroll to bottom of chat on load
        chatContainer.scrollTop = chatContainer.scrollHeight;
    </script>
</body>
</html>
    
    # Run the Flask app on port 9000 to avoid conflicts
    app.run(debug=True, port=9000)
