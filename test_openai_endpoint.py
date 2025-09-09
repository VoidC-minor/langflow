#!/usr/bin/env python3
"""
Test script for OpenAI-compatible flow-by-ID endpoint in Langflow.

This script lists available flows (like test_streaming.py) and lets the user
pick a flow ID to test the OpenAI-compatible endpoint:
    POST /api/v1/openai_run_flow/{flow_id}

Usage:
    python test_openai_endpoint.py [optional_flow_id]

Requirements:
    - Running Langflow instance
    - Valid API key (if your instance requires it)
"""

import asyncio
import httpx
import json
import os
import sys

from test_streaming import get_available_flows

# Configuration - align with test_streaming.py, but keep compatibility
LANGFLOW_URL = os.getenv("LANGFLOW_URL") or os.getenv("LANGFLOW_BASE_URL", "http://localhost:7860")
API_KEY = os.getenv("LANGFLOW_API_KEY", "")
FLOW_ID = "ec8fd11e-ba02-45a2-8d13-a15aabb4e0a6"


async def test_openai_flow_by_id(flow_id: str):
    """Test the flow-specific OpenAI-compatible endpoint: /api/v1/openai_run_flow/{flow_id}."""
    print(f"\nTesting flow-specific OpenAI endpoint: /api/v1/openai_run_flow/{flow_id}")

    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
        headers["x-api-key"] = API_KEY

    # Build request body in OpenAI-compatible format
    request_body = {
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is the capital of France?"},
        ],
        "model": flow_id,
        "temperature": 0.7,
        "max_tokens": 150,
    }

    url = f"{LANGFLOW_URL}/api/v1/openai_run_flow/{flow_id}"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            print(f"Making request to: {url}")
            print(f"Request body: {json.dumps(request_body, indent=2)}")

            response = await client.post(url, json=request_body, headers=headers)

            print(f"Status Code: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                print("Flow-specific execution successful!")
                print(f"Response: {json.dumps(result, indent=2)}")
            else:
                print(f"Flow-specific execution failed: {response.status_code}")
                print(f"Error Response: {response.text}")

    except Exception as e:
        print(f"Flow-specific test exception: {e}")


async def main():
    """Main function: list flows, accept user input, and test by ID."""
    print("Starting OpenAI-compatible Flow-by-ID Test for Langflow")
    print("=" * 60)

    print("Configuration:")
    print(f"   Base URL: {LANGFLOW_URL}")
    print(f"   API Key: {'***' if API_KEY else 'Not set'}")
    print()

    # Determine flow ID from CLI arg or prompt user after listing flows
    if len(sys.argv) > 1:
        flow_id = sys.argv[1].strip()
        print(f"Using flow ID from command line: {flow_id}")
    else:
        # Show available flows to help the user choose
        await get_available_flows()
        prompt = "Enter Flow ID to test"
        user_input = input(f"{prompt}: ").strip()
        flow_id = user_input or FLOW_ID

    if not flow_id:
        print("No flow ID provided. Exiting.")
        return

    await test_openai_flow_by_id(flow_id)

if __name__ == "__main__":
    asyncio.run(main())
