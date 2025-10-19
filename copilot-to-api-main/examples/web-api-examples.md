# Web API Servers Usage Examples

## Starting the Servers

### Node.js Server (Port 3000)
```bash
npm install
npm start
```

### Python Server (Port 5000)
```bash
pip install -r requirements.txt
python server.py
```

## OpenAI-Compatible Endpoints

### 1. Get Available Models

```bash
# Node.js server
curl http://localhost:3000/v1/models

# Python server
curl http://localhost:5000/v1/models
```

### 2. Chat Completions

```bash
# Node.js server
curl -X POST http://localhost:3000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Write a Python function to calculate factorial"}
    ],
    "max_tokens": 1000,
    "temperature": 0.3
  }'

# Python server
curl -X POST http://localhost:5000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Write a Python function to calculate factorial"}
    ],
    "max_tokens": 1000,
    "temperature": 0.3
  }'
```

## Compatibility with OpenAI Libraries

### JavaScript/Node.js
```javascript
import OpenAI from 'openai';

const openai = new OpenAI({
  baseURL: 'http://localhost:3000/v1',
  apiKey: 'dummy-key' // Not used but required
});

const completion = await openai.chat.completions.create({
  model: 'gpt-4o',
  messages: [
    { role: 'user', content: 'Hello, how are you?' }
  ]
});

console.log(completion.choices[0].message.content);
```

### Python
```python
import openai

# Configure client to use our local server
openai.api_base = "http://localhost:5000/v1"
openai.api_key = "dummy-key"  # Not used but required

response = openai.ChatCompletion.create(
    model="gpt-4o",
    messages=[
        {"role": "user", "content": "Hello, how are you?"}
    ]
)

print(response.choices[0].message.content)
```

### Python with requests directly
```python
import requests

response = requests.post('http://localhost:5000/v1/chat/completions', 
    headers={'Content-Type': 'application/json'},
    json={
        'messages': [
            {'role': 'user', 'content': 'Hello, how are you?'}
        ],
        'max_tokens': 1000,
        'temperature': 0.3
    }
)

print(response.json()['choices'][0]['message']['content'])
```

## Health Check

```bash
# Node.js server
curl http://localhost:3000/health

# Python server
curl http://localhost:5000/health
```

## Features

- ✅ **OpenAI-compatible endpoints**: `/v1/models` and `/v1/chat/completions`
- ✅ **Smart token management**: Uses `expires_at` from API response for precise token refresh timing
- ✅ **CORS enabled**: Allows requests from web browsers
- ✅ **Error handling**: OpenAI-format error responses
- ✅ **Logging**: All requests are logged with timestamps
- ✅ **Health checks**: Endpoint for service monitoring

## Production configuration

### Environment variables
```bash
# Custom port
PORT=8080 node server.js
PORT=8080 python server.py
```

### Docker (optional)
```dockerfile
# Dockerfile for Node.js
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
EXPOSE 3000
CMD ["npm", "start"]

# Dockerfile for Python
FROM python:3.9-alpine
WORKDIR /app
COPY requirements.txt ./
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "server.py"]
```
