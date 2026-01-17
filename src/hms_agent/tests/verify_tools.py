#!/usr/bin/env python3
import json
import requests
import sys

BASE_URL = "http://localhost:8000/mcp"

class MCPClient:
    def __init__(self, base_url):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        })
        self.request_id = 0
        self.session_id = None

    def _next_id(self):
        self.request_id += 1
        return self.request_id

    def _send_request(self, method, params=None):
        payload = {"jsonrpc": "2.0", "id": self._next_id(), "method": method}
        if params: payload["params"] = params
        
        headers = {}
        if self.session_id: headers["Mcp-Session-Id"] = self.session_id

        resp = self.session.post(self.base_url, json=payload, headers=headers, stream=True)
        if method == "initialize" and "mcp-session-id" in resp.headers:
            self.session_id = resp.headers["mcp-session-id"]

        results = []
        for line in resp.iter_lines():
            if line:
                line = line.decode("utf-8")
                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                        results.append(data)
                    except: continue
        return results[-1] if results else None

    def initialize(self):
        res = self._send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "verify-client", "version": "1.0.0"},
        })
        # Send initialized notification
        self.session.post(self.base_url, json={"jsonrpc": "2.0", "method": "notifications/initialized"}, 
                         headers={"Mcp-Session-Id": self.session_id})
        return res

    def call_tool(self, tool_name, arguments):
        return self._send_request("tools/call", {"name": tool_name, "arguments": arguments})

def main():
    client = MCPClient(BASE_URL)
    if not client.initialize():
        print("Failed to initialize")
        sys.exit(1)

    print("1. Testing search_hotels with location_id=1")
    res = client.call_tool("search_hotels", {"location_id": 1})
    text = res["result"]["content"][0]["text"]
    hotels = json.loads(text).get("hotels", [])
    print(f"   Found {len(hotels)} hotels")

    print("\n2. Testing search_hotels with location_id=None")
    res = client.call_tool("search_hotels", {})
    text = res["result"]["content"][0]["text"]
    hotels = json.loads(text).get("hotels", [])
    print(f"   Found {len(hotels)} hotels (total)")

    print("\n3. Testing create_customer_entry")
    customer_params = {"name": "John Doe", "phone_number": "1234567890"}
    res = client.call_tool("create_customer_entry", customer_params)
    text = res["result"]["content"][0]["text"]
    created_customer = json.loads(text)
    print(f"   Created customer: {created_customer}")

    print("\n4. Testing search_customers by name")
    res = client.call_tool("search_customers", {"name": "John Doe"})
    text = res["result"]["content"][0]["text"]
    customers = json.loads(text).get("customers", [])
    print(f"   Found {len(customers)} customers by name")

    print("\n5. Testing search_customers by phone_number")
    res = client.call_tool("search_customers", {"phone_number": "1234567890"})
    text = res["result"]["content"][0]["text"]
    customers = json.loads(text).get("customers", [])
    print(f"   Found {len(customers)} customers by phone_number")

if __name__ == "__main__":
    main()
