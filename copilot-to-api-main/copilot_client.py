#!/usr/bin/env python3

import json
import time
import requests
import argparse
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

class CopilotAPI:
    def __init__(self, config_path: str = './config.json'):
        self.config_path = config_path
        self.config = self.load_config()
        self.copilot_token: Optional[str] = None
        self.token_expiry: Optional[datetime] = None

    def load_config(self) -> Dict[str, str]:
        """Load configuration from JSON file"""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
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

    def chat_completion(self, messages: List[Dict[str, str]], options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send a chat completion request"""
        self.ensure_valid_token()
        
        if options is None:
            options = {}
        
        stream = options.get('stream', False)

        request_data = {
            'messages': messages,
            'max_tokens': options.get('max_tokens', 1000),
            'temperature': options.get('temperature', 0.3),
            'stream': stream
        }

        headers = {
            'authorization': f'Bearer {self.copilot_token}',
            'Copilot-Integration-Id': 'vscode-chat',
            'content-type': 'application/json'
        }

        response = requests.post(
            'https://api.githubcopilot.com/chat/completions',
            headers=headers,
            json=request_data,
            stream=stream
        )

        if not stream:
            return {
                'status': response.status_code,
                'data': response.json() if response.status_code == 200 else response.text
            }

        if response.status_code != 200:
            return {'status': response.status_code, 'data': response.text}

        aggregated_text: List[str] = []
        usage: Optional[Dict[str, Any]] = None

        print('\n🛈 Streaming response:\n')

        for line in response.iter_lines(decode_unicode=True):
            if not line:
                continue

            if line.startswith('data:'):
                payload = line[len('data:'):].strip()

                if payload == '[DONE]':
                    break

                try:
                    chunk = json.loads(payload)
                except json.JSONDecodeError:
                    continue

                if 'usage' in chunk:
                    usage = chunk['usage']

                choices = chunk.get('choices', [])
                if not choices:
                    continue

                delta = choices[0].get('delta', {}) or {}
                content = delta.get('content')
                if content:
                    print(content, end='', flush=True)
                    aggregated_text.append(content)

        print('\n')

        data = {
            'choices': [
                {
                    'message': {
                        'content': ''.join(aggregated_text)
                    }
                }
            ],
            'usage': usage,
            'streamed': True,
        }

        return {'status': 200, 'data': data}


def show_help():
    """Show help message"""
    print("""
🤖 GitHub Copilot API Client (Python)

Usage:
  python copilot_client.py <command> [options]

Commands:
  models                     - Get available models
  chat "<message>"          - Send a chat message
  chat-file <file.txt>      - Send content from a file
  
Options:
  --max-tokens <number>     - Maximum tokens (default: 1000)
  --temperature <number>    - Temperature 0-1 (default: 0.3)
  --stream                  - Enable streaming

Examples:
  python copilot_client.py models
  python copilot_client.py chat "Write a Python function to sort a list"
  python copilot_client.py chat "Explain recursion" --max-tokens 500 --temperature 0.7
  python copilot_client.py chat-file prompt.txt

Note: Make sure to set your YOUR_ACCESS_TOKEN in config.json first!
    """)


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='GitHub Copilot API Client', add_help=False)
    parser.add_argument('command', nargs='?', help='Command to execute')
    parser.add_argument('message_or_file', nargs='?', help='Message or file path')
    parser.add_argument('--max-tokens', type=int, default=1000, help='Maximum tokens')
    parser.add_argument('--temperature', type=float, default=0.3, help='Temperature')
    parser.add_argument('--stream', action='store_true', help='Enable streaming')
    parser.add_argument('--help', '-h', action='store_true', help='Show help')

    args = parser.parse_args()

    if args.help or not args.command:
        show_help()
        return

    client = CopilotAPI()

    try:
        if args.command == 'models':
            print('📋 Getting available models...')
            response = client.get_models()
            print('Models:', json.dumps(response['data'], indent=2))

        elif args.command == 'chat':
            if not args.message_or_file:
                print('❌ Please provide a message for chat')
                return

            options = {
                'max_tokens': args.max_tokens,
                'temperature': args.temperature,
                'stream': args.stream
            }

            print('💬 Sending chat message...')
            response = client.chat_completion([
                {'role': 'user', 'content': args.message_or_file}
            ], options)

            if response['status'] == 200:
                if args.stream and response['data'].get('streamed'):
                    full_text = response['data']['choices'][0]['message']['content']
                    if full_text:
                        print('\n\n📝 Final Response (aggregated):')
                        print(full_text)

                    usage = response['data'].get('usage') or {}
                    total_tokens = usage.get('total_tokens')
                    if total_tokens is not None:
                        print(f"\n📊 Usage: {total_tokens} tokens")
                else:
                    print('\n📝 Response:')
                    print(response['data']['choices'][0]['message']['content'])

                    usage = response['data'].get('usage') or {}
                    total_tokens = usage.get('total_tokens')
                    if total_tokens is not None:
                        print(f"\n📊 Usage: {total_tokens} tokens")
            else:
                print(f'❌ Error: {response["data"]}')

        elif args.command == 'chat-file':
            if not args.message_or_file:
                print('❌ Please provide a file path')
                return

            try:
                with open(args.message_or_file, 'r', encoding='utf-8') as f:
                    file_content = f.read()

                print('📁 Sending file content...')
                
                options = {
                    'max_tokens': args.max_tokens,
                    'temperature': args.temperature,
                    'stream': args.stream
                }

                response = client.chat_completion([
                    {'role': 'user', 'content': file_content}
                ], options)

                if response['status'] == 200:
                    print('\n📝 Response:')
                    print(response['data']['choices'][0]['message']['content'])
                    print(f"\n📊 Usage: {response['data']['usage']['total_tokens']} tokens")
                else:
                    print(f'❌ Error: {response["data"]}')

            except Exception as e:
                print(f'❌ Error reading file: {e}')

        else:
            print(f'❌ Unknown command: {args.command}')
            show_help()

    except Exception as e:
        print(f'❌ Error: {e}')


if __name__ == '__main__':
    main()
