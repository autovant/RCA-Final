#!/bin/bash

echo "🧪 Testing Copilot API Servers"
echo "==============================="

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Función para probar endpoint
test_endpoint() {
    local url=$1
    local description=$2
    
    echo -e "\n${YELLOW}Testing: ${description}${NC}"
    echo "URL: $url"
    
    if curl -s --connect-timeout 5 "$url" > /dev/null; then
        echo -e "${GREEN}✅ Success${NC}"
        return 0
    else
        echo -e "${RED}❌ Failed${NC}"
        return 1
    fi
}

# Función para probar POST endpoint
test_post_endpoint() {
    local url=$1
    local data=$2
    local description=$3
    
    echo -e "\n${YELLOW}Testing: ${description}${NC}"
    echo "URL: $url"
    
    response=$(curl -s --connect-timeout 5 -X POST "$url" \
        -H "Content-Type: application/json" \
        -d "$data")
    
    if [ $? -eq 0 ] && [[ $response == *"choices"* || $response == *"data"* ]]; then
        echo -e "${GREEN}✅ Success${NC}"
        echo "Response preview: $(echo $response | cut -c1-100)..."
        return 0
    else
        echo -e "${RED}❌ Failed${NC}"
        echo "Response: $response"
        return 1
    fi
}

echo -e "\n🔍 Checking if servers are running..."

# Test Node.js server (puerto 3000)
echo -e "\n${YELLOW}=== Node.js Server (Port 3000) ===${NC}"
if curl -s --connect-timeout 2 http://localhost:3000/health > /dev/null; then
    echo -e "${GREEN}✅ Node.js server is running${NC}"
    
    # Test endpoints
    test_endpoint "http://localhost:3000/health" "Health check"
    test_endpoint "http://localhost:3000/v1/models" "Models endpoint"
    test_post_endpoint "http://localhost:3000/v1/chat/completions" \
        '{"messages":[{"role":"user","content":"Hello"}],"max_tokens":50}' \
        "Chat completions endpoint"
else
    echo -e "${RED}❌ Node.js server is not running on port 3000${NC}"
    echo "   Start it with: npm start"
fi

# Test Python server (puerto 5000)
echo -e "\n${YELLOW}=== Python Server (Port 5000) ===${NC}"
if curl -s --connect-timeout 2 http://localhost:5000/health > /dev/null; then
    echo -e "${GREEN}✅ Python server is running${NC}"
    
    # Test endpoints
    test_endpoint "http://localhost:5000/health" "Health check"
    test_endpoint "http://localhost:5000/v1/models" "Models endpoint"
    test_post_endpoint "http://localhost:5000/v1/chat/completions" \
        '{"messages":[{"role":"user","content":"Hello"}],"max_tokens":50}' \
        "Chat completions endpoint"
else
    echo -e "${RED}❌ Python server is not running on port 5000${NC}"
    echo "   Start it with: python server.py"
fi

echo -e "\n${YELLOW}=== Quick Start Commands ===${NC}"
echo "Start Node.js server:  npm start"
echo "Start Python server:   python server.py"
echo "Test health:           curl http://localhost:3000/health"
echo "Test models:           curl http://localhost:3000/v1/models"

echo -e "\n🎉 Testing complete!"
