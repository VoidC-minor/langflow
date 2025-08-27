#!/usr/bin/env python3
"""
Test script for OpenAI Compatible API endpoint in Langflow

This script tests the current OpenAI endpoint implementation that redirects
to flow-specific endpoints.

Usage:
    python test_openai_endpoint.py

Requirements:
    - Running Langflow instance 
    - Valid API key
    - Valid flow ID
"""

import asyncio
import httpx
import json
import os
from typing import Dict, Any

# Configuration - adjust these values for your setup
LANGFLOW_BASE_URL = os.getenv("LANGFLOW_BASE_URL", "http://localhost:7860")
API_KEY = os.getenv("LANGFLOW_API_KEY", "")  
FLOW_ID = os.getenv("LANGFLOW_FLOW_ID", "581f2884-3260-4982-ba08-bea27c14a857e")

# Test data in OpenAI-compatible format
OPENAI_REQUEST_EXAMPLE = {
    "messages": [
        {
            "role": "system",
            "content": "You are a helpful assistant."
        },
        {
            "role": "user", 
            "content": "What is the capital of France?"
        }
    ],
    "model": FLOW_ID,  # Using flow_id as model
    "temperature": 0.7,
    "max_tokens": 150
}

async def test_openai_endpoint():
    """Test the /openai_run_flow endpoint."""
    print("Testing OpenAI endpoint: /api/v1/openai_run_flow")
    
    headers = {
        "Content-Type": "application/json"
    }
    
    # Add API key if provided
    if API_KEY and API_KEY != "your-api-key-here":
        headers["Authorization"] = f"Bearer {API_KEY}"
        headers["x-api-key"] = API_KEY
    
    url = f"{LANGFLOW_BASE_URL}/api/v1/openai_run_flow"
    
    try:
        async with httpx.AsyncClient(follow_redirects=False, timeout=30.0) as client:
            print(f"Making request to: {url}")
            print(f"Request headers: {headers}")
            print(f"Request body: {json.dumps(OPENAI_REQUEST_EXAMPLE, indent=2)}")
            
            response = await client.post(
                url,
                json=OPENAI_REQUEST_EXAMPLE,
                headers=headers
            )
            
            print(f"Status Code: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                print("Flow execution successful!")
                result = response.json()
                print(f"Response: {json.dumps(result, indent=2)}")
                
            else:
                print(f"Error: {response.status_code}")
                print(f"Response: {response.text}")
                
    except Exception as e:
        print(f"Exception: {e}")

async def test_redirect_target(redirect_url: str, headers: Dict[str, str]):
    """Test the redirect target URL."""
    print(f"\nFollowing redirect to: {redirect_url}")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Convert OpenAI format to Langflow format for the redirect target
            langflow_request = {
                "input_value": OPENAI_REQUEST_EXAMPLE["messages"][-1]["content"],
                "input_type": "chat",
                "output_type": "chat",
                "tweaks": {
                    "temperature": OPENAI_REQUEST_EXAMPLE.get("temperature", 0.7),
                    "max_tokens": OPENAI_REQUEST_EXAMPLE.get("max_tokens", 150)
                }
            }
            
            response = await client.post(
                redirect_url,
                json=langflow_request,
                headers=headers
            )
            
            print(f"Redirect Target Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print("Flow execution successful!")
                print(f"Flow Response: {json.dumps(result, indent=2)}")
            else:
                print(f"Flow execution failed: {response.status_code}")
                print(f"Error Response: {response.text}")
                
    except Exception as e:
        print(f"Redirect test exception: {e}")

async def test_direct_flow_endpoint():
    """Test calling the flow endpoint directly for comparison."""
    print(f"\nTesting direct flow endpoint: /api/v1/run/{FLOW_ID}")
    
    headers = {
        "Content-Type": "application/json"
    }
    
    if API_KEY and API_KEY != "your-api-key-here":
        headers["Authorization"] = f"Bearer {API_KEY}"
        headers["x-api-key"] = API_KEY
    
    # Convert OpenAI format to Langflow format
    langflow_request = {
        "input_value": OPENAI_REQUEST_EXAMPLE["messages"][-1]["content"],
        "input_type": "chat", 
        "output_type": "chat",
        "tweaks": {
            "temperature": OPENAI_REQUEST_EXAMPLE.get("temperature", 0.7),
            "max_tokens": OPENAI_REQUEST_EXAMPLE.get("max_tokens", 150)
        }
    }
    
    url = f"{LANGFLOW_BASE_URL}/api/v1/run/{FLOW_ID}"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            print(f"Making direct request to: {url}")
            print(f"Request body: {json.dumps(langflow_request, indent=2)}")
            
            response = await client.post(
                url,
                json=langflow_request,
                headers=headers
            )
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print("Direct flow execution successful!")
                print(f"Response: {json.dumps(result, indent=2)}")
            else:
                print(f"Direct flow execution failed: {response.status_code}")
                print(f"Error Response: {response.text}")
                
    except Exception as e:
        print(f"Direct test exception: {e}")

def test_request_parsing():
    """Test the OpenAI request parsing logic."""
    print("\nTesting OpenAI request parsing logic...")
    
    # Simulate the parsing logic from the endpoint
    input_request = OPENAI_REQUEST_EXAMPLE
    
    # Extract flow_id from model field
    flow_id = input_request.get("model")
    print(f"Extracted flow_id: {flow_id}")
    
    # Extract messages
    messages = input_request.get("messages", [])
    user_messages = [msg["content"] for msg in messages if msg["role"] == "user"]
    system_messages = [msg["content"] for msg in messages if msg["role"] == "system"]
    
    print(f"User messages: {user_messages}")
    print(f"System messages: {system_messages}")
    
    # Show the conversion to Langflow format
    langflow_format = {
        "input_value": user_messages[-1] if user_messages else "",
        "input_type": "chat",
        "output_type": "chat", 
        "tweaks": {
            "temperature": input_request.get("temperature"),
            "max_tokens": input_request.get("max_tokens")
        }
    }
    
    if system_messages:
        langflow_format["tweaks"]["system_message"] = system_messages[0]
    
    print("Conversion to Langflow format:")
    print(json.dumps(langflow_format, indent=2))

async def test_error_cases():
    """Test error handling."""
    print("\nTesting error cases...")
    
    headers = {
        "Content-Type": "application/json"
    }
    
    if API_KEY and API_KEY != "your-api-key-here":
        headers["Authorization"] = f"Bearer {API_KEY}"
        headers["x-api-key"] = API_KEY
    
    url = f"{LANGFLOW_BASE_URL}/api/v1/openai_run_flow"
    
    # Test 1: Missing model field
    print("Test 1: Missing model field")
    try:
        async with httpx.AsyncClient(follow_redirects=False, timeout=10.0) as client:
            invalid_request = {
                "messages": [{"role": "user", "content": "Hello"}]
                # Missing "model" field
            }
            
            response = await client.post(url, json=invalid_request, headers=headers)
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"Exception: {e}")
    
    # Test 2: Invalid flow ID
    print("\nTest 2: Invalid flow ID")
    try:
        async with httpx.AsyncClient(follow_redirects=False, timeout=10.0) as client:
            invalid_request = {
                "messages": [{"role": "user", "content": "Hello"}],
                "model": "invalid-flow-id-12345"
            }
            
            response = await client.post(url, json=invalid_request, headers=headers)
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"Exception: {e}")

async def test_openai_flow_by_id():
    """Test the flow-specific OpenAI endpoint."""
    print(f"\nTesting flow-specific OpenAI endpoint: /api/v1/openai_run_flow/{FLOW_ID}")
    
    headers = {
        "Content-Type": "application/json"
    }
    
    if API_KEY and API_KEY != "your-api-key-here":
        headers["Authorization"] = f"Bearer {API_KEY}"
        headers["x-api-key"] = API_KEY
    
    url = f"{LANGFLOW_BASE_URL}/api/v1/openai_run_flow/{FLOW_ID}"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            print(f"Making request to: {url}")
            print(f"Request body: {json.dumps(OPENAI_REQUEST_EXAMPLE, indent=2)}")
            
            response = await client.post(
                url,
                json=OPENAI_REQUEST_EXAMPLE,
                headers=headers
            )
            
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

async def test_get_models():
    """Test the get models endpoint."""
    print("\nTesting get models endpoint: /api/v1/v1/models")
    
    headers = {
        "Content-Type": "application/json"
    }
    
    if API_KEY and API_KEY != "your-api-key-here":
        headers["Authorization"] = f"Bearer {API_KEY}"
        headers["x-api-key"] = API_KEY
    
    url = f"{LANGFLOW_BASE_URL}/api/v1/v1/models"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            print(f"Making request to: {url}")
            
            response = await client.get(url, headers=headers)
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print("Models retrieval successful!")
                print(f"Response: {json.dumps(result, indent=2)}")
            else:
                print(f"Models retrieval failed: {response.status_code}")
                print(f"Error Response: {response.text}")
                
    except Exception as e:
        print(f"Models test exception: {e}")

async def main():
    """Main test function."""
    print("Starting OpenAI Compatible API Tests for Langflow")
    print("=" * 60)
    
    # Show configuration
    print("Configuration:")
    print(f"   Base URL: {LANGFLOW_BASE_URL}")
    print(f"   API Key: {'***' if API_KEY != 'your-api-key-here' else 'Not set'}")
    print(f"   Flow ID: {FLOW_ID}")
    print()
    
    # Check if configuration is set
    if API_KEY == "your-api-key-here" or FLOW_ID == "your-flow-id-here":
        print("Warning: Please set environment variables or update the script:")
        print("   export LANGFLOW_API_KEY=your-actual-api-key")
        print("   export LANGFLOW_FLOW_ID=your-actual-flow-id")
        print("   export LANGFLOW_BASE_URL=http://your-langflow-instance:port")
        print()
    
    # Run tests
    test_request_parsing()
    await test_openai_endpoint()
    
    if API_KEY != "your-api-key-here" and FLOW_ID != "your-flow-id-here":
        await test_openai_flow_by_id()
        await test_direct_flow_endpoint()
        await test_get_models()
    
    await test_error_cases()
    
    print("\n" + "=" * 60)
    print("Tests completed!")
    
    # Show usage examples
    print("\nUsage Examples:")
    print("1. Generic OpenAI-compatible endpoint:")
    print(f"   POST {LANGFLOW_BASE_URL}/api/v1/openai_run_flow")
    print("   Headers: Authorization: Bearer <api-key>")
    print('   Body: {"messages": [...], "model": "<flow_id>"}')
    
    print("\n2. Flow-specific OpenAI endpoint:")
    print(f"   POST {LANGFLOW_BASE_URL}/api/v1/v1/openai_run_flow/<flow_id>")
    print("   Headers: Authorization: Bearer <api-key>")
    print('   Body: {"messages": [...]}')
    
    print("\n3. Get available models:")
    print(f"   GET {LANGFLOW_BASE_URL}/api/v1/v1/models")
    print("   Headers: Authorization: Bearer <api-key>")
    
    print("\n4. Direct Langflow endpoint (for comparison):")
    print(f"   POST {LANGFLOW_BASE_URL}/run/<flow_id>")
    print("   Headers: Authorization: Bearer <api-key>")
    print('   Body: {"input_value": "...", "input_type": "chat", ...}')

if __name__ == "__main__":
    asyncio.run(main())
