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
        
        # Initialize state and collectors
        STATE_PRE_THINKING = 0
        STATE_THINKING_TAG = 1
        STATE_POST_THINKING = 2
        current_state = STATE_PRE_THINKING
        
        collected_reasoning = ""
        collected_content = ""

        start = time_module.time()

        print("Reasoning: ")
        
        # Process the stream chunk by chunk
        async for chunk in stream:
            delta = chunk.choices[0].delta
            content_chunk = getattr(delta, "content", None)

            if content_chunk:
                remaining_chunk = content_chunk
                
                while remaining_chunk:
                    if current_state == STATE_PRE_THINKING:
                        if '<' in remaining_chunk:
                            parts = remaining_chunk.split('<', 1)
                            reasoning_part = parts[0]
                            if reasoning_part:
                                print(reasoning_part, end="", flush=True)
                                collected_reasoning += reasoning_part
                            current_state = STATE_THINKING_TAG
                            remaining_chunk = parts[1]
                        else:
                            print(remaining_chunk, end="", flush=True)
                            collected_reasoning += remaining_chunk
                            remaining_chunk = ""
                            
                    elif current_state == STATE_THINKING_TAG:
                        if '>' in remaining_chunk:
                            parts = remaining_chunk.split('>', 1)
                            current_state = STATE_POST_THINKING
                            remaining_chunk = parts[1]
                            # Mark thinking end
                            thought_for = round(time_module.time() - start)
                            print(f"\n\nThought for {thought_for}s")
                            print("\nFinal Answer: ")
                        else:
                            # Ignore content within tags
                            remaining_chunk = ""
                            
                    elif current_state == STATE_POST_THINKING:
                        print(remaining_chunk, end="", flush=True)
                        collected_content += remaining_chunk
                        remaining_chunk = ""
        
        # Final print statements if needed
        if current_state == STATE_PRE_THINKING:
            # If no tags were found, maybe mark thinking end here?
            thought_for = round(time_module.time() - start)
            print(f"\n\nThought for {thought_for}s (No tags found)")
            print("\nFinal Answer: ")
        elif current_state == STATE_THINKING_TAG:
             # Stream ended while inside tags?
             thought_for = round(time_module.time() - start)
             print(f"\n\nThought for {thought_for}s (Stream ended unexpectedly)")
             print("\nFinal Answer: ")
        
        print("\n\n--- Stream End ---")
        
        # Print the final collected content
        print("\n=== FINAL COLLECTED REASONING ===")
        print(collected_reasoning)
        print("=== END FINAL COLLECTED REASONING ===")
        
        print("\n=== FINAL COLLECTED CONTENT ===")
        print(collected_content)
        print("=== END FINAL COLLECTED CONTENT ===")

    except Exception as e:
        print(f"Error: {e}")

# Run the async function
asyncio.run(query_local_llm())