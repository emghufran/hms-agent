#!/usr/bin/env python3
"""
Simple MCP HTTP client to test your HMS MCP server
Usage: uv run python test_mcp.py
"""

import json
import requests

BASE_URL = "http://localhost:8000/mcp"


class MCPClient:
    def __init__(self, base_url):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            }
        )
        self.request_id = 0
        self.session_id = None

    def _next_id(self):
        self.request_id += 1
        return self.request_id

    def _send_request(self, method, params=None):
        payload = {"jsonrpc": "2.0", "id": self._next_id(), "method": method}
        if params:
            payload["params"] = params

        # Add session ID header if we have one
        headers = {}
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id

        print(f"   Sending: {method}")
        if self.session_id:
            print(f"   Using Session-ID: {self.session_id[:20]}...")

        resp = self.session.post(
            self.base_url, json=payload, headers=headers, stream=True
        )

        # Capture session ID from response headers (only on initialize)
        if method == "initialize" and "mcp-session-id" in resp.headers:
            self.session_id = resp.headers["mcp-session-id"]
            print(f"   ✓ Received Session-ID: {self.session_id[:20]}...")

        # Parse SSE response - collect all data events
        results = []
        for line in resp.iter_lines():
            if line:
                line = line.decode("utf-8")
                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])  # Remove 'data: ' prefix
                        results.append(data)
                    except json.JSONDecodeError as e:
                        print(f"   JSON parse error: {e}")
                        continue

        # Return the last result (usually the actual response)
        if results:
            return results[-1]
        return None

    def initialize(self):
        """Initialize the MCP session"""
        result = self._send_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "python-test-client", "version": "1.0.0"},
            },
        )
        print("✓ Initialized MCP session")
        return result

    def send_initialized_notification(self):
        """Send initialized notification after initialize"""
        payload = {"jsonrpc": "2.0", "method": "notifications/initialized"}

        headers = {"Mcp-Session-Id": self.session_id} if self.session_id else {}

        print("   Sending: notifications/initialized")

        self.session.post(self.base_url, json=payload, headers=headers)
        print("   ✓ Sent initialized notification")

    def list_tools(self):
        """List available tools"""
        result = self._send_request("tools/list")
        return result

    def call_tool(self, tool_name, arguments):
        """Call a specific tool"""
        result = self._send_request(
            "tools/call", {"name": tool_name, "arguments": arguments}
        )
        return result


def main():
    print("=== HMS MCP Server Test ===\n")

    client = MCPClient(BASE_URL)

    # Step 1: Initialize
    print("1. Initializing session...")
    init_result = client.initialize()
    if init_result and "result" in init_result:
        print(f"   Server: {init_result['result']['serverInfo']['name']}\n")
    else:
        print("   ERROR: Failed to initialize\n")
        return

    # Step 1.5: Send initialized notification
    print("1.5. Sending initialized notification...")
    client.send_initialized_notification()
    print()

    # Step 2: List tools
    print("2. Listing available tools...")
    tools_result = client.list_tools()
    if tools_result and "result" in tools_result:
        tools = tools_result["result"].get("tools", [])
        print(f"   Found {len(tools)} tools:")
        for tool in tools:
            print(f"   - {tool['name']}: {tool.get('description', 'No description')}")
    else:
        print("   Warning: Could not retrieve tools list")
        print(f"   Response: {tools_result}")
    print()

    # Step 2.1: Search for hotels (no location)
    print("2.1 Searching for all hotels...")
    hotels_all_result = client.call_tool("search_hotels", {})
    if hotels_all_result and "result" in hotels_all_result:
        content = hotels_all_result["result"].get("content", [])
        if content:
            result_data = json.loads(content[0].get("text", "{}"))
            hotels = result_data.get("hotels", [])
            print(f"   ✓ Found {len(hotels)} hotels total")
    else:
        print(f"   Failed: {hotels_all_result}")
    print()

    # Step 2.2: Create and Search Customer
    print("2.2 Testing customer management...")
    customer_params = {"name": "Alice Smith", "phone_number": "555-0123"}
    print(f"   Creating customer: {customer_params['name']}...")
    create_res = client.call_tool("create_customer_entry", customer_params)

    if create_res and "result" in create_res:
        print("   ✓ Success!")

        print(
            f"   Searching for customer by phone: {customer_params['phone_number']}..."
        )
        search_res = client.call_tool(
            "search_customers", {"phone_number": customer_params["phone_number"]}
        )
        if search_res and "result" in search_res:
            content = search_res["result"].get("content", [])
            if content:
                res_data = json.loads(content[0].get("text", "{}"))
                customers = res_data.get("customers", [])
                if customers:
                    print(
                        f"   ✓ Found customer: {customers[0]['name']} (ID: {customers[0]['id']})"
                    )
                else:
                    print("   Failed: Customer not found after creation")
        else:
            print(f"   Search Failed: {search_res}")
    else:
        print(f"   Creation Failed: {create_res}")
    print()

    # Step 3: Search for rooms
    print("3. Searching for available rooms...")
    search_result = client.call_tool(
        "search_rooms",
        {
            "hotel_id": 1,
            "check_in_date": "2026-01-15",
            "check_out_date": "2026-01-20",
            "min_capacity": 2,
        },
    )

    if search_result and "result" in search_result:
        print("   ✓ Success!")
        content = search_result["result"].get("content", [])
        booking_id = None
        if content and len(content) > 0:
            result_data = json.loads(content[0].get("text", "{}"))
            rooms = result_data.get("rooms", [])
            print(f"   Found {len(rooms)} available rooms")
            for room in rooms[:]:  # Show rooms
                print(
                    f"     - Room {room['room_number']}: {room['room_type']} (${room['price_per_night']}/night)"
                )

            # Step 4: Create a reservation if rooms found
            if rooms:
                room_id = rooms[0]["id"]
                print(f"\n4. Creating reservation for room {room_id}...")
                booking_result = client.call_tool(
                    "create_reservation",
                    {
                        "customer_id": 1,
                        "room_id": room_id,
                        "check_in_date": "2026-01-15",
                        "check_out_date": "2026-01-20",
                    },
                )

                if booking_result and "result" in booking_result:
                    print("   ✓ Success!")
                    content = booking_result["result"].get("content", [])
                    if content:
                        booking_data = json.loads(content[0].get("text", "{}"))
                        booking_id = booking_data.get("booking_id")
                        print(f"   Booking ID: {booking_id}")
                        print(f"   Status: {booking_data.get('status')}")
                else:
                    print(f"   Failed: {booking_result}")

            # Step 5: Cancel the reservation
            if booking_id:
                print(f"\n5. Cancelling reservation {booking_id}...")
                cancel_result = client.call_tool(
                    "cancel_reservation", {"booking_id": booking_id}
                )

                if cancel_result and "result" in cancel_result:
                    content = cancel_result["result"].get("content", [])
                    if content:
                        cancel_data = json.loads(content[0].get("text", "{}"))
                        print(f"   ✓ Cancelled booking {cancel_data.get('booking_id')}")
                        print(f"   Status: {cancel_data.get('status')}")
                else:
                    print(f"   Failed to cancel booking: {cancel_result}")
            else:
                print("\n4. No rooms available to book")
        else:
            print("   No rooms data in response")
    else:
        print(f"   Failed: {search_result}")

    print("\n=== Test Complete ===")


if __name__ == "__main__":
    main()
