#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const https = require('https');

class CopilotAPI {
    constructor(configPath = './config.json') {
        this.configPath = configPath;
        this.config = this.loadConfig();
        this.copilotToken = null;
        this.tokenExpiry = null;
    }

    loadConfig() {
        try {
            const configData = fs.readFileSync(this.configPath, 'utf8');
            return JSON.parse(configData);
        } catch (error) {
            console.error('Error loading config:', error.message);
            process.exit(1);
        }
    }

    async makeRequest(options, data = null) {
        return new Promise((resolve, reject) => {
            const req = https.request(options, (res) => {
                let body = '';
                res.on('data', chunk => body += chunk);
                res.on('end', () => {
                    try {
                        const response = JSON.parse(body);
                        resolve({ status: res.statusCode, data: response });
                    } catch (error) {
                        resolve({ status: res.statusCode, data: body });
                    }
                });
            });

            req.on('error', reject);
            
            if (data) {
                req.write(typeof data === 'string' ? data : JSON.stringify(data));
            }
            
            req.end();
        });
    }

    async refreshCopilotToken() {
        console.log('🔄 Refreshing Copilot token...');
        
        const options = {
            hostname: 'api.github.com',
            port: 443,
            path: '/copilot_internal/v2/token',
            method: 'GET',
            headers: {
                'authorization': `token ${this.config.access_token}`,
                'user-agent': 'GithubCopilot/1.155.0'
            }
        };

        try {
            const response = await this.makeRequest(options);
            
            if (response.status === 200) {
                this.copilotToken = response.data.token;
                // Use the expires_at timestamp from the API response (subtract 60 seconds for safety margin)
                this.tokenExpiry = (response.data.expires_at * 1000) - (60 * 1000);
                console.log('✅ Copilot token refreshed successfully');
                return true;
            } else {
                console.error('❌ Error refreshing token:', response.data);
                return false;
            }
        } catch (error) {
            console.error('❌ Network error refreshing token:', error.message);
            return false;
        }
    }

    async ensureValidToken() {
        if (!this.copilotToken || !this.tokenExpiry || Date.now() > this.tokenExpiry) {
            const success = await this.refreshCopilotToken();
            if (!success) {
                throw new Error('Failed to obtain valid Copilot token');
            }
        }
    }

    async getModels() {
        await this.ensureValidToken();
        
        const options = {
            hostname: 'api.githubcopilot.com',
            port: 443,
            path: '/models',
            method: 'GET',
            headers: {
                'authorization': `Bearer ${this.copilotToken}`,
                'Copilot-Integration-Id': 'vscode-chat'
            }
        };

        const response = await this.makeRequest(options);
        return response;
    }

    async chatCompletion(messages, options = {}) {
        await this.ensureValidToken();
        
        const requestData = {
            messages: messages,
            max_tokens: options.maxTokens || 1000,
            temperature: options.temperature || 0.3,
            stream: options.stream || false
        };

        const httpOptions = {
            hostname: 'api.githubcopilot.com',
            port: 443,
            path: '/chat/completions',
            method: 'POST',
            headers: {
                'authorization': `Bearer ${this.copilotToken}`,
                'Copilot-Integration-Id': 'vscode-chat',
                'content-type': 'application/json'
            }
        };

        const response = await this.makeRequest(httpOptions, requestData);
        return response;
    }
}

// Función para mostrar ayuda
function showHelp() {
    console.log(`
🤖 GitHub Copilot API Client (Node.js)

Usage:
  node copilot-client.js <command> [options]

Commands:
  models                     - Get available models
  chat "<message>"          - Send a chat message
  chat-file <file.txt>      - Send content from a file
  
Options:
  --max-tokens <number>     - Maximum tokens (default: 1000)
  --temperature <number>    - Temperature 0-1 (default: 0.3)
  --stream                  - Enable streaming

Examples:
  node copilot-client.js models
  node copilot-client.js chat "Write a Python function to sort a list"
  node copilot-client.js chat "Explain recursion" --max-tokens 500 --temperature 0.7
  node copilot-client.js chat-file prompt.txt

Note: Make sure to set your YOUR_ACCESS_TOKEN in config.json first!
    `);
}

// Función principal
async function main() {
    const args = process.argv.slice(2);
    
    if (args.length === 0 || args[0] === '--help' || args[0] === '-h') {
        showHelp();
        return;
    }

    const client = new CopilotAPI();
    const command = args[0];

    try {
        switch (command) {
            case 'models':
                console.log('📋 Getting available models...');
                const modelsResponse = await client.getModels();
                console.log('Models:', JSON.stringify(modelsResponse.data, null, 2));
                break;

            case 'chat':
                if (args.length < 2) {
                    console.error('❌ Please provide a message for chat');
                    return;
                }

                const message = args[1];
                const options = {};
                
                // Parse options
                for (let i = 2; i < args.length; i += 2) {
                    switch (args[i]) {
                        case '--max-tokens':
                            options.maxTokens = parseInt(args[i + 1]);
                            break;
                        case '--temperature':
                            options.temperature = parseFloat(args[i + 1]);
                            break;
                        case '--stream':
                            options.stream = true;
                            i--; // No value needed for this flag
                            break;
                    }
                }

                console.log('💬 Sending chat message...');
                const chatResponse = await client.chatCompletion([
                    { role: 'user', content: message }
                ], options);

                if (chatResponse.status === 200) {
                    console.log('\n📝 Response:');
                    console.log(chatResponse.data.choices[0].message.content);
                    console.log(`\n📊 Usage: ${chatResponse.data.usage.total_tokens} tokens`);
                } else {
                    console.error('❌ Error:', chatResponse.data);
                }
                break;

            case 'chat-file':
                if (args.length < 2) {
                    console.error('❌ Please provide a file path');
                    return;
                }

                const filePath = args[1];
                try {
                    const fileContent = fs.readFileSync(filePath, 'utf8');
                    console.log('📁 Sending file content...');
                    
                    const fileResponse = await client.chatCompletion([
                        { role: 'user', content: fileContent }
                    ]);

                    if (fileResponse.status === 200) {
                        console.log('\n📝 Response:');
                        console.log(fileResponse.data.choices[0].message.content);
                        console.log(`\n📊 Usage: ${fileResponse.data.usage.total_tokens} tokens`);
                    } else {
                        console.error('❌ Error:', fileResponse.data);
                    }
                } catch (error) {
                    console.error('❌ Error reading file:', error.message);
                }
                break;

            default:
                console.error('❌ Unknown command:', command);
                showHelp();
        }
    } catch (error) {
        console.error('❌ Error:', error.message);
    }
}

// Ejecutar si este archivo es llamado directamente
if (require.main === module) {
    main();
}

module.exports = CopilotAPI;
