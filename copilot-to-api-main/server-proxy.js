const express = require('express');
const cors = require('cors');
const { createProxyMiddleware } = require('http-proxy-middleware');
const fs = require('fs');
const https = require('https');

class TokenManager {
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

    async refreshCopilotToken() {
        console.log('🔄 Refreshing Copilot token...');
        
        return new Promise((resolve, reject) => {
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

            const req = https.request(options, (res) => {
                let body = '';
                res.on('data', chunk => body += chunk);
                res.on('end', () => {
                    try {
                        if (res.statusCode === 200) {
                            const response = JSON.parse(body);
                            this.copilotToken = response.token;
                            this.tokenExpiry = (response.expires_at * 1000) - (60 * 1000);
                            console.log('✅ Copilot token refreshed successfully');
                            console.log(`🕐 Token expires at: ${new Date(this.tokenExpiry).toISOString()}`);
                            resolve(true);
                        } else {
                            console.error('❌ Error refreshing token:', body);
                            resolve(false);
                        }
                    } catch (error) {
                        console.error('❌ Parse error:', error.message);
                        resolve(false);
                    }
                });
            });

            req.on('error', (error) => {
                console.error('❌ Network error refreshing token:', error.message);
                resolve(false);
            });
            
            req.end();
        });
    }

    async getValidToken() {
        if (!this.copilotToken || !this.tokenExpiry || Date.now() > this.tokenExpiry) {
            const success = await this.refreshCopilotToken();
            if (!success) {
                throw new Error('Failed to obtain valid Copilot token');
            }
        }
        return this.copilotToken;
    }
}

// Create Express app
const app = express();
const port = process.env.PORT || 3000;

// Create token manager
const tokenManager = new TokenManager();

// Enable CORS
app.use(cors());

// Logging middleware
app.use((req, res, next) => {
    console.log(`${new Date().toISOString()} - ${req.method} ${req.path}`);
    next();
});

// Health endpoint
app.get('/health', (req, res) => {
    res.json({ 
        status: 'healthy', 
        timestamp: new Date().toISOString(),
        service: 'copilot-api-proxy' 
    });
});

// Root endpoint with API information
app.get('/', (req, res) => {
    res.json({
        service: 'GitHub Copilot to OpenAI API Proxy (Ultra-Fast)',
        version: '2.0.0',
        endpoints: {
            health: 'GET /health',
            models: 'GET /v1/models',
            chat_completions: 'POST /v1/chat/completions'
        },
        documentation: 'https://platform.openai.com/docs/api-reference',
        note: 'This service provides transparent proxy to GitHub Copilot with automatic token injection'
    });
});

// Ultra-fast proxy for all /v1/* endpoints
app.use('/v1', async (req, res, next) => {
    try {
        // Get token before creating proxy
        const token = await tokenManager.getValidToken();
        
        // Create proxy middleware with token
        const proxy = createProxyMiddleware({
            target: 'https://api.githubcopilot.com',
            changeOrigin: true,
            
            // Remove /v1 prefix when forwarding to GitHub Copilot
            pathRewrite: {
                '^/v1': '' // Remove /v1 prefix
            },
            
            // Inject auth headers (now synchronous)
            onProxyReq: (proxyReq, req, res) => {
                proxyReq.setHeader('authorization', `Bearer ${token}`);
                proxyReq.setHeader('Copilot-Integration-Id', 'vscode-chat');
            },

            // Handle proxy errors
            onError: (err, req, res) => {
                console.error('Proxy error:', err);
                if (!res.headersSent) {
                    res.status(500).json({
                        error: {
                            message: 'Proxy request failed',
                            type: 'proxy_error',
                            code: 500
                        }
                    });
                }
            },

            // Log proxy responses
            onProxyRes: (proxyRes, req, res) => {
                console.log(`📡 Proxy: ${req.method} ${req.path} → ${proxyRes.statusCode}`);
            }
        });

        // Execute proxy
        proxy(req, res, next);
        
    } catch (error) {
        console.error('Error getting token for proxy:', error);
        if (!res.headersSent) {
            res.status(500).json({
                error: {
                    message: 'Failed to obtain authentication token',
                    type: 'auth_error',
                    code: 500
                }
            });
        }
    }
});

// Handle 404 routes
app.use('*', (req, res) => {
    res.status(404).json({
        error: {
            message: `Route ${req.method} ${req.originalUrl} not found`,
            type: 'not_found_error',
            code: 404
        }
    });
});

// Error handling middleware
app.use((error, req, res, next) => {
    console.error('Unhandled error:', error);
    res.status(500).json({
        error: {
            message: 'Internal server error',
            type: 'internal_error',
            code: 500
        }
    });
});

// Start server
app.listen(port, () => {
    console.log(`🚀 Copilot API Proxy (Ultra-Fast) running on port ${port}`);
    console.log(`📖 OpenAI-compatible endpoints:`);
    console.log(`   GET  http://localhost:${port}/v1/models`);
    console.log(`   POST http://localhost:${port}/v1/chat/completions`);
    console.log(`💡 Health check: http://localhost:${port}/health`);
    console.log(`⚡ Ultra-fast transparent proxy mode enabled!`);
});

module.exports = { app, TokenManager };
