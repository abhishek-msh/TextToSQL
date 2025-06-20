# TextToSQL

A multi-tenant BI Assistant that translates natural language questions into SQL queries and visualizations using Apache Pinot and other OLAP/SQL backends.

## Features

- Converts user questions into accurate, tenant-scoped SQL queries
- Supports Apache Pinot (MYSQL_ANSI dialect) and other databases
- Real-time streaming answers and visualizations via a Streamlit UI
- Modular architecture with adapters for OpenAI, Ollama, Milvus, and more
- Tracks analytics and retrieval logs for each conversation

## Project Structure

```
.
├── main.py                # FastAPI backend entrypoint
├── streamlit_app.py       # Streamlit frontend app
├── config.py              # Configuration classes for all services
├── requirements.txt       # Python dependencies
├── src/                   # Core source code
│   ├── bi_assistant.py
│   ├── prompts.py
│   ├── pinot_prompts.py
│   ├── extra_pinot_prompts.py
│   ├── types.py
│   ├── utils.py
│   ├── adapters/
│   └── ...
├── data/                  # Sample data and few-shot examples
```

## Setup

1. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```

2. **Configure environment variables:**
   - Copy `example.env` to `.env` and fill in required values.

3. **Run the backend API:**
   ```sh
   uvicorn main:app --reload
   ```

4. **Run the Streamlit frontend:**
   ```sh
   streamlit run streamlit_app.py
   ```

## Usage

- Open the Streamlit app in your browser.
- Enter your BI question in natural language.
- View generated SQL, results, and visualizations interactively.

## Customization

- Add new prompt templates in [`src/pinot_prompts.py`](src/pinot_prompts.py).
- Extend adapters for new LLMs or databases in [`src/adapters/`](src/adapters/).

## Authors

- Abhishek M Sharma
- AI/ML Software Developer Engineer