# CLI Scripts Usage Examples

## Initial Setup

1. **Configure the access token** in `config.json`:
   ```json
   {
     "access_token": "your_access_token_here",
     "client_id": "Iv1.b507a08c87ecfe98"
   }
   ```

2. **For Python**, install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage Examples

### Node.js

```bash
# View available models
node copilot-client.js models

# Ask a question
node copilot-client.js chat "Write a function to calculate fibonacci numbers"

# With custom options
node copilot-client.js chat "Explain machine learning" --max-tokens 500 --temperature 0.7

# Send file content
echo "How can I optimize this code?" > prompt.txt
node copilot-client.js chat-file prompt.txt
```

### Python

```bash
# View available models
python copilot_client.py models

# Ask a question
python copilot_client.py chat "Write a function to calculate fibonacci numbers"

# With custom options
python copilot_client.py chat "Explain machine learning" --max-tokens 500 --temperature 0.7

# Send file content
echo "How can I optimize this code?" > prompt.txt
python copilot_client.py chat-file prompt.txt
```

## Main Features

- ✅ **Auto-refresh token**: Scripts automatically detect when token expires (every 25 minutes) and renew it
- ✅ **Error handling**: Robust handling of network and authentication errors
- ✅ **Multiple commands**: Support for getting models and making chat completions
- ✅ **Configurable options**: max_tokens, temperature, streaming
- ✅ **File input**: Allows sending prompts from text files
- ✅ **Usage information**: Shows tokens used in each request

## Important Notes

- Tokens expire every 25 minutes, but scripts renew them automatically
- Recommended to make maximum 1 request every 2 seconds to avoid rate limits
- Scripts save token expiration time to optimize renewals
- These CLI scripts are perfect for automation, scripting, and one-off tasks

## When to Use CLI vs Web API

**Use CLI scripts when:**
- You need quick one-time queries
- Building automation scripts
- Working in command-line environments
- Want minimal setup and dependencies

**Use Web API servers when:**
- Integrating with existing applications
- Need OpenAI-compatible endpoints
- Building web applications or services
- Want to use existing OpenAI client libraries
