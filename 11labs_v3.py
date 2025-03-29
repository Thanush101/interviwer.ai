import os
import signal
import sys
from elevenlabs.client import ElevenLabs
from elevenlabs.conversational_ai.conversation import Conversation, ConversationInitiationData
from elevenlabs.conversational_ai.default_audio_interface import DefaultAudioInterface
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from flask_sock import Sock
import threading
import time
import json
import base64
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)
sock = Sock(app)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['STATIC_FOLDER'] = 'static'

# Store active interviews in memory (note: this will reset on serverless function cold starts)
active_threads = {}
active_websockets = {}

class WebSocketAudioInterface:
    def __init__(self, ws):
        self.ws = ws
        self._is_recording = False
        self._input_callback = None
        self._buffer = []
        self._max_buffer_size = 100

    def play_audio(self, audio_data):
        """Send audio data through WebSocket."""
        try:
            if isinstance(audio_data, bytes):
                audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            else:
                audio_base64 = audio_data
            
            message = {
                'type': 'audio',
                'data': audio_base64
            }
            
            # Add to buffer if we're not recording
            if not self._is_recording:
                self._buffer.append(message)
                if len(self._buffer) > self._max_buffer_size:
                    self._buffer.pop(0)
            
            # Send immediately if we're recording
            self.ws.send(json.dumps(message))
            logger.debug(f"Sent audio data of length: {len(audio_base64)}")
        except Exception as e:
            logger.error(f"Error sending audio: {e}")

    def start(self, input_callback):
        """Start recording audio."""
        self._is_recording = True
        self._input_callback = input_callback
        logger.debug("Started recording audio")

    def stop(self):
        """Stop recording audio."""
        self._is_recording = False
        self._input_callback = None
        logger.debug("Stopped recording audio")

    def is_recording(self):
        """Check if currently recording."""
        return self._is_recording

class Interview:
    def __init__(self, agent_id, api_key, resume, job_description, ws):
        self.agent_id = agent_id
        self.api_key = api_key
        self.resume = resume
        self.job_description = job_description
        self.ws = ws
        self.running = True
        self.question_count = 0
        self.max_questions = 7
        self.audio_interface = WebSocketAudioInterface(ws)
        logger.info(f"Created new interview session for agent {agent_id}")

    def run(self):
        try:
            dynamic_vars = {
                "resume": self.resume,
                "job_description": self.job_description,
                "agent_id": self.agent_id
            }
            config = ConversationInitiationData(
                dynamic_variables=dynamic_vars
            )

            client = ElevenLabs(api_key=self.api_key)
            conversation = Conversation(
                client,
                self.agent_id,
                config=config,
                requires_auth=bool(self.api_key),
                audio_interface=self.audio_interface,
                callback_agent_response=self.handle_agent_response,
                callback_user_transcript=lambda transcript: logger.info(f"User: {transcript}"),
            )
            conversation.start_session()
            logger.info(f"Started conversation session for agent {self.agent_id}")
            
            while self.running and self.question_count < self.max_questions:
                time.sleep(0.1)
            
            if self.question_count >= self.max_questions:
                logger.info("Interview completed - maximum questions reached")
                print("Agent: Thank you for your time! This concludes our interview. We will review your responses and get back to you soon.")
                conversation.end_session()
            else:
                logger.info("Interview ended early")
                conversation.end_session()
        except Exception as e:
            logger.error(f"Error in interview: {e}")
        finally:
            if self.agent_id in active_threads:
                del active_threads[self.agent_id]
                logger.info(f"Cleaned up interview thread for agent {self.agent_id}")
            if self.agent_id in active_websockets:
                del active_websockets[self.agent_id]
                logger.info(f"Cleaned up WebSocket for agent {self.agent_id}")

    def handle_agent_response(self, response):
        logger.info(f"Agent: {response}")
        self.question_count += 1
        if self.question_count >= self.max_questions:
            self.running = False

@app.route('/')
def index():
    return render_template('index.html')

@sock.route('/ws/<agent_id>')
def handle_websocket(ws, agent_id):
    logger.info(f"New WebSocket connection for agent {agent_id}")
    active_websockets[agent_id] = ws
    
    try:
        while True:
            try:
                data = ws.receive()
                if data is None:
                    logger.info(f"WebSocket connection closed for agent {agent_id}")
                    break
                
                # Handle incoming audio data if needed
                message = json.loads(data)
                if message.get('type') == 'audio' and agent_id in active_threads:
                    interview = active_threads[agent_id]
                    if interview.audio_interface._input_callback and interview.audio_interface.is_recording():
                        interview.audio_interface._input_callback(message['data'])
                        logger.debug(f"Processed audio data for agent {agent_id}")
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON received: {e}")
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {e}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        if agent_id in active_websockets:
            del active_websockets[agent_id]
            logger.info(f"Cleaned up WebSocket connection for agent {agent_id}")

@app.route('/offer', methods=['POST'])
def handle_offer():
    data = request.json
    agent_id = data.get('agentId')
    api_key = data.get('apiKey')
    resume = data.get('resume')
    job_description = data.get('jobDescription')
    
    if not agent_id or not api_key or not resume or not job_description:
        logger.error("Missing required fields in offer request")
        return jsonify({'error': 'Agent ID, API Key, Resume, and Job Description are required'}), 400
    
    if agent_id not in active_websockets:
        logger.error(f"No active WebSocket connection for agent {agent_id}")
        return jsonify({'error': 'WebSocket connection not established'}), 400
    
    # Create and start interview
    interview = Interview(agent_id, api_key, resume, job_description, active_websockets[agent_id])
    thread = threading.Thread(target=interview.run)
    active_threads[agent_id] = interview
    thread.start()
    logger.info(f"Started interview thread for agent {agent_id}")
    
    return jsonify({'conversationId': agent_id})

@app.route('/cancel', methods=['POST'])
def handle_cancel():
    data = request.json
    agent_id = data.get('agentId')
    
    if not agent_id:
        logger.error("Missing agent ID in cancel request")
        return jsonify({'error': 'Agent ID is required'}), 400
    
    if agent_id in active_threads:
        interview = active_threads[agent_id]
        interview.running = False
        del active_threads[agent_id]
        logger.info(f"Cancelled interview for agent {agent_id}")
        return jsonify({'status': 'cancelled'})
    
    logger.warning(f"No active session found for agent {agent_id}")
    return jsonify({'error': 'No active session found'}), 404

# For local development
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080) 