"""
Excel Agent using LangChain and Chainlit

A simple, clean agent that can manipulate Excel files through a chat interface.
It can load, query, modify, and save Excel files using openpyxl.
"""
import os
from dotenv import load_dotenv
import chainlit as cl
from typing import Optional
from langchain.agents import AgentType, initialize_agent, Tool
from langchain.memory import ConversationBufferMemory
from langchain_community.chat_models import ChatOpenAI
from openai import AsyncOpenAI
from document_utils import read_document_bytes

# Import the tools from the excel_agent_tools module
from excel_agent_tools import (
    ListExcelFilesTool, LoadExcelFileTool, GetExcelInfoTool,
    ExcelPythonREPLTool,
    DownloadExcelFileTool, UnmergeExcelCellsTool,
    clear_excel_files, load_excel_files_metadata, get_excel_files, get_current_file_id, set_current_file_id
)

# Load environment variables
load_dotenv()

# Create a directory for Excel files if it doesn't exist
EXCEL_FILES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "excel_files")
os.makedirs(EXCEL_FILES_DIR, exist_ok=True)

# Path to the metadata file
METADATA_FILE = os.path.join(EXCEL_FILES_DIR, "excel_files_metadata.json")

from users import verify_user

@cl.password_auth_callback
def auth_callback(username: str, password: str) -> Optional[cl.User]:
    """Authenticate a user with username and password."""
    print(f"Auth callback called with username: {username}")
    
    # Authenticate the user using the verify_user function
    user_data = verify_user(username, password)
    
    if user_data:
        # Create a Chainlit User object from the user data
        user = cl.User(
            identifier=user_data["username"],
            metadata={
                "role": user_data["role"],
                "provider": "credentials"
            }
        )
        print(f"Authentication successful for user: {username}")
        return user
    else:
        print("Authentication failed")
        return None

@cl.on_chat_resume
async def on_chat_resume(thread):
    """Handle resuming a previous chat session.
    
    This function is called when a user returns to a previous conversation.
    The thread parameter contains all the information about the previous conversation.
    """
    # Get the authenticated user from the session
    user = cl.user_session.get("user")
    
    # Simple debug information
    print(f"Resuming chat for user: {user.identifier if user else 'Unknown'}")
    
    try:
        # Initialize an empty list to store the reconstructed chat history
        all_messages = []
        
        # Get the messages from the thread
        if "steps" in thread:
            # First, get all user messages (which are root messages)
            user_messages = [m for m in thread["steps"] if m.get("parentId") is None and m.get("type") == "user_message"]
            for message in user_messages:
                all_messages.append({"role": "user", "content": message["output"]})
            
            # Then, find all on_message runs (which are parents of thinking and assistant messages)
            on_message_runs = [m for m in thread["steps"] if m.get("type") == "run" and m.get("name") == "on_message"]
            
            # For each on_message run, find its children (thinking and assistant messages)
            for run in on_message_runs:
                # Find all children of this run
                children = [m for m in thread["steps"] if m.get("parentId") == run["id"]]
                
                # Extract thinking steps
                thinking_steps = [m for m in children if m.get("type") == "undefined" and "thought" in m.get("name", "").lower()]
                
                # Extract assistant messages
                assistant_messages = [m for m in children if m.get("type") == "assistant_message"]
                for assistant in assistant_messages:
                    # Skip welcome back messages
                    if "welcome back" in assistant.get("output", "").lower():
                        print(f"Skipped welcome back message")
                        continue
                    
                    content = assistant.get("output", "")
                    all_messages.append({"role": "assistant", "content": content})
        
        elif "messages" in thread:
            messages_data = thread["messages"]
            
            for msg in messages_data:
                if isinstance(msg, dict):
                    if msg.get("type") == "user_message" or msg.get("role") == "user":
                        content = msg.get("output", msg.get("content", ""))
                        # Print full text retrieved from database
                        all_messages.append({"role": "user", "content": content})
                    elif msg.get("type") in ["assistant_message", "ai_message"] or msg.get("role") == "assistant":
                        # Skip welcome back messages from previous chat resumptions
                        if "welcome back" in msg.get("output", msg.get("content", "")).lower():
                            continue
                            
                        # Skip thinking steps
                        if "thinking" in msg.get("name", "").lower() or msg.get("type") == "thinking":
                            continue
                            
                        content = msg.get("output", msg.get("content", ""))
                        
                        
                        # Print full text prepared to send to user
                        all_messages.append({"role": "assistant", "content": content})
        
        # Set the chat history in the session
        if all_messages:
            """
            print(f"\n--- RESTORED MESSAGES SUMMARY ---")
            for i, msg in enumerate(all_messages):
                print(f"Message {i+1}: {msg['role']}")
                print(f"Content: {msg['content']}")
                print("-" * 50)
            print(f"Total restored messages: {len(all_messages)}")
            """
            cl.user_session.set("chat_history", all_messages)
        else:
            #print("No messages found in thread")
            cl.user_session.set("chat_history", [])
        
        # Always ensure Excel agent mode is deactivated when resuming a chat
        cl.user_session.set("excel_agent_active", False)
        # Clear any existing agent from the session
        cl.user_session.set("agent", None)
        
        # Initialize chat client for regular chat mode
        cl.user_session.set("chat_client", AsyncOpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com"
        ))
        


        # Initialize a new agent object (but not activate it yet)
        # Setup the LLM with DeepSeek API
        llm = ChatOpenAI(
            temperature=0,
            model="deepseek-reasoner",
            streaming=True,
            openai_api_key=os.getenv("DEEPSEEK_API_KEY"),
            openai_api_base="https://api.deepseek.com"
        )
        
        # Create the tools
        tools = [
            ListExcelFilesTool(),
            LoadExcelFileTool(),
            GetExcelInfoTool(),
            ExcelPythonREPLTool(),
            DownloadExcelFileTool(),
            UnmergeExcelCellsTool()
        ]
        
        # Setup memory for conversation history
        memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        # Initialize the agent
        agent = initialize_agent(
            tools=tools,
            llm=llm,
            agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION,
            memory=memory,
            verbose=True,
            agent_kwargs={
                "system_message": """You are an Excel agent that helps users manipulate Excel files.

IMPORTANT: When writing openpyxl code, NEVER load workbooks from disk using load_workbook(). 
Instead, always use the 'wb' variable that is already provided to you in the execution environment.
This 'wb' variable contains the current workbook that the user is working with.

For example:
- DON'T write: wb = load_workbook('filename.xlsx')
- DO write: # Use the existing wb object
            sheet = wb.active
            
This ensures that you're working with the most up-to-date version of the workbook and prevents errors.

CRITICAL: PROPER CODE INDENTATION IS REQUIRED
The most common errors when executing code are related to improper indentation. Python requires consistent indentation for code blocks.

INDENTATION RULES:
1. ALWAYS indent code blocks with 4 spaces after statements ending with a colon (:)
2. NEVER skip indentation after 'if', 'for', 'while', 'def', etc.
3. ALWAYS maintain the same indentation level for code in the same block
4. ALWAYS add a new indentation level (4 more spaces) for nested blocks

Example of CORRECT indentation:
```python
# Notice how each nested level adds 4 more spaces of indentation
for sheet in wb:                           # Level 0 (0 spaces)
    for row in sheet.iter_rows():          # Level 1 (4 spaces)
        for cell in row:                   # Level 2 (8 spaces)
            if cell.value is None:         # Level 3 (12 spaces)
                cell.value = 'none'        # Level 4 (16 spaces)
```

Example of INCORRECT indentation that will cause errors:
```python
for sheet in wb:
for row in sheet.iter_rows():        # ERROR: Missing indentation after 'for'
    for cell in row:
        if cell.value is None:
        cell.value = 'none'          # ERROR: Missing indentation after 'if'
```

Remember to use the execute_openpyxl_code tool for any Excel operations."""
            }
        )
        
        # Store the agent in the user session
        cl.user_session.set("agent", agent)
        
        # Send a welcome back message
        #await cl.Message(content=f"Welcome back! You're in regular chat mode. Type 'run excel agent' to activate Excel agent mode.").send()
    
    except Exception as e:
        print(f"Error processing thread: {e}")
        # Set empty chat history
        cl.user_session.set("chat_history", [])
        cl.user_session.set("excel_agent_active", False)
    
    # Notify the user that they've resumed a previous conversation
    mode_status = "Excel agent mode" if cl.user_session.get("excel_agent_active", False) else "regular chat mode"
    # Removed the "Welcome back" message

@cl.on_chat_start
async def on_chat_start():
    """Initialize the agent when a new chat starts."""
    # Clear all Excel files from previous sessions
    clear_excel_files(EXCEL_FILES_DIR, METADATA_FILE)
    
    # Initialize the Excel files dictionary in the user session
    cl.user_session.set("excel_files", {})
    cl.user_session.set("current_file_id", None)
    
    # Load existing Excel files (should be empty now)
    load_excel_files_metadata(EXCEL_FILES_DIR, METADATA_FILE)
    
    # Setup the LLM with DeepSeek API
    llm = ChatOpenAI(
        temperature=0,
        model="deepseek-reasoner",
        streaming=True,
        openai_api_key=os.getenv("DEEPSEEK_API_KEY"),
        openai_api_base="https://api.deepseek.com"
    )
    
    # Create the tools
    tools = [
        ListExcelFilesTool(),
        LoadExcelFileTool(),
        GetExcelInfoTool(),
        ExcelPythonREPLTool(),
        DownloadExcelFileTool(),
        UnmergeExcelCellsTool()
    ]
    
    # Setup memory for conversation history
    memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True
    )
    
    # Initialize the agent
    agent = initialize_agent(
        tools=tools,
        llm=llm,
        agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION,
        memory=memory,
        verbose=True,
        agent_kwargs={
            "system_message": """You are an Excel agent that helps users manipulate Excel files.

IMPORTANT: When writing openpyxl code, NEVER load workbooks from disk using load_workbook(). 
Instead, always use the 'wb' variable that is already provided to you in the execution environment.
This 'wb' variable contains the current workbook that the user is working with.

For example:
- DON'T write: wb = load_workbook('filename.xlsx')
- DO write: # Use the existing wb object
            sheet = wb.active
            
This ensures that you're working with the most up-to-date version of the workbook and prevents errors.

CRITICAL: PROPER CODE INDENTATION IS REQUIRED
The most common errors when executing code are related to improper indentation. Python requires consistent indentation for code blocks.

INDENTATION RULES:
1. ALWAYS indent code blocks with 4 spaces after statements ending with a colon (:)
2. NEVER skip indentation after 'if', 'for', 'while', 'def', etc.
3. ALWAYS maintain the same indentation level for code in the same block
4. ALWAYS add a new indentation level (4 more spaces) for nested blocks

Example of CORRECT indentation:
```python
# Notice how each nested level adds 4 more spaces of indentation
for sheet in wb:                           # Level 0 (0 spaces)
    for row in sheet.iter_rows():          # Level 1 (4 spaces)
        for cell in row:                   # Level 2 (8 spaces)
            if cell.value is None:         # Level 3 (12 spaces)
                cell.value = 'none'        # Level 4 (16 spaces)
```

Example of INCORRECT indentation that will cause errors:
```python
for sheet in wb:
for row in sheet.iter_rows():        # ERROR: Missing indentation after 'for'
    for cell in row:
        if cell.value is None:
        cell.value = 'none'          # ERROR: Missing indentation after 'if'
```

Remember to use the execute_openpyxl_code tool for any Excel operations."""
        }
    )
    
    # Store the agent in the user session
    cl.user_session.set("agent", agent)
    
    # Initialize chat history for regular conversation mode
    cl.user_session.set("chat_history", [])
    
    # Set the default mode to regular chat (not Excel agent)
    cl.user_session.set("excel_agent_active", False)
    
    
    # Initialize the OpenAI client for regular chat mode
    from openai import AsyncOpenAI
    
    # Initialize the OpenAI client
    chat_client = AsyncOpenAI(
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url="https://api.deepseek.com"
    )
    
    # Store the chat client in the session
    cl.user_session.set("chat_client", chat_client)


@cl.on_message
async def on_message(message: cl.Message):
    """Process incoming messages."""
    # Get the agent from the user session
    agent = cl.user_session.get("agent")
    
    # Check if this is a command to activate the Excel agent
    if "run excel agent" in message.content.lower():
        cl.user_session.set("excel_agent_active", True)
        await cl.Message(content="🔄 Excel agent mode activated! I can now help you manipulate Excel files using openpyxl.\n\nYou can:\n- Upload an Excel file\n- Ask me to analyze your data\n- Execute openpyxl code to modify your Excel files\n- Save and download your modified files\n\nType 'exit excel agent' to return to regular chat mode.").send()
        return
    
    # Check if this is a command to deactivate the Excel agent
    if "exit excel agent" in message.content.lower():
        cl.user_session.set("excel_agent_active", False)
        await cl.Message(content="✅ Returned to regular chat mode. Type 'run excel agent' anytime to reactivate the Excel agent.").send()
        return

    # Check if we're in Excel agent mode
    if cl.user_session.get("excel_agent_active", False):

        # Check if files were uploaded with the message
        if message.elements:
            for element in message.elements:
                if isinstance(element, cl.File) and element.name.endswith(('.xlsx', '.xls')):
                    try:
                        # Save the file to the Excel files directory
                        file_path = os.path.join(EXCEL_FILES_DIR, element.name)
                        
                        # If file already exists, add a number to the filename
                        if os.path.exists(file_path):
                            base_name, ext = os.path.splitext(element.name)
                            counter = 1
                            while os.path.exists(file_path):
                                file_path = os.path.join(EXCEL_FILES_DIR, f"{base_name}_{counter}{ext}")
                                counter += 1
                        
                        # Save the file content - improved handling for different Chainlit versions
                        file_saved = False
                        
                        # Method 1: Try using get_bytes() if available
                        if hasattr(element, "get_bytes") and callable(getattr(element, "get_bytes")):
                            try:
                                file_bytes = element.get_bytes()
                                if file_bytes:
                                    with open(file_path, "wb") as f:
                                        f.write(file_bytes)
                                    file_saved = True
                            except Exception as e:
                                print(f"Error using get_bytes(): {str(e)}")
                        
                        # Method 2: Try using path attribute
                        if not file_saved and hasattr(element, "path") and element.path:
                            try:
                                import shutil
                                shutil.copy(element.path, file_path)
                                file_saved = True
                            except Exception as e:
                                print(f"Error copying from path: {str(e)}")
                        
                        # Method 3: Try using content attribute
                        if not file_saved and hasattr(element, "content") and element.content is not None:
                            try:
                                with open(file_path, "wb") as f:
                                    f.write(element.content)
                                file_saved = True
                            except Exception as e:
                                print(f"Error writing content: {str(e)}")
                        
                        # Check if file was saved successfully
                        if not file_saved:
                            raise ValueError("Could not save file: no valid file content found")
                        
                        # Load the Excel file using the LoadExcelFileTool
                        load_tool = LoadExcelFileTool()
                        result = load_tool._run(file_path)
                        
                        # Send a message with the result
                        await cl.Message(content=f"File uploaded and loaded: {element.name}\n\n{result}").send()
                        
                        # If Excel agent is active, let the agent analyze the file
                        if cl.user_session.get("excel_agent_active", False):
                            # Let the agent know about the file upload
                            await agent.arun(
                                input=f"I've just uploaded an Excel file named {element.name} and it has been loaded. Please only list the sheet names in the file, nothing else.",
                                callbacks=[cl.LangchainCallbackHandler()]
                            )
                        else:
                            # In regular chat mode, just inform the user
                            await cl.Message(content="The Excel file has been loaded. Type 'run excel agent' to analyze and manipulate this file.").send()
                        return
                    except Exception as e:
                        await cl.Message(content=f"Error processing the Excel file: {str(e)}").send()
                        return

        # Use the Excel agent to process the message
        msg = cl.Message(content="")
        await msg.send()
        
        # Process the message with the agent
        response = await agent.arun(
            input=message.content,
            callbacks=[cl.LangchainCallbackHandler()]
        )
        
        # Ensure the response is properly stored in the conversation memory
        # This is handled internally by the agent's memory system, but we'll make sure
        # it's properly updated in the session as well
        if hasattr(agent, 'memory') and agent.memory is not None:
            # Get the updated chat history from the agent's memory
            updated_history = agent.memory.chat_memory.messages
            # Convert to the format we use in the session
            formatted_history = []
            for msg in updated_history:
                if hasattr(msg, 'type') and msg.type == 'human':
                    formatted_history.append({"role": "user", "content": msg.content})
                elif hasattr(msg, 'type') and msg.type == 'ai':
                    formatted_history.append({"role": "assistant", "content": msg.content})
            # Store the updated history in the session
            cl.user_session.set("chat_history", formatted_history)
        
        # Check if we need to trigger a file download after the agent has finished
        if cl.user_session.get("trigger_download"):
            # Get the download information
            download_info = cl.user_session.get("immediate_download")
            if download_info and isinstance(download_info, dict):
                try:
                    file_name = download_info.get("file_name")
                    file_bytes = download_info.get("file_bytes")
                    mime_type = download_info.get("mime_type")
                    
                    if file_name and file_bytes:
                        # Create a file element and send it as a download
                        file = cl.File(
                            name=file_name,
                            content=file_bytes,
                            mime=mime_type
                        )
                        
                        await cl.Message(
                            content=f"Here is your Excel file: {file_name}",
                            elements=[file]
                        ).send()
                except Exception as e:
                    await cl.Message(content=f"Error sending file download: {str(e)}").send()
            
            # Reset the trigger
            cl.user_session.set("trigger_download", False)
            cl.user_session.set("immediate_download", None)
        
        # Update the message with the response
        msg.content = response
        await msg.send()
    else:
        # In regular chat mode, use a more sophisticated approach based on deepseek_api.py
        
        # Check if files were uploaded with the message
        if message.elements:
            for element in message.elements:
                try:
                    # Import document utilities
                    from document_utils import read_document_bytes
                    
                    # Get file bytes
                    file_bytes = None
                    if hasattr(element, "get_bytes") and callable(getattr(element, "get_bytes")):
                        file_bytes = element.get_bytes()
                    elif hasattr(element, "content") and element.content is not None:
                        file_bytes = element.content
                    elif hasattr(element, "path") and element.path:
                        with open(element.path, "rb") as f:
                            file_bytes = f.read()
                    
                    if file_bytes:
                        # Process the file using document_utils
                        file_content = read_document_bytes(file_bytes, element.name)
                        
                        # Send a simple message instead of the extracted content
                        await cl.Message(content=f"文件已尽加载完毕了").send()
                        
                        # Add the file content to the chat history
                        chat_history = cl.user_session.get("chat_history", [])
                        chat_history.append({"role": "user", "content": f"I've uploaded a file named {element.name}"})
                        chat_history.append({"role": "assistant", "content": f"文件已尽加载完毕了\n" + file_content})
                        #chat_history.append({})
                        cl.user_session.set("chat_history", chat_history)
                        return
                    else:
                        await cl.Message(content=f"Could not read the file: {element.name}").send()
                        return
                except Exception as e:
                    await cl.Message(content=f"Error processing the file: {str(e)}").send()
                    return
        
        
        # Get the chat history from the user session
        chat_history = cl.user_session.get("chat_history", [])
        
        # Ensure the last message in the history is not from the user
        if chat_history and chat_history[-1]["role"] == "user":
            # Remove the last user message to avoid consecutive user messages
            chat_history = chat_history[:-1]
        
        # Add the current user message to chat history
        chat_history.append({"role": "user", "content": message.content})
        cl.user_session.set("chat_history", chat_history)
        
        try:
            # Get the chat client from the session
            client = cl.user_session.get("chat_client")
            
            # Create messages array with system prompt and conversation history
            messages = [
                {"role": "system", "content": "You are a helpful assistant that can chat about various topics.."}
            ]
            
            # Add chat history to messages, ensuring alternating user/assistant pattern
            current_role = None
            formatted_history = []
            
            for msg in chat_history:
                if msg["role"] != current_role:
                    formatted_history.append(msg)
                    current_role = msg["role"]
            
            messages.extend(formatted_history)
            
            # Stream the response from the API
            stream = await client.chat.completions.create(
                model="deepseek-reasoner",
                messages=messages,
                temperature=0.7,
                stream=True
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

            import time as time_module
            start = time_module.time()

            print("thinking start =====================")

            # Streaming the thinking
            async with cl.Step(name="Thinking") as thinking_step:
                async for chunk in stream:
                    
                    # Print the chunk object to understand its structure
                    print("\n=== CHUNK OBJECT (THINKING) ===")
                    print(f"Chunk type: {type(chunk)}")
                    print(f"Chunk dir: {dir(chunk)}")
                    print(f"Chunk repr: {repr(chunk)}")
                    print(f"Chunk choices: {chunk.choices}")
                    print(f"Chunk delta type: {type(chunk.choices[0].delta)}")
                    print(f"Chunk delta dir: {dir(chunk.choices[0].delta)}")
                    print(f"Chunk delta repr: {repr(chunk.choices[0].delta)}")
                    print("=== END CHUNK OBJECT ===\n")
                    
                    
                    delta = chunk.choices[0].delta
                    reasoning_content = getattr(delta, "reasoning_content", None)
                    
                    print(reasoning_content, end="", flush=True)
                    if reasoning_content is not None and not thinking_completed:
                        collected_reasoning += reasoning_content
                        await thinking_step.stream_token(reasoning_content)
                    elif not thinking_completed:
                        # Exit the thinking step
                        thought_for = round(time_module.time() - start)
                        thinking_step.name = f"Thought for {thought_for}s"
                        await thinking_step.update()
                        thinking_completed = True
                        break
            
            print("\nthinking end =====================")

            # Create an empty message for the final answer
            final_answer = cl.Message(content="")

            # Streaming the final answer
            async for chunk in stream:
                # Print the chunk object to understand its structure
                #print("\n=== CHUNK OBJECT (FINAL ANSWER) ===")
                #print(f"Chunk type: {type(chunk)}")
                #print(f"Chunk repr: {repr(chunk)}")
                #print(f"Chunk delta type: {type(chunk.choices[0].delta)}")
                #print(f"Chunk delta repr: {repr(chunk.choices[0].delta)}")
                #print("=== END CHUNK OBJECT ===\n")
                
                delta = chunk.choices[0].delta
                content = getattr(delta, "content", None)
                print(content, end="", flush=True)
                if content is not None:  # Handle empty strings
                    collected_content += content
                    await final_answer.stream_token(content)

            print("\nfinal answer end =====================")

            # Send the final message after all streaming is complete
            await final_answer.send()

            # Add the assistant's response to chat history
            chat_history.append({"role": "assistant", "content": collected_content})

            # Keep only the last 20 messages to avoid context length issues
            if len(chat_history) > 20:
                chat_history = chat_history[-20:]

            # Save updated chat history
            cl.user_session.set("chat_history", chat_history)

        except Exception as e:
            error_message = f"Error: {str(e)}"
            print(f"API Error: {error_message}")
            
            # If there's an error with the OpenAI API, fall back to simple responses
            fallback_responses = {
                "help": "I'm your Excel Assistant! I can help you with Excel files when you activate the Excel agent mode.\n\nTo get started, type 'run excel agent'.",
                "default": "I'm your Excel Assistant, but I'm currently in regular chat mode. To use my Excel capabilities, please type 'run excel agent'."
            }
            
            user_input = message.content.lower()
            if "excel" in user_input:
                response_text = fallback_responses["excel"]
            elif "help" in user_input:
                response_text = fallback_responses["help"]
            else:
                response_text = fallback_responses["default"]
            
            # Update the message with the fallback response
            await cl.Message(content=response_text).send()
    

if __name__ == "__main__":
    # Run the Chainlit app
    cl.run()