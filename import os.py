import os
import time
import openai
import AsyncOpenAI
import cl  # Assuming this is a custom module for chat context

client = AsyncOpenAI(
    api_key=os.getenv("DEEP_SEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)


start = time.time()

# Add the user's question to the messages
messages = [
    {"role": "system", "content": "You are a helpful assistant"},
    {"role": "user", "content": "write a love story about AI"},  # Explicitly include the user's prompt
]

async def generate_story():
    start = time.time()
    try:
        response = await client.chat.completions.create(  # Asynchronous call [[7]][[10]]
            model="deepseek",  # Replace with the specific DeepSeek model name if needed
            messages=messages,
            max_tokens=500  # Adjust parameters as required
        )
        end = time.time()
        print(f"Response time: {end - start:.2f} seconds")
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error: {e}")  # Handle errors like unauthorized access [[1]]
        return None

import asyncio

story = asyncio.run(generate_story())
print(story)