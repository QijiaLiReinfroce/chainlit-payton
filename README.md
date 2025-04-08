# Excel Agent using LangChain

This project implements an AI-powered Excel agent that can write and execute code to manipulate Excel files. The agent can query, reformat, change, and save Excel files through natural language instructions.

## Features

- **Load Excel Files**: Load any Excel file for analysis and manipulation
- **Data Analysis**: Query and analyze Excel data using pandas
- **Data Transformation**: Reformat and modify Excel data through code execution
- **Visualization**: Generate plots and charts from your Excel data
- **Data Export**: Save modified data back to Excel files

## Requirements

This project requires Python 3.8+ and the following packages:

```
langchain>=0.0.267
langchain-openai>=0.0.2
pandas>=2.0.3
openpyxl>=3.1.2
python-dotenv>=1.0.0
chainlit>=0.7.0
numpy>=1.24.0
matplotlib>=3.7.0
```

## Setup

1. Clone this repository or navigate to the project directory
2. Install the required packages:

```bash
pip install -r requirements.txt
```

3. Create a `.env` file with your OpenAI API key:

```
OPENAI_API_KEY=your_api_key_here
```

## Usage

To start the Excel agent:

```bash
chainlit run excel_agent.py
```

This will start a web interface where you can interact with the Excel agent.

### Example Interactions

Here are some examples of what you can ask the Excel agent to do:

1. **Load an Excel file**:
   ```
   Please load the Excel file at /path/to/your/file.xlsx
   ```

2. **Get information about the data**:
   ```
   What columns are in this Excel file? Show me the first few rows.
   ```

3. **Filter and query data**:
   ```
   Show me all rows where the Sales column is greater than 1000
   ```

4. **Transform data**:
   ```
   Add a new column that calculates the profit margin (profit divided by revenue)
   ```

5. **Create visualizations**:
   ```
   Create a bar chart showing sales by region
   ```

6. **Save the modified file**:
   ```
   Save the changes to a new file called updated_data.xlsx
   ```

## How It Works

The Excel agent uses LangChain's agent framework to:

1. Parse natural language requests
2. Generate Python code using pandas to fulfill those requests
3. Execute the code safely in a controlled environment
4. Return the results to the user

The agent has access to several tools:
- `list_excel_files`: List all loaded Excel files
- `load_excel_file`: Load an Excel file into memory
- `get_excel_info`: Get information about a loaded Excel file
- `execute_pandas_code`: Execute pandas code on a loaded Excel file
- `save_excel_file`: Save a loaded Excel file to disk
- `generate_plot`: Generate a plot from Excel data

## Customization

You can modify the `excel_agent.py` file to:

- Add new tools for specific Excel operations
- Change the system prompt to customize the agent's behavior
- Adjust the model parameters (e.g., temperature, model name)
- Add support for additional file formats

## License

This project is licensed under the MIT License - see the LICENSE file for details.
