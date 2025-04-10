# Use a base image (e.g., Python if your app is Python-based) [[4]][[5]]
FROM python:3.12.2-slim
# Set working directory
WORKDIR /langchain_agent
# Copy dependencies file (e.g., requirements.txt)
COPY requirements.txt .
# Install dependencies
RUN pip install -r requirements.txt
# Copy application code
COPY . .
# Expose the port your app uses [[8]]
EXPOSE 8019
# Command to run the app (ensure it binds to 0.0.0.0) [[1]][[4]]
CMD ["chainlit", "run", "excel_agent.py", "--host=0.0.0.0", "--port=8019"]