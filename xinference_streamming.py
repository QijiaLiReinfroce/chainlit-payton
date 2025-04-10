import asyncio
import time as time_module
from openai import AsyncOpenAI

async def query_local_llm():
    # Initialize client with the correct external IP/port
    client = AsyncOpenAI(
        base_url="http://172.23.5.34:9997/v1",  # Use the address from curl
        api_key="empty",  # Placeholder (required by AsyncOpenAI)
    )

    try:
        # Prepare messages for the model
        messages = [
            {"role": "system", "content": "You are a helpful assistant. First think about the question in detail, then provide a concise answer."},
            {"role": "user", "content": "Tell me a short story about AI."}
        ]
        
        # Stream the response from the API
        stream = await client.chat.completions.create(
            model="Deepseek-R1",  # Use the model ID or name
            messages=messages,
            temperature=0.7,
            max_tokens=3000,
            stream=True  # Enable streaming
        )
        
        # Print the stream object to understand its structure
        print("\n=== STREAM OBJECT ===")
        print(f"Stream type: {type(stream)}")
        print(f"Stream dir: {dir(stream)}")
        print("=== END STREAM OBJECT ===\n")
        
        # Flag to track if we've exited the thinking step
        thinking_completed = False
        collected_reasoning = ""
        collected_content = ""

        start = time_module.time()

        print("thinking start =====================")
        
        # Streaming the thinking phase
        async for chunk in stream:
            # Print the first chunk to understand its structure
            if not thinking_completed and not collected_reasoning:
                print("\n=== FIRST CHUNK OBJECT (THINKING) ===")
                print(f"Chunk type: {type(chunk)}")
                print(f"Chunk dir: {dir(chunk)}")
                print(f"Chunk repr: {repr(chunk)}")
                print(f"Chunk choices: {chunk.choices}")
                print(f"Chunk delta type: {type(chunk.choices[0].delta)}")
                print(f"Chunk delta dir: {dir(chunk.choices[0].delta)}")
                print(f"Chunk delta repr: {repr(chunk.choices[0].delta)}")
                print("=== END FIRST CHUNK OBJECT ===\n")
            
            delta = chunk.choices[0].delta
            
            # Try to get reasoning_content (if available in the model's response)
            reasoning_content = getattr(delta, "reasoning_content", None)
            
            # Print reasoning content for debugging
            print(reasoning_content, end="", flush=True)
            
            if reasoning_content is not None and not thinking_completed:
                collected_reasoning += reasoning_content
            else:
                # If no reasoning_content is found, check for regular content
                content = getattr(delta, "content", None)
                
                # If this is the first content after reasoning (or if no reasoning at all)
                if content is not None and not thinking_completed:
                    # Exit the thinking step
                    thought_for = round(time_module.time() - start)
                    print(f"\nThought for {thought_for}s")
                    thinking_completed = True
                    print("\nthinking end =====================")
                    print("\nfinal answer start =====================")
                
                # Print and collect content
                if content is not None:
                    print(content, end="", flush=True)
                    collected_content += content
        
        print("\nfinal answer end =====================")
        
        # Print the final collected content
        print("\n\n=== FINAL COLLECTED CONTENT ===")
        print(collected_content)
        print("=== END FINAL COLLECTED CONTENT ===")

    except Exception as e:
        print(f"Error: {e}")

# Run the async function
asyncio.run(query_local_llm())