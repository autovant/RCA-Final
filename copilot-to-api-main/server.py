#!/usr/bin/env python3

import sys
import io

# Fix Windows Unicode encoding issue - force UTF-8 for stdout/stderr
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import json
import time
import requests
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from flask import Flask, request, jsonify, Response
from flask_cors import CORS

class CopilotAPI:
    def __init__(self, config_path: str = './config.json'):
        self.config_path = config_path
        self.config = self.load_config()
        self.copilot_token: Optional[str] = None
        self.token_expiry: Optional[datetime] = None

    def load_config(self) -> Dict[str, str]:
        """Load configuration from JSON file or environment."""
        env_token = os.environ.get('GITHUB_TOKEN') or os.environ.get('COPILOT_ACCESS_TOKEN')

        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            if env_token:
                print('ℹ️  config.json not found; using access token from environment.')
                return {'access_token': env_token}
            print('❌ config.json not found and no GITHUB_TOKEN/COPILOT_ACCESS_TOKEN provided.')
            exit(1)
        except Exception as e:
            print(f'Error loading config: {e}')
            exit(1)

    def refresh_copilot_token(self) -> bool:
        """Refresh the Copilot token using the access token"""
        print('🔄 Refreshing Copilot token...')
        
        headers = {
            'authorization': f'token {self.config["access_token"]}',
            'user-agent': 'GithubCopilot/1.155.0'
        }

        try:
            response = requests.get(
                'https://api.github.com/copilot_internal/v2/token',
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                self.copilot_token = data['token']
                # Use the expires_at timestamp from the API response (subtract 60 seconds for safety margin)
                self.token_expiry = datetime.fromtimestamp(data['expires_at'] - 60)
                print('✅ Copilot token refreshed successfully')
                print(f'🕐 Token expires at: {self.token_expiry.isoformat()}')
                return True
            else:
                print(f'❌ Error refreshing token: {response.text}')
                return False
        except Exception as e:
            print(f'❌ Network error refreshing token: {e}')
            return False

    def ensure_valid_token(self):
        """Ensure we have a valid Copilot token"""
        if not self.copilot_token or not self.token_expiry or datetime.now() > self.token_expiry:
            success = self.refresh_copilot_token()
            if not success:
                raise Exception('Failed to obtain valid Copilot token')

    def get_models(self) -> Dict[str, Any]:
        """Get available Copilot models"""
        self.ensure_valid_token()
        
        headers = {
            'authorization': f'Bearer {self.copilot_token}',
            'Copilot-Integration-Id': 'vscode-chat'
        }

        response = requests.get('https://api.githubcopilot.com/models', headers=headers)
        return {
            'status': response.status_code,
            'data': response.json() if response.status_code == 200 else response.text
        }

    def chat_completion(self, messages: List[Dict[str, str]], options: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send a chat completion request"""
        self.ensure_valid_token()
        
        if options is None:
            options = {}
        
        request_data = {
            'messages': messages,
            'max_tokens': options.get('max_tokens', 1000),
            'temperature': options.get('temperature', 0.3),
            'stream': options.get('stream', False),
            'model': options.get('model', 'gpt-4o')  # OpenAI compatibility
        }

        headers = {
            'authorization': f'Bearer {self.copilot_token}',
            'Copilot-Integration-Id': 'vscode-chat',
            'content-type': 'application/json'
        }

        # Handle streaming vs non-streaming differently
        if options.get('stream', False):
            response = requests.post(
                'https://api.githubcopilot.com/chat/completions',
                headers=headers,
                json=request_data,
                stream=True  # Enable streaming
            )
            return {
                'status': response.status_code,
                'stream': response
            }
        else:
            response = requests.post(
                'https://api.githubcopilot.com/chat/completions',
                headers=headers,
                json=request_data
            )
            return {
                'status': response.status_code,
                'data': response.json() if response.status_code == 200 else response.text
            }


# Create Flask application
app = Flask(__name__)
CORS(app)

# Create CopilotAPI instance
copilot = CopilotAPI()

# Logging middleware
@app.before_request
def log_request():
    print(f"{datetime.now().isoformat()} - {request.method} {request.path}")

# Health endpoint
@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'copilot-api-server-python'
    })

# Get models endpoint (OpenAI compatible)
@app.route('/v1/models', methods=['GET'])
def get_models():
    try:
        response = copilot.get_models()
        
        if response['status'] == 200:
            return jsonify(response['data'])
        else:
            return jsonify({
                'error': {
                    'message': response['data'],
                    'type': 'api_error',
                    'code': response['status']
                }
            }), response['status']
    except Exception as e:
        print(f'Error in /v1/models: {e}')
        return jsonify({
            'error': {
                'message': str(e),
                'type': 'internal_error',
                'code': 500
            }
        }), 500

# Chat completions endpoint (OpenAI compatible)
@app.route('/v1/chat/completions', methods=['POST'])
def chat_completions():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'error': {
                    'message': 'Request body must be JSON',
                    'type': 'invalid_request_error',
                    'code': 400
                }
            }), 400
        
        messages = data.get('messages')
        if not messages or not isinstance(messages, list):
            return jsonify({
                'error': {
                    'message': 'messages field is required and must be an array',
                    'type': 'invalid_request_error',
                    'code': 400
                }
            }), 400

        options = {
            'max_tokens': data.get('max_tokens', 1000),
            'temperature': data.get('temperature', 0.3),
            'stream': data.get('stream', False),
            'model': data.get('model', 'gpt-4o')
        }

        response = copilot.chat_completion(messages, options)
        
        if options.get('stream', False):
            # Handle streaming response
            if response['status'] == 200:
                def generate_stream():
                    try:
                        for chunk in response['stream'].iter_content(chunk_size=None, decode_unicode=False):
                            if chunk:
                                yield chunk
                    except Exception as e:
                        print(f'Streaming error: {e}')
                        yield b''

                return Response(
                    generate_stream(),
                    mimetype='text/event-stream',
                    headers={
                        'Cache-Control': 'no-cache',
                        'Connection': 'keep-alive',
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Headers': 'Cache-Control'
                    }
                )
            else:
                return jsonify({
                    'error': {
                        'message': response.get('data', 'Streaming request failed'),
                        'type': 'api_error',
                        'code': response['status']
                    }
                }), response['status']
        else:
            # Handle non-streaming response (as before)
            if response['status'] == 200:
                return jsonify(response['data'])
            else:
                return jsonify({
                    'error': {
                        'message': response['data'],
                        'type': 'api_error',
                        'code': response['status']
                    }
                }), response['status']
    except Exception as e:
        print(f'Error in /v1/chat/completions: {e}')
        return jsonify({
            'error': {
                'message': str(e),
                'type': 'internal_error',
                'code': 500
            }
        }), 500

# Root endpoint with API information
@app.route('/', methods=['GET'])
def root():
    return jsonify({
        'service': 'GitHub Copilot to OpenAI API Bridge (Python)',
        'version': '1.0.0',
        'endpoints': {
            'health': 'GET /health',
            'models': 'GET /v1/models',
            'chat_completions': 'POST /v1/chat/completions'
        },
        'documentation': 'https://platform.openai.com/docs/api-reference',
        'note': 'This service provides OpenAI-compatible endpoints for GitHub Copilot'
    })

# Handle 404 routes
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': {
            'message': f'Route {request.method} {request.path} not found',
            'type': 'not_found_error',
            'code': 404
        }
    }), 404

# Handle general errors
@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'error': {
            'message': 'Internal server error',
            'type': 'internal_error',
            'code': 500
        }
    }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f'🚀 Copilot API Server (Python) running on port {port}')
    print(f'📖 OpenAI-compatible endpoints:')
    print(f'   GET  http://localhost:{port}/v1/models')
    print(f'   POST http://localhost:{port}/v1/chat/completions')
    print(f'💡 Health check: http://localhost:{port}/health')
    
    app.run(host='0.0.0.0', port=port, debug=False)
