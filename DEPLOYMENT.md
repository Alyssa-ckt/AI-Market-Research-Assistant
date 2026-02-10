# 🚀 Quick Deployment Guide

## Files Created

1. **app.py** - Main Streamlit application
2. **requirements.txt** - Python dependencies
3. **README.md** - Full documentation
4. **.gitignore** - Git ignore file
5. **Dockerfile** - Docker configuration
6. **render.yaml** - Render deployment config
7. **.streamlit/secrets.toml** - Local secrets (template)
8. **.streamlit/config.toml** - Streamlit config

## ⚡ Fastest Deployment (5 minutes)

### Streamlit Community Cloud

1. **Get Groq API Key** (Free)
   - Go to https://console.groq.com
   - Sign up and create an API key
   - Copy the key

2. **Push to GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin <your-github-repo-url>
   git push -u origin main
   ```

3. **Deploy on Streamlit**
   - Go to https://share.streamlit.io
   - Click "New app"
   - Select your GitHub repo
   - Main file path: `app.py`
   - Click "Advanced settings"
   - In **Secrets**, paste:
     ```toml
     GROQ_API_KEY = "your-actual-api-key-here"
     ```
   - Click "Deploy"

Done! Your app will be live in ~2 minutes.

## 🧪 Test Locally First

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Add your API key**
   Edit `.streamlit/secrets.toml`:
   ```toml
   GROQ_API_KEY = "your-groq-api-key-here"
   ```

3. **Run the app**
   ```bash
   streamlit run app.py
   ```

4. **Test it**
   - Open http://localhost:8501
   - Enter an industry like "Healthcare"
   - Click "Generate Report"

## 🔧 Alternative Deployments

### Render (Free Tier)
1. Create account at render.com
2. New → Web Service
3. Connect GitHub repo
4. It will auto-detect `render.yaml`
5. Add environment variable: `GROQ_API_KEY = your-key`
6. Deploy

### Hugging Face Spaces (Free)
1. Go to huggingface.co/spaces
2. Create new Space
3. Choose "Streamlit" SDK
4. Upload files or connect GitHub
5. Add secret: `GROQ_API_KEY`
6. Auto-deploys

## 📝 Important Notes

- **Never commit `.streamlit/secrets.toml`** to GitHub (it's in .gitignore)
- Groq free tier is generous but has rate limits
- First load may be slow as it downloads Wikipedia data
- For production, consider caching strategies

## 🐛 Common Issues

**"GROQ_API_KEY not found"**
→ Make sure you added it to secrets/environment variables

**"No Wikipedia articles found"**
→ Try more specific industry names (e.g., "Automotive Manufacturing" not "Cars")

**Slow generation**
→ Normal for first query, Wikipedia retrieval takes time

## 🎯 Next Steps

1. Test locally
2. Push to GitHub
3. Deploy to Streamlit Cloud
4. Share your link!

Need help? Check the full README.md for detailed instructions.
