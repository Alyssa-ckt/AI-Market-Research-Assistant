# 📊 AI Market Research Assistant

Generate comprehensive industry reports powered by AI and Wikipedia data.

## Features

- 🔍 Intelligent industry validation
- 📝 Multi-query search strategy
- 🌐 Automatic Wikipedia data retrieval
- 🔎 Smart source filtering
- ✍️ AI-generated structured reports
- 📥 Downloadable reports

## Prerequisites

- Python 3.8+
- Groq API key (get one free at [console.groq.com](https://console.groq.com))

## Local Installation

1. Clone this repository:
```bash
git clone <your-repo-url>
cd market-research-assistant
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create `.streamlit/secrets.toml` and add your API key:
```toml
GROQ_API_KEY = "your-groq-api-key-here"
```

4. Run the app:
```bash
streamlit run app.py
```

## Deployment Options

### Option 1: Streamlit Community Cloud (Recommended)

1. Push your code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Click "New app"
4. Select your repository and `app.py`
5. In **Advanced settings → Secrets**, add:
   ```toml
   GROQ_API_KEY = "your-groq-api-key-here"
   ```
6. Click "Deploy"

### Option 2: Render

1. Create a new Web Service on [Render](https://render.com)
2. Connect your GitHub repository
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
5. Add environment variable:
   - Key: `GROQ_API_KEY`
   - Value: `your-groq-api-key-here`
6. Deploy

### Option 3: Hugging Face Spaces

1. Create a new Space at [huggingface.co/spaces](https://huggingface.co/spaces)
2. Select "Streamlit" as the SDK
3. Upload your files or connect to GitHub
4. In Settings → Repository secrets, add:
   - Name: `GROQ_API_KEY`
   - Value: `your-groq-api-key-here`
5. Your app will auto-deploy

### Option 4: Docker (Advanced)

Build and run with Docker:
```bash
docker build -t market-research-app .
docker run -p 8501:8501 -e GROQ_API_KEY="your-key" market-research-app
```

## Usage

1. Enter an industry name (e.g., "Healthcare", "Semiconductors", "E-commerce")
2. Click "Generate Report"
3. Wait for the AI to:
   - Validate your input
   - Search Wikipedia
   - Filter relevant sources
   - Generate a comprehensive report
4. Download your report as a text file

## Example Industries

- Healthcare
- Semiconductors
- Renewable Energy
- E-commerce
- Biotechnology
- Automotive Manufacturing
- Financial Services
- Artificial Intelligence

## Tech Stack

- **Frontend**: Streamlit
- **LLM**: Groq (Llama 3.3 70B)
- **Framework**: LangChain
- **Data Source**: Wikipedia API

## Troubleshooting

**"GROQ_API_KEY not found"**
- Make sure you've added your API key to `.streamlit/secrets.toml` (local) or your deployment platform's secrets/environment variables

**"No Wikipedia articles found"**
- Try being more specific with your industry name
- Use standard industry terminology
- Example: "Automotive Manufacturing" instead of "Cars"

**Rate limits**
- Groq offers generous free tier limits
- If you hit limits, wait a few minutes or upgrade your plan

## License

MIT License

## Contributing

Pull requests are welcome! For major changes, please open an issue first.
