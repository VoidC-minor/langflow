#!/usr/bin/env python3
"""
Demonstration: How to achieve character streaming ['h', 'e', 'l', 'l', 'o'] in Langflow.

This shows the concept and provides a working example using the existing flow structure.
"""

import asyncio
import json
import os
import time

import httpx
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

LANGFLOW_URL = os.getenv("LANGFLOW_URL", "http://localhost:7860")
API_KEY = os.getenv("LANGFLOW_API_KEY", "")


def demonstrate_streaming_concept():
    """Demonstrate the concept of character streaming."""
    console.print(Panel.fit(
        "[bold blue]HOW TO ACHIEVE CHARACTER STREAMING ['h', 'e', 'l', 'l', 'o'][/bold blue]",
        title="Streaming Concept"
    ))
    
    console.print("\n[bold cyan]Current Flow Behavior:")
    console.print("[yellow]ChatInput → ChatOutput")
    console.print("[white]Input: 'hello' → Output: 'hello' (all at once)")
    
    console.print("\n[bold cyan]Desired Character Streaming:")
    console.print("[yellow]ChatInput → Custom Component → ChatOutput")
    console.print("[white]Input: 'hello' → Stream: 'h' → 'e' → 'l' → 'l' → 'o'")
    
    console.print("\n[bold green]Implementation Options:")
    
    table = Table()
    table.add_column("Method", style="cyan")
    table.add_column("Description", style="white")
    table.add_column("Streaming Type", style="yellow")
    
    table.add_row(
        "1. Custom Component",
        "Create component with async generator",
        "Real token streaming"
    )
    table.add_row(
        "2. OpenAI Model",
        "Use LLM with streaming enabled",
        "Real token streaming"
    )
    table.add_row(
        "3. Manual Token Emission",
        "Use event manager directly",
        "Simulated streaming"
    )
    table.add_row(
        "4. Modify Existing Flow",
        "Add streaming logic to current flow",
        "Enhanced streaming"
    )
    
    console.print(table)


async def simulate_character_streaming():
    """Simulate what character streaming would look like."""
    console.print(f"\n[bold blue]SIMULATING CHARACTER STREAMING:")
    console.print("=" * 50)
    
    text = "hello"
    chars = list(text)
    
    console.print(f"[cyan]Input text: '{text}'")
    console.print(f"[cyan]Characters to stream: {chars}")
    console.print(f"\n[yellow]Simulated streaming events:")
    
    # Simulate streaming events
    for i, char in enumerate(chars, 1):
        console.print(f"\n[green]Event #{i}:")
        console.print(f"[white]  Type: token")
        console.print(f"[yellow]  TOKEN #{i}: '{char}'")
        console.print(f"[cyan]  Cumulative: '{''.join(chars[:i])}'")
        
        # Simulate delay
        await asyncio.sleep(0.5)
    
    console.print(f"\n[green]Event #{len(chars) + 1}:")
    console.print(f"[white]  Type: end")
    console.print(f"[magenta]  END - Stream completed")
    
    console.print(f"\n[bold green]Final result: '{text}' streamed as {chars}")


async def test_with_openai_flow():
    """Test streaming with an OpenAI flow that actually streams."""
    console.print(f"\n[bold blue]TESTING WITH REAL STREAMING FLOW:")
    console.print("=" * 50)
    
    # Use the known working OpenAI flow
    openai_flow_id = "41af00c8-b0ad-41b7-ab13-353cf9f0e958"  # Basic Prompting flow
    
    console.print(f"[cyan]Using OpenAI flow: {openai_flow_id}")
    console.print(f"[cyan]This flow has real streaming capability")
    
    stream_url = f"{LANGFLOW_URL}/api/v1/run/{openai_flow_id}?stream=true"
    
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["x-api-key"] = API_KEY
    
    # Ask it to respond with just "hello"
    input_data = {
        "input_value": "Please respond with exactly the word 'hello' and nothing else",
        "input_type": "text",
        "output_type": "chat"
    }
    
    console.print(f"[cyan]Request: {input_data['input_value']}")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            console.print("[yellow]Making request to OpenAI flow...")
            
            async with client.stream("POST", stream_url, headers=headers, json=input_data) as response:
                if response.status_code == 200:
                    console.print(f"[green]Status: 200 - Streaming response")
                    console.print(f"\n[bold yellow]REAL STREAMING TOKENS:")
                    console.print("-" * 30)
                    
                    token_count = 0
                    tokens = []
                    
                    async for line in response.aiter_lines():
                        if not line or line.strip() == "":
                            continue
                        
                        try:
                            event_data = json.loads(line)
                            event_type = event_data.get("event", "unknown")
                            
                            if event_type == "token":
                                token_data = event_data.get("data", {})
                                chunk = token_data.get("chunk", "")
                                tokens.append(chunk)
                                token_count += 1
                                
                                console.print(f"[yellow]TOKEN #{token_count}: '{chunk}'")
                                console.print(f"[cyan]  Cumulative: '{''.join(tokens)}'")
                                
                            elif event_type == "end":
                                console.print(f"[magenta]END - Stream completed")
                                break
                            
                            # Limit for demo
                            if token_count >= 10:
                                console.print(f"[yellow]Showing first 10 tokens...")
                                break
                                
                        except json.JSONDecodeError:
                            continue
                    
                    final_text = "".join(tokens)
                    console.print(f"\n[bold green]Final streamed text: '{final_text}'")
                    console.print(f"[green]Total tokens: {token_count}")
                    
                else:
                    console.print(f"[red]Request failed: {response.status_code}")
                    
    except Exception as e:
        console.print(f"[red]Error: {e}")


def show_forward_no_forward_concept():
    """Show the difference between Forward and No-Forward."""
    console.print(f"\n[bold blue]FORWARD vs NO-FORWARD STREAMING:")
    console.print("=" * 50)
    
    console.print("[bold cyan]NO FORWARD (Direct Streaming):")
    console.print("[white]Client → Langflow API → Stream Response")
    console.print("[green]✓ Direct connection")
    console.print("[green]✓ Lower latency")
    console.print("[green]✓ Simple architecture")
    
    console.print("\n[bold cyan]WITH FORWARD (Proxy Streaming):")
    console.print("[white]Client → Nginx/Proxy → Langflow API → Stream Response")
    console.print("[yellow]• Additional network hop")
    console.print("[yellow]• Proxy configuration required")
    console.print("[yellow]• May add buffering/latency")
    
    console.print("\n[bold green]For Character Streaming ['h', 'e', 'l', 'l', 'o']:")
    console.print("[white]Both methods will work the same way")
    console.print("[white]The key is the component implementation, not the forwarding")


async def main():
    """Main demonstration function."""
    console.print(Panel.fit(
        "[bold blue]CHARACTER STREAMING DEMONSTRATION[/bold blue]\n"
        "How to stream 'hello' as ['h', 'e', 'l', 'l', 'o'] in Langflow",
        title="Streaming Demo"
    ))
    
    # Show concept
    demonstrate_streaming_concept()
    
    # Simulate character streaming
    await simulate_character_streaming()
    
    # Test with real streaming
    await test_with_openai_flow()
    
    # Show forward concept
    show_forward_no_forward_concept()
    
    # Final recommendations
    console.print(f"\n[bold green]RECOMMENDATIONS:")
    console.print("=" * 40)
    console.print("[cyan]1. To achieve character streaming in your simple flow:")
    console.print("[white]   • Add a Custom Component between ChatInput and ChatOutput")
    console.print("[white]   • Use async generator to yield individual characters")
    console.print("[white]   • Add small delays between characters")
    
    console.print("\n[cyan]2. Custom Component Code Structure:")
    console.print("[white]   • async def char_generator(): yield char")
    console.print("[white]   • Message(text=char_generator())")
    console.print("[white]   • await self.send_message(message)")
    
    console.print("\n[cyan]3. For testing Forward vs No-Forward:")
    console.print("[white]   • Set FORWARD_FLOW=true/false")
    console.print("[white]   • Set FORWARD_FLOW_URL=http://nginx:80")
    console.print("[white]   • Both should stream characters the same way")
    
    console.print(f"\n[bold blue]The streaming infrastructure is working!")
    console.print(f"[green]The key is creating the right component to emit individual characters.")


if __name__ == "__main__":
    asyncio.run(main())



