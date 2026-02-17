import streamlit as st
from langchain_community.retrievers import WikipediaRetriever
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
import re
import os

# Page configuration
st.set_page_config(
    page_title="AI Market Research Assistant",
    page_icon="📊",
    layout="wide"
)

# Initialize LLM
@st.cache_resource
def get_llm(api_key, provider, model):
    """Initialize the LLM with API key and provider"""
    if provider == "Groq":
        return ChatGroq(
            model_name=model,
            temperature=0.2,
            max_tokens=1200,
            max_retries=2,
            api_key=api_key
        )
    else:  # OpenAI
        return ChatOpenAI(
            model=model,
            temperature=0.2,
            max_tokens=3000,
            max_retries=2,
            api_key=api_key
        )

def validate_industry(user_input, llm):
    """Validate if the input is a valid industry"""
    industry_check_prompt = f"""
    You are an input validator.
    TASK:
    Determine whether the "{user_input}" refers to a BUSINESS INDUSTRY, SECTOR, or MARKET.
    
    RULES:
    - Accept industry names even if informal or simplified
    - Only mark as INVALID if:
      1. It's a single generic product with no industry context
      2. It's not business-related at all (e.g., "my dog", "happiness", "purple")
    - Be permissive — if it could reasonably refer to an industry, mark it VALID
    
    RESPOND IN THIS EXACT FORMAT:
    
    If the input clearly refers to an industry (even informally):
    VALID
    
    If the input is too vague and needs clarification:
    INVALID - [one sentence explanation]
    SUGGESTIONS: [3-5 specific industry alternatives, comma-separated]
    """
    
    classification_raw = llm.invoke(industry_check_prompt).content.strip()
    classification = classification_raw.split()[0].upper()
    
    if classification == "VALID":
        return True, "", []
    else:
        # Parse response for reason and suggestions
        lines = classification_raw.split('\n')
        reason = ""
        suggestions = []
        
        for line in lines:
            if line.startswith("INVALID"):
                reason = line.replace("INVALID", "").replace("-", "").strip()
            elif line.startswith("SUGGESTIONS:"):
                suggestions_text = line.replace("SUGGESTIONS:", "").strip()
                suggestions = [s.strip() for s in suggestions_text.split(",")]
        
        return False, reason, suggestions

def generate_queries(user_input, llm):
    """Generate multiple search queries for the industry"""
    setup_prompt = f"""
   You are a research query planner for a market research assistant.

    INDUSTRY:
    "{user_input}"

    OBJECTIVE:
    Generate Wikipedia search queries that will retrieve pages useful for producing
    a business-focused industry research report.

    STRICT RULES:
    - Every query MUST explicitly refer to the "{user_input}" industry or a very close synonym.
    - Do NOT generate queries for adjacent or parent industries unless they explicitly include "{user_input}".
    - Prefer canonical Wikipedia article titles over descriptive phrases.
    - Avoid geography-only, company-only, or historical-only queries.
    - Do NOT include future predictions or forecasts unless Wikipedia commonly covers them.

    TASK:
    Generate exactly 5 Wikipedia search queries, each targeting a distinct business dimension:

    1. Industry definition and scope
    2. Market structure and value chain
    3. Competitive landscape and key players
    4. Economic significance or market size (if available)
    5. Industry trends, regulation, or structural change

    FORMAT (EXACT):
    QUERIES:
    - <query 1>
    - <query 2>
    - <query 3>
    - <query 4>
    - <query 5>
    """
    setup_data = llm.invoke(setup_prompt).content.strip()
    
    queries = [
        q.strip("- ").strip()
        for q in setup_data.splitlines()
        if q.strip().startswith("-")
    ]
    
    return queries

def retrieve_documents(queries):
    """Retrieve documents from Wikipedia"""
    retriever = WikipediaRetriever(load_max_docs=12, lang="en")
    
    all_docs = []
    for q in queries:
        all_docs.extend(retriever.invoke(q))
    
    # Deduplicate
    unique_docs = {doc.metadata["title"]: doc for doc in all_docs}
    return list(unique_docs.values())

def filter_documents(raw_docs, user_input, llm):
    """Filter and select the most relevant documents"""
    if not raw_docs:
        return []
        
    retriever = WikipediaRetriever(load_max_docs=20, lang="en")

    titles_list = [doc.metadata["title"] for doc in raw_docs]
    
    bouncer_prompt = f"""
    You are a source quality filter for a business market research tool.

  INDUSTRY:
  "{user_input}"

  TASK:
  From the list below, select only 5 Wikipedia article titles that:
  - Are relevant and describe the "{user_input}" industry as a whole
  - Are useful for business or market analysis

  RETURN FORMAT:
  - Return ONLY the exact titles, separated by commas.
  - Do NOT explain your reasoning.

  CANDIDATE TITLES:
  {titles_list}
  """
    
    verified_titles = [
        t.strip().lower()
        for t in llm.invoke(bouncer_prompt).content.split(",")
    ]
    
    final_docs = [
        doc for doc in raw_docs
        if any(v in doc.metadata["title"].lower() for v in verified_titles)
    ]
    
    # Deduplicate by title
    seen = set()
    deduped_docs = []
    
    for doc in final_docs:
        title = doc.metadata["title"]
        if title not in seen:
            seen.add(title)
            deduped_docs.append(doc)
    
    final_docs = deduped_docs
    
    if len(final_docs) < 5:
        print("[!] Expanding search scope...")
        broad_queries = [
            user_input,
        f"{user_input} sector",
        f"{user_input} services",
        f"{user_input} market"
        ]

        # Search each broad query and add results
        for q in broad_queries:
            try:
                docs = retriever.invoke(q)
            except Exception:
                continue  # Skip failed queries
            for doc in docs:
                title = doc.metadata["title"]
                if title not in [d.metadata["title"] for d in final_docs]:
                    if user_input.lower() in title.lower():
                        final_docs.append(doc)
                        
    final_docs = final_docs[:5]

    if not final_docs:
        return [] # This stops the function immediately so no report is generated

    return final_docs

def generate_report(final_docs, user_input, llm):
    """Generate the final industry report"""
    context_text = ""
    sources_info = []
    
    for i, doc in enumerate(final_docs, 1):
        title = doc.metadata.get('title')
        url = doc.metadata.get('source')
        # Extract financial figures per source
        per_source_prompt = f"""
        You are a financial data extractor.
        TASK:
        Scan the SOURCE CONTENT below and extract ALL explicit financial or market-scale figures.
        
        Include: market size, revenue, valuations, growth rates (CAGR), investment amounts, market spending.
        
        STRICT RULES:
        - Extract ONLY figures explicitly stated in the content below.
        - Do NOT calculate, estimate, or infer.
        - Every bullet MUST follow this exact format:
          • [figure] — [what it refers to, in plain English]
          Example: • US$1.3 billion — Sri Lanka tea industry export revenue in 2021
          Example: • 8.5% CAGR — projected annual growth rate of the global tea market
        - Do NOT return bare numbers without context.
        - If none found, return exactly: "None"
        
        SOURCE CONTENT:
        {doc.page_content[:1500]}
        """
        try:
            per_source_financials = llm.invoke(per_source_prompt).content.strip()
        except Exception:
            per_source_financials = "None"

        sources_info.append({
            "#": i,
            "Title": title,
            "URL": url,
            "Financial Figures": per_source_financials
        })

        context_text += (
            f"[SOURCE {i}]\n"
            f"TITLE: {title}\n"
            f"URL: {url}\n"
            f"CONTENT:\n{doc.page_content[:1500]}\n\n"
        )


    # Combined financial summary for the report prompt
    financial_text = "\n\n".join([
        f"SOURCE {s['#']} — {s['Title']}:\n{s['Financial Figures']}"
        for s in sources_info
    ])
    
    report_prompt = ChatPromptTemplate.from_template("""
    ROLE:
    You are a Market Research Assistant supporting business analysts at a large corporation.

    OBJECTIVE:
    Produce a concise, decision-oriented industry briefing that helps a corporate analyst
    understand the structure, economics, risks, and strategic outlook of the {industry}.

    STRICT RULES:
    - Use ONLY information explicitly contained in the CONTEXT below.
    - Every factual statement MUST end with at least one clickable citation in this format: [SOURCE X](URL).
    - Do NOT include assumptions, extrapolations, or forward-looking estimates unless directly supported by the sources.
    - Do NOT generalize about market size if exact figures are available.
    - Avoid generic business statements that could apply to most industries.
    - You SHOULD incorporate the financial figures listed in FINANCIAL FIGURES only if appropriate and accurately.

    WRITING STYLE:
    - Professional, neutral, and analytical.
    - Focus on industry mechanisms and economic structure.
    - Prioritise financial scale, capital intensity, and economic impact when available.

    FORMATTING RULES (CRITICAL):
    - Use ## for each section heading (e.g. ## 1. Industry Overview & Market Value)
    - Leave a blank line between the heading and the paragraph text
    - For bullet point lists, put each bullet on its own line with a blank line between bullets
    - For the SWOT section, use bold labels: **Strengths**, **Weaknesses**, **Opportunities**, **Threats**
    - Do NOT run section headings and content together on the same line

    REPORT STRUCTURE:

 1. Industry Overview & Market Value
      - Briefly describe what the industry does and its core economic function.
      If the sources contain any:
      - Market size figures
      - Revenue numbers
      - Spending levels
      - Growth rates
      - CAGR
      - Year-over-year changes

      You MUST explicitly report them with exact figures and citations.
      If no numerical figures are present in the sources, explicitly state:
      "No numerical market size data provided in sources."

    2. Market Structure & Value Chain
      - Explain how value is created and captured.
      - Identify key participants and economic roles.

    3. Industry Scale & Geographic Footprint
      - Describe major producing regions, revenue concentration, or geographic dominance.
      - Include regional financial figures if present.

    4. Competitive Landscape
      - Identify major players.
      - Describe concentration levels and economic power structure.

    5. Key Industry Drivers
      - List 3–4 concrete drivers that influence industry performance.
      - Drivers should reflect structural, regulatory, technological, or demand-side forces 
        specific to the {industry}.

    6. Risks, Constraints & Regulatory Barriers
      - Identify capital requirements, cost structure, supply constraints, regulatory barriers, or systemic risks.

    7. SWOT Analysis
      Provide an industry-specific SWOT summary:
      - Strengths: Structural or economic advantages unique to the industry
      - Weaknesses: Structural limitations or inefficiencies
      - Opportunities: Changes or trends that could materially improve industry performance
      - Threats: External or internal forces that could materially harm the industry
      Each point must be grounded in the provided sources and avoid generic statements.

    8. Industry Outlook
      - Summarize how the industry is expected to evolve based on current trends
        described in the sources (2–3 sentences).

    LENGTH:
    Maximum 500 words.

    CONTEXT:
    {context}

    FINANCIAL FIGURES:
    {financials}
    """)
    
    report = (report_prompt | llm).invoke({
        "context": context_text,
        "industry": user_input,
        "financials": financial_text
        })
    
    return report.content, sources_info, financial_text

# Streamlit UI
# Logo + Title
import os
if os.path.exists("ai logo.png"):
    st.image("ai logo.png", width=100)
st.title("📊 AI Market Research Assistant")
st.markdown("Hi, I am here to help with your industry research. Just enter an industry below to get started!")

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Provider Selection
    provider = st.selectbox(
        "AI Provider",
        ["Groq", "OpenAI"],
        help="Choose your AI provider"
    )
    
    # Model Selection based on provider
    if provider == "Groq":
        model = st.selectbox(
            "Model",
            ["llama-3.3-70b-versatile"],
            help="Select Groq model"
        )
        api_url = "https://console.groq.com"
    else:  # OpenAI
        model = st.selectbox(
            "Model",
            ["gpt-4o"],
            help="Select OpenAI model"
        )
        api_url = "https://platform.openai.com/api-keys"
    
    # API Key Input
    api_key = st.text_input(
        f"{provider} API Key",
        type="password",
        help=f"Get your API key from {api_url}"
    )
    
    if api_key:
        st.success("✅ API Key provided")
    else:
        st.warning(f"⚠️ Please enter your {provider} API key")
    
    st.markdown("---")
    
    st.header("About")
    st.markdown("""
    This tool generates market research reports by:
    1. Validating your industry input
    2. Searching Wikipedia for relevant data
    3. Filtering and analyzing sources
    4. Generating a structured report
    
    **Powered by:**
    - LangChain
    - Groq/OpenAI
    - Wikipedia API
    """)
    
    st.header("Examples")
    st.markdown("""
    - Healthcare
    - Semiconductors
    - Renewable Energy
    - E-commerce
    - Biotechnology
    """)

# Main input
user_input = st.text_input(
    "Enter an industry:",
    placeholder="e.g., Healthcare, Tourism, Automotive"
)

if st.button("Generate Report", type="primary"):
    if not api_key:
        st.error(f"⚠️ Please enter your {provider} API key in the sidebar first!")
        st.info(f"Get your API key at {api_url}")
        st.stop()
        
    if not user_input or len(user_input) < 3:
        st.error("Please enter a valid industry name (at least 3 characters)")
    else:
        try:
            llm = get_llm(api_key, provider, model)
            
            # Progress tracking
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Step 1: Validate industry
            status_text.text("🔍 Validating industry...")
            progress_bar.progress(10)
            
            is_valid, reason, suggestions = validate_industry(user_input, llm)

            if not is_valid:
                st.error(f"'{user_input}' does not appear to be a valid industry.")
                if reason:
                    st.warning(f"Reason: {reason}")
                if suggestions:
                    st.info("💡 **Did you mean one of these?**")
                    for s in suggestions:
                        st.write(f"• {s}")
                st.stop()
            
            # Step 2: Generate queries
            status_text.text("📝 Generating search queries...")
            progress_bar.progress(25)
            
            queries = generate_queries(user_input, llm)
            
            with st.expander("View Generated Queries"):
                for i, q in enumerate(queries, 1):
                    st.write(f"{i}. {q}")
            
            # Step 3: Retrieve documents
            status_text.text("🌐 Retrieving Wikipedia data...")
            progress_bar.progress(50)
            
            raw_docs = retrieve_documents(queries)
            
            if not raw_docs:
                st.warning("No Wikipedia articles found. Try a different industry name.")
                st.stop()

            with st.expander(f"📄 Raw Articles Retrieved ({len(raw_docs)} total)"):
                for i, doc in enumerate(raw_docs, 1):
                    st.write(f"{i}. {doc.metadata['title']}")

            # Step 4: Filter documents
            status_text.text("🔎 Filtering relevant sources...")
            progress_bar.progress(70)
            
            final_docs = filter_documents(raw_docs, user_input, llm)
            
            if not final_docs:
                st.warning(f"""
                **DATA GAP DETECTED**
                
                I couldn't find specific business market data for '{user_input}' on Wikipedia.
                
                Please try:
                - Being more specific (e.g., 'Automotive manufacturing' instead of 'Cars')
                - Using industry standard terminology
                - A different but related sector
                """)
                st.stop()
            
            # Step 5: Generate report
            status_text.text("✍️ Generating report...")
            progress_bar.progress(90)
            
            report_content, sources_info, financial_text = generate_report(final_docs, user_input, llm)
            
            progress_bar.progress(100)
            status_text.text("✅ Report generated successfully!")
            
            # Display results
            st.success("Report generated successfully!")
            
            # Sources + Financial figures combined
            st.subheader("📚 Verified Sources & Financial Figures")
            for s in sources_info:
                with st.expander(f"SOURCE {s['#']}: {s['Title']}"):
                    st.markdown(f"🔗 [{s['URL']}]({s['URL']})")
                    st.markdown("**💰 Financial Figures:**")
                    if s['Financial Figures'] == "None":
                        st.caption("No explicit financial figures found in this source.")
                    else:
                        formatted = s['Financial Figures'].replace('• ', '\n\n• ')
                        st.markdown(formatted)
            
            # Report section
            st.subheader(f"📊 Industry Report: {user_input.upper()}")
            st.markdown("---")
            st.markdown(report_content)
            
            # Download button
            st.download_button(
                label="📥 Download Report",
                data=f"INDUSTRY REPORT: {user_input.upper()}\n\n{report_content}",
                file_name=f"{user_input.lower().replace(' ', '_')}_report.txt",
                mime="text/plain"
            )
            
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            st.exception(e)

# Footer
st.markdown("---")
st.markdown(
    "<p style='text-align: center; color: gray;'>Built with Streamlit and LangChain</p>",
    unsafe_allow_html=True
)
