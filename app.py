import streamlit as st
from langchain_community.retrievers import WikipediaRetriever
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
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
def get_llm(api_key):
    """Initialize the LLM with API key from secrets"""
    api_key = st.secrets.get("GROQ_API_KEY", os.getenv("GROQ_API_KEY"))
    if not api_key:
        st.error("⚠️ GROQ_API_KEY not found. Please add it to your secrets.")
        st.stop()
    
    return ChatGroq(
        model_name="llama-3.3-70b-versatile",
        temperature=0.5,
        max_tokens=1200,
        max_retries=2,
        api_key=api_key
    )

def validate_industry(user_input, llm):
    """Validate if the input is a valid industry"""
    industry_check_prompt = f"""
You are an input validator.

TASK:
Determine whether the "{user_input}" refers to a BUSINESS INDUSTRY, SECTOR, or MARKET.

Respond with EXACTLY one word:
VALID or INVALID

Then give a one sentence reason if it is INVALID
"""
    classification_raw = llm.invoke(industry_check_prompt).content.strip()
    classification = classification_raw.split()[0].upper()
    
    if classification == "VALID":
        return True, ""
    else:
        reason = classification_raw.replace("INVALID", "").strip()
        return False, reason

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
    retriever = WikipediaRetriever(load_max_docs=17, lang="en")
    
    all_docs = []
    for q in queries:
        all_docs.extend(retriever.invoke(q))
    
    # Deduplicate
    unique_docs = {doc.metadata["title"]: doc for doc in all_docs}
    return list(unique_docs.values())

def filter_documents(raw_docs, user_input, llm):
    """Filter and select the most relevant documents"""
    retriever = WikipediaRetriever(load_max_docs=10, lang="en")
    if not raw_docs:
        return []
    
    titles_list = [doc.metadata["title"] for doc in raw_docs]
    
    bouncer_prompt = f"""
    You are a source quality filter for a business market research tool.

  INDUSTRY:
  "{user_input}"

  TASK:
  From the list below, select only 5 Wikipedia article titles that:
  - Are relevant and describe the "{user_input}" industry as a whole
  - Are useful for business or market analysis
  - NOT country-specific, company-specific, or historical-only

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
            docs = retriever.invoke(q)
            for doc in docs:
                title = doc.metadata["title"]
                # Add only if it's new and contains the industry keyword
                if title not in [d.metadata["title"] for d in final_docs]:
                    if user_input.lower() in title.lower():  # strict relevance
                        final_docs.append(doc)

    # Cap at 5 sources
    return final_docs[:5]

    if not final_docs:
        print("\n[!] DATA GAP DETECTED")
        print(f"I couldn't find specific business market data for '{user_input}' on Wikipedia.")
        print("Please provide more details (e.g., 'Automotive manufacturing' instead of just 'Cars') or try a different sector.")
        return # This stops the function immediately so no report is generated


def generate_report(final_docs, user_input, llm):
    """Generate the final industry report"""
    context_text = ""
    sources_info = []
    
    for i, doc in enumerate(final_docs, 1):
        title = doc.metadata.get('title')
        url = doc.metadata.get('source')
        sources_info.append({"#": i, "Title": title, "URL": url})
        
        context_text += (
            f"[SOURCE {i}]\n"
            f"TITLE: {title}\n"
            f"URL: {url}\n"
            f"CONTENT:\n{doc.page_content[:1500]}\n\n"
        )
    
    report_prompt = ChatPromptTemplate.from_template("""
    ROLE:
    You are a Market Research Assistant supporting business analysts at a large corporation.

    OBJECTIVE:
    Produce a concise, decision-oriented industry briefing that helps a corporate analyst
    understand the structure, economics, risks, and strategic outlook of the {user_input} industry.

    STRICT RULES:
    - Use ONLY information explicitly contained in the CONTEXT below.
    - Every factual statement MUST end with at least one clickable citation in this format: [SOURCE X](URL).
    - Do NOT include assumptions, estimates, or forward-looking claims unless directly supported by the sources.
    - Avoid generic business statements that could apply to most industries.
    - If a topic is not covered in the sources, explicitly state: "Not covered in sources."

    WRITING STYLE:
    - Professional, neutral, and analytical.
    - Focus on industry mechanisms, not definitions.
    - Prioritize insights that matter for corporate strategy and risk assessment.

    REPORT STRUCTURE:

    1. Industry Overview  
        Briefly describe what the industry does, its core economic function, and why it matters
        in the broader economy (2–3 sentences).

    2. Market Structure & Value Chain  
        Explain how value is created and captured in the industry.
        Identify key participants (e.g. producers, intermediaries, regulators, customers)
        and how they interact.

    3. Industry Scale & Geographic Footprint  
        Describe the industry’s global or regional scale, major operating regions,
        and any notable geographic concentration patterns.

    4. Competitive Landscape  
        Identify major players and explain how competition is structured
        (e.g. fragmentation, concentration, role of incumbents vs new entrants).

    5. Key Industry Drivers  
        List 3–4 concrete drivers that influence industry performance.
        Drivers should reflect structural, regulatory, technological, or demand-side forces
        specific to the {user_input} industry.

    6. Risks, Constraints & Regulatory Barriers  
        Describe the most significant risks and constraints facing the industry,
        including regulatory requirements, cost structures, operational risks,
        or external pressures.

    7. SWOT Analysis
        Provide an industry-specific SWOT summary:
        - Strengths: Structural or economic advantages unique to the industry
        - Weaknesses: Structural limitations or inefficiencies
        - Opportunities: Changes or trends that could materially improve industry performance
        - Threats: External or internal forces that could materially harm the industry  
        Each point must be grounded in the provided sources and avoid generic statements.

    8. Industry Outlook  
        Summarize how the industry is expected to evolve based on current trends
        described in the sources (2–3 sentences).

    LENGTH:
    Finish the report in less than 500 words.

    CONTEXT:
    {context}
    """)
    
    report = (report_prompt | llm).invoke({
        "context": context_text,
        "user_input": user_input
        })
    
    return report.content, sources_info

# Streamlit UI
st.title("AI Market Research Assistant")
st.markdown("Hi, I am here to help with your industry research, what would you like to know? Just tell me anything.")

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # API Key Input
    api_key = st.text_input(
        "Groq API Key",
        type="password",
        help="Get your free API key from https://console.groq.com"
    )
    
    if api_key:
        st.success("✅ API Key provided")
    else:
        st.warning("⚠️ Please enter your Groq API key to use the app")
    
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
    - Groq (Llama 3.3 70B)
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
        st.error("⚠️ Please enter your Groq API key in the sidebar first!")
        st.info("Get a free API key at https://console.groq.com")
        st.stop()
        
    if not user_input or len(user_input) < 3:
        st.error("Please enter a valid industry name (at least 3 characters)")
    else:
        try:
            llm = get_llm(api_key)
            
            # Progress tracking
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Step 1: Validate industry
            status_text.text("🔍 Validating industry...")
            progress_bar.progress(10)
            
            is_valid, reason = validate_industry(user_input, llm)
            
            if not is_valid:
                st.error(f"'{user_input}' does not appear to be a valid industry.")
                if reason:
                    st.warning(f"Reason: {reason}")
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
            
            report_content, sources_info = generate_report(final_docs, user_input, llm)
            
            progress_bar.progress(100)
            status_text.text("✅ Report generated successfully!")
            
            # Display results
            st.success("Report generated successfully!")
            
            # Sources section
            st.subheader("📚 Verified Sources")
            st.dataframe(sources_info, use_container_width=True, hide_index=True)
            
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
