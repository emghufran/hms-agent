#!/bin/bash

# Initialize and get session ID
RESPONSE=$(curl -s -D - -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2024-11-05",
      "capabilities": {},
      "clientInfo": {
        "name": "curl-client",
        "version": "1.0.0"
      }
    }
  }')

# Extract session ID from headers
SESSION_ID=$(echo "$RESPONSE" | grep -i "mcp-session-id" | cut -d':' -f2 | tr -d ' \r')

echo "Session ID: $SESSION_ID"

# Now use the session to call tools
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "mcp-session-id: $SESSION_ID" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
      "name": "search_rooms",
      "arguments": {
        "input": {
          "hotel_id": 1,
          "check_in_date": "2026-01-15",
          "check_out_date": "2026-01-20",
          "min_capacity": 2
      }
      }
    }
  }'