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

resume = """Thanush is a Python Developer with 1 years of experience in building and optimizing scalable applications.
He specializes in developing backend solutions, integrating RESTful APIs, and managing databases efficiently.
His expertise includes working with frameworks like Django and Flask, implementing security best practices, and optimizing application performance.
He has a strong understanding of cloud platforms, DevOps tools, and containerization, enabling seamless deployment and automation.
Thanush is adept at troubleshooting complex issues and collaborating with cross-functional teams to deliver high-quality software solutions."""

job_description= """Data Analyst: Extract, analyze, and interpret data to drive business insights.
                    Create visualizations and reports to communicate findings and support strategic decision-making."""

app = Flask(__name__)
CORS(app)
sock = Sock(app)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['STATIC_FOLDER'] = 'static'

# Store active interviews in memory (note: this will reset on serverless function cold starts)
active_threads = {}
active_websockets = {}

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
                audio_interface=DefaultAudioInterface(),
                callback_agent_response=self.handle_agent_response,
                callback_user_transcript=lambda transcript: print(f"User: {transcript}"),
            )
            conversation.start_session()
            
            while self.running and self.question_count < self.max_questions:
                time.sleep(0.1)
            
            if self.question_count >= self.max_questions:
                print("Agent: Thank you for your time! This concludes our interview. We will review your responses and get back to you soon.")
                conversation.end_session()
                print("Interview ended after 7 questions")
            else:
                conversation.end_session()
        except Exception as e:
            print(f"Error in interview: {e}")
        finally:
            if self.agent_id in active_threads:
                del active_threads[self.agent_id]
            if self.agent_id in active_websockets:
                del active_websockets[self.agent_id]

    def handle_agent_response(self, response):
        print(f"Agent: {response}")
        self.question_count += 1
        if self.question_count >= self.max_questions:
            self.running = False

@app.route('/')
def index():
    return render_template('index.html')

@sock.route('/ws/<agent_id>')
def handle_websocket(ws, agent_id):
    active_websockets[agent_id] = ws
    try:
        while True:
            data = ws.receive()
            if data is None:
                break
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        if agent_id in active_websockets:
            del active_websockets[agent_id]

@app.route('/offer', methods=['POST'])
def handle_offer():
    data = request.json
    agent_id = data.get('agentId')
    api_key = data.get('apiKey')
    resume = data.get('resume')
    job_description = data.get('jobDescription')
    
    if not agent_id or not api_key or not resume or not job_description:
        return jsonify({'error': 'Agent ID, API Key, Resume, and Job Description are required'}), 400
    
    if agent_id not in active_websockets:
        return jsonify({'error': 'WebSocket connection not established'}), 400
    
    # Create and start interview
    interview = Interview(agent_id, api_key, resume, job_description, active_websockets[agent_id])
    thread = threading.Thread(target=interview.run)
    active_threads[agent_id] = interview
    thread.start()
    
    return jsonify({'sdp': data['sdp']})

@app.route('/cancel', methods=['POST'])
def handle_cancel():
    data = request.json
    agent_id = data.get('agentId')
    
    if not agent_id:
        return jsonify({'error': 'Agent ID is required'}), 400
    
    if agent_id in active_threads:
        interview = active_threads[agent_id]
        interview.running = False
        del active_threads[agent_id]
        return jsonify({'status': 'cancelled'})
    
    return jsonify({'error': 'No active session found'}), 404

# For local development
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)