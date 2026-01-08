"""
ClearClause - Privacy-First Document Analyzer
A Streamlit application for secure PDF analysis with PII redaction
"""
import streamlit as st
import PyPDF2
import os
import json
from io import BytesIO
from dotenv import load_dotenv
import google.generativeai as genai
from privacy_guard import redact_pii, get_redaction_summary

# Load environment variables from .env file
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="ClearClause",
    page_icon="�",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern styling
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .header-title {
        text-align: center;
        font-size: 3rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 1rem;
    }
    .subtitle {
        text-align: center;
        font-size: 1.1rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .info-box {
        background-color: #f0f2f6;
        border-left: 4px solid #667eea;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .success-box {
        background-color: #d4edda;
        border-left: 4px solid #28a745;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .risk-high {
        color: #d32f2f;
        font-weight: 600;
    }
    .risk-medium {
        color: #f57c00;
        font-weight: 600;
    }
    .risk-low {
        color: #388e3c;
        font-weight: 600;
    }
    .risk-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        border-radius: 0.75rem;
        padding: 1.5rem;
        margin: 1rem 0;
        border-left: 5px solid #667eea;
    }
    .risk-card-financial {
        border-left-color: #f57c00;
    }
    .risk-card-privacy {
        border-left-color: #d32f2f;
    }
    .risk-card-legal {
        border-left-color: #1976d2;
    }
    .metric-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 0.75rem;
        padding: 1.5rem;
        color: white;
        text-align: center;
        margin: 1rem 0;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if "extracted_text" not in st.session_state:
    st.session_state.extracted_text = None
if "redacted_text" not in st.session_state:
    st.session_state.redacted_text = None
if "analysis_json" not in st.session_state:
    st.session_state.analysis_json = None
if "redaction_summary" not in st.session_state:
    st.session_state.redaction_summary = None


def extract_text_from_pdf(uploaded_file):
    """
    Extracts text from PDF file without saving to disk.
    Reads directly from uploaded file buffer.
    
    Args:
        uploaded_file: Streamlit UploadedFile object
        
    Returns:
        str: Extracted text from PDF
    """
    try:
        # Read PDF directly from buffer
        pdf_reader = PyPDF2.PdfReader(BytesIO(uploaded_file.read()))
        text = ""
        
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            text += page.extract_text() + "\n"
        
        return text.strip() if text.strip() else "No text found in PDF"
    except Exception as e:
        st.error(f"Error extracting PDF text: {str(e)}")
        return None


def render_riskometer_dashboard(risk_data: dict):
    """
    Renders the Riskometer dashboard with visual analytics.
    
    Args:
        risk_data (dict): Parsed JSON analysis data with risk information
    """
    st.markdown("### Risk Analysis Dashboard")
    st.divider()
    
    # Extract data
    risk_score = risk_data.get("risk_score", 0)
    risk_level = risk_data.get("risk_level", "Unknown")
    summary = risk_data.get("summary", "No summary available")
    financial_risks = risk_data.get("financial_risks", [])
    privacy_risks = risk_data.get("privacy_risks", [])
    legal_risks = risk_data.get("legal_risks", [])
    
    # Top row: Risk Score Metric
    st.metric(
        label="Overall Risk Score",
        value=f"{risk_score}/100",
        delta=None
    )
    
    # Risk Level Summary
    st.markdown(f"**Risk Level**: {risk_level}")
    st.markdown(f"**Summary**: {summary}")
    
    st.divider()
    
    # Progress bar with color coding
    st.markdown("### Risk Indicator")
    
    # Normalize score for progress bar (0-1)
    progress_value = risk_score / 100
    
    # Color coding logic
    if risk_score > 80:
        color_class = "Safe"
        bar_color = "#28a745"  # Green
    elif risk_score >= 50:
        color_class = "Medium"
        bar_color = "#f57c00"  # Orange
    else:
        color_class = "Risky"
        bar_color = "#d32f2f"  # Red
    
    # Display progress bar
    st.progress(progress_value)
    st.markdown(f"<p style='text-align: center; font-weight: 600; color: {bar_color};'>{color_class}</p>", unsafe_allow_html=True)
    
    st.divider()
    
    # Categorized Risk Cards - Three columns
    st.markdown("### Risk Breakdown")
    col1, col2, col3 = st.columns(3)
    
    # Financial Risks
    with col1:
        st.markdown("#### Financial Risks")
        if financial_risks:
            for risk in financial_risks:
                st.markdown(f"• {risk}")
        else:
            st.info("No financial risks identified")
    
    # Privacy Risks
    with col2:
        st.markdown("#### Privacy Risks")
        if privacy_risks:
            for risk in privacy_risks:
                st.markdown(f"• {risk}")
        else:
            st.info("No privacy risks identified")
    
    # Legal Risks
    with col3:
        st.markdown("#### Legal Risks")
        if legal_risks:
            for risk in legal_risks:
                st.markdown(f"• {risk}")
        else:
            st.info("No legal risks identified")
    
    st.divider()
    
    # Raw JSON export option
    st.markdown("### Export Results")
    json_str = json.dumps(risk_data, indent=2)
    st.download_button(
        label="Download Analysis as JSON",
        data=json_str,
        file_name="clearclause_analysis.json",
        mime="application/json",
        use_container_width=True
    )
    
    # Text report
    report_text = f"""ClearClause Analysis Report
===========================

Risk Score: {risk_score}/100
Risk Level: {risk_level}
Summary: {summary}

Financial Risks:
{chr(10).join([f'- {risk}' for risk in financial_risks]) if financial_risks else 'None identified'}

Privacy Risks:
{chr(10).join([f'- {risk}' for risk in privacy_risks]) if privacy_risks else 'None identified'}

Legal Risks:
{chr(10).join([f'- {risk}' for risk in legal_risks]) if legal_risks else 'None identified'}
"""
    
    st.download_button(
        label="Download Analysis as Text",
        data=report_text,
        file_name="clearclause_analysis_report.txt",
        mime="text/plain",
        use_container_width=True
    )


def analyze_risks_with_gemini(redacted_text: str) -> dict:
    """
    Sends redacted text to Google Gemini API for risk analysis with JSON response.
    
    Args:
        redacted_text (str): The redacted document text
        
    Returns:
        dict: Analysis results with parsed JSON structure
    """
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return {
                "error": "GEMINI_API_KEY not found. Please set it in your environment variables.",
                "success": False
            }
        
        # Configure Gemini API
        genai.configure(api_key=api_key)
        
        # Use gemini-1.5-flash model (fast and free)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        analysis_prompt = f"""Analyze the following redacted document and provide a JSON response with this exact structure:

{{
  "risk_score": <number 0-100>,
  "risk_level": "<High/Medium/Low based on score: 0-50=High, 51-80=Medium, 81-100=Low>",
  "summary": "<one sentence summary of overall risk>",
  "financial_risks": [<list of specific financial risks identified>],
  "privacy_risks": [<list of specific privacy risks identified>],
  "legal_risks": [<list of specific legal risks identified>]
}}

Scoring guidelines:
- 0-50: High Risk (Multiple concerning issues)
- 51-80: Medium Risk (Some areas of concern)
- 81-100: Low Risk (Generally safe)

Be concise and specific in identifying risks. Return ONLY valid JSON, no other text.

---DOCUMENT---
{redacted_text}
"""
        
        # Generate content with Gemini
        response = model.generate_content(analysis_prompt)
        response_text = response.text.strip()
        
        # Robust JSON extraction: find first { and last }
        json_start = response_text.find('{')
        json_end = response_text.rfind('}')
        
        if json_start == -1 or json_end == -1 or json_start > json_end:
            return {
                "error": "No valid JSON found in AI response",
                "success": False
            }
        
        # Extract JSON substring
        json_str = response_text[json_start:json_end + 1]
        
        # Parse JSON response
        analysis_json = json.loads(json_str)
        
        return {
            "analysis_json": analysis_json,
            "success": True
        }
    
    except json.JSONDecodeError as e:
        return {
            "error": f"Failed to parse AI response as JSON: {str(e)}",
            "success": False
        }
    except Exception as e:
        return {
            "error": f"Error analyzing document: {str(e)}",
            "success": False
        }


# Main header
st.markdown('<div class="header-title">ClearClause</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">Privacy-First Document Analyzer | Secure PII Redaction & Risk Analysis</div>',
    unsafe_allow_html=True
)

st.divider()

# Sidebar information
with st.sidebar:
    st.markdown("### About ClearClause")
    st.write("**Key Features:**")
    st.write("• Extracts text from PDF files")
    st.write("• Detects and redacts PII data")
    st.write("• Analyzes documents for risks")
    st.write("• Processes files securely in memory")
    
    st.markdown("### Privacy Features")
    st.write("• In-memory processing only")
    st.write("• Local PII detection with spaCy")
    st.write("• Redacted text analysis")
    st.write("• No original data exposure")

# File upload section
st.markdown("### Upload Document")
uploaded_file = st.file_uploader(
    "Choose a PDF file",
    type=["pdf"],
    help="Upload a PDF document for analysis. File is processed in memory only."
)

if uploaded_file:
    with st.spinner("Extracting text from PDF..."):
        extracted = extract_text_from_pdf(uploaded_file)
        
        if extracted and extracted != "No text found in PDF":
            st.session_state.extracted_text = extracted
            st.session_state.redacted_text = redact_pii(extracted)
            st.session_state.redaction_summary = get_redaction_summary(
                st.session_state.extracted_text,
                st.session_state.redacted_text
            )
            st.markdown(
                '<div class="success-box">PDF processed successfully!</div>',
                unsafe_allow_html=True
            )
        elif extracted == "No text found in PDF":
            st.warning("No text content found in the uploaded PDF")
else:
    st.info("Upload a PDF to get started")

st.divider()

# Display extracted and redacted text
if st.session_state.extracted_text:
    # Create tabs for Original and Redacted views
    tab1, tab2, tab3 = st.tabs(["Original Text", "Redacted View", "Redaction Statistics"])
    
    with tab1:
        st.markdown("### Original Document Text")
        st.text_area(
            "Original Text",
            value=st.session_state.extracted_text,
            height=300,
            disabled=True,
            label_visibility="collapsed"
        )
    
    with tab2:
        st.markdown("### Redacted Document Text")
        st.text_area(
            "Redacted Text",
            value=st.session_state.redacted_text,
            height=300,
            disabled=True,
            label_visibility="collapsed"
        )
        st.caption("Only this text will be sent for analysis")
    
    with tab3:
        st.markdown("### Redaction Summary")
        if st.session_state.redaction_summary:
            summary = st.session_state.redaction_summary
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric(
                    "Total Redactions",
                    summary["total_redactions"]
                )
            
            with col2:
                entity_breakdown = summary["entity_breakdown"]
                if entity_breakdown:
                    st.markdown("**Entity Types Redacted:**")
                    for entity_type, count in entity_breakdown.items():
                        st.write(f"• {entity_type}: {count}")
                else:
                    st.write("• No PII detected")
    
    st.divider()
    
    # Risk analysis button
    st.markdown("### Analyze Risks (Private Mode)")
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.info(
            "Privacy Protected: Only the redacted text (with PII removed) will be sent for analysis. "
            "Your original sensitive information stays private."
        )
    
    analyze_button = st.button(
        "Analyze Risks with Gemini",
        type="primary",
        use_container_width=True,
        key="analyze_risks_button"
    )
    
    if analyze_button:
        with st.spinner("Analyzing document with Gemini..."):
            result = analyze_risks_with_gemini(st.session_state.redacted_text)
            
            if result.get("success"):
                st.session_state.analysis_json = result["analysis_json"]
                st.markdown(
                    '<div class="success-box">Analysis complete!</div>',
                    unsafe_allow_html=True
                )
            else:
                st.error(f"Error: {result.get('error', 'Unknown error occurred')}")
    
    # Display analysis results with Riskometer dashboard
    if st.session_state.analysis_json:
        render_riskometer_dashboard(st.session_state.analysis_json)

else:
    st.markdown(
        '<div class="info-box"><b>Get Started</b>: Upload a PDF document above to begin analyzing for privacy risks and potential legal issues.</div>',
        unsafe_allow_html=True
    )

# Footer
st.divider()
st.markdown(
    "<div style='text-align: center; color: #666; font-size: 0.9rem;'>"
    "ClearClause 2026 | Privacy-First Document Analysis | "
    "Powered by Streamlit, spaCy, and Gemini</div>",
    unsafe_allow_html=True
)
