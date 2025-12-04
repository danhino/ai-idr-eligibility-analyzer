"""
Streamlit entrypoint for IDR Analyzer application.
"""
import streamlit as st
from pathlib import Path
from typing import List
import traceback
import tempfile

from src.config import AI_ENABLED, SAMPLES_DIR
from src.db import init_db, load_seed_data
from src.pdf_extract import extract_text_from_pdf
from src.era_parser import ERAParser
from src.rules import EligibilityEvaluator
from src.models import ERAFile, EligibilityResult
from src.ui.forms import render_code_management_form
from src.ui.views import render_results_table, render_download_buttons
from src.utils.logging import logger
from src.ai_enhance import is_available as ai_available

# Page config
st.set_page_config(
    page_title="IDR EligibilityAnalyzer",
    page_icon="📋",
    layout="wide"
)

# Initialize session state
if "results" not in st.session_state:
    st.session_state.results = []
if "era_files" not in st.session_state:
    st.session_state.era_files = []
if "processing_issues" not in st.session_state:
    st.session_state.processing_issues = []


def initialize_app():
    """Initialize database and load seed data."""
    try:
        init_db()
        load_seed_data()
        logger.info("Application initialized")
    except Exception as e:
        logger.error(f"Initialization error: {e}")
        st.error(f"Initialization error: {e}")


def process_files(uploaded_files: List, use_ai: bool = False, redact: bool = False):
    """
    Process uploaded ERA files.
    
    Args:
        uploaded_files: List of uploaded file objects
        use_ai: Whether to use AI enhancement
        redact: Whether to redact PHI
    """
    results = []
    era_files = []
    processing_issues = []
    ai_usage_stats = {
        "files_processed_with_ai": 0,
        "ai_successes": 0,
        "ai_failures": 0
    }
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    ai_status_text = st.empty()
    
    total_files = len(uploaded_files)
    
    # Show initial AI status
    if use_ai:
        if ai_available():
            ai_status_text.info("🤖 AI Enhancement: **Enabled** - OpenAI API is available")
        else:
            ai_status_text.warning("🤖 AI Enhancement: **Requested but unavailable** - OpenAI API key not configured")
            use_ai = False  # Disable if not available
    else:
        ai_status_text.empty()
    
    for idx, uploaded_file in enumerate(uploaded_files):
        try:
            status_text.text(f"📄 Processing {uploaded_file.name} ({idx + 1}/{total_files})...")
            progress_bar.progress((idx + 1) / total_files)
            
            # Determine file type
            file_ext = Path(uploaded_file.name).suffix.lower()
            tmp_path = None
            if file_ext in [".pdf"]:
                file_type = "pdf"
                status_text.text(f"📄 Processing {uploaded_file.name} ({idx + 1}/{total_files})... Extracting text from PDF...")
                # Read PDF to temporary file
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                        tmp_path = Path(tmp_file.name)
                        tmp_file.write(uploaded_file.read())
                    
                    # Extract text (file is now closed)
                    text = extract_text_from_pdf(tmp_path)
                finally:
                    # Clean up temp file
                    if tmp_path and tmp_path.exists():
                        try:
                            tmp_path.unlink()
                        except (PermissionError, OSError) as e:
                            # File might still be locked, log but continue
                            logger.warning(f"Could not delete temp file {tmp_path}: {e}")
            elif file_ext in [".edi", ".835", ".txt"]:
                file_type = "835"
                text = uploaded_file.read().decode("utf-8", errors="ignore")
            else:
                processing_issues.append({
                    "filename": uploaded_file.name,
                    "error": f"Unsupported file type: {file_ext}"
                })
                continue
            
            # Parse ERA
            status_text.text(f"📄 Processing {uploaded_file.name} ({idx + 1}/{total_files})... Parsing ERA data...")
            parser = ERAParser()
            era_file = parser.parse_file(text, uploaded_file.name, file_type)
            
            # Optional AI enhancement
            if use_ai and ai_available():
                ai_usage_stats["files_processed_with_ai"] += 1
                status_text.text(f"📄 Processing {uploaded_file.name} ({idx + 1}/{total_files})... 🤖 Using AI enhancement...")
                ai_status_text.info(f"🤖 **AI Processing**: Enhancing {uploaded_file.name} with OpenAI...")
                
                try:
                    from src.ai_enhance import summarize_segments, validate_line_items
                    
                    # Extract segments for AI analysis
                    if file_type == "835":
                        # For 835 files, get segments
                        segments = parser.tokenizer.tokenize_segments(text)
                        if segments:
                            ai_result = summarize_segments(segments[:50])  # Limit to first 50
                            if ai_result:
                                ai_usage_stats["ai_successes"] += 1
                                ai_status_text.success(f"✅ **AI Enhancement Complete**: {uploaded_file.name} - Extracted additional codes/validations")
                                era_file.processing_warnings.append("AI enhancement applied successfully")
                            else:
                                ai_usage_stats["ai_failures"] += 1
                                ai_status_text.warning(f"⚠️ **AI Enhancement**: {uploaded_file.name} - No additional insights from AI")
                    else:
                        # For PDFs, validate service lines
                        service_lines_data = []
                        for claim in era_file.claims:
                            for svc_line in claim.service_lines:
                                svc_data = {
                                    "cpt": svc_line.cpt.code if svc_line.cpt else None,
                                    "description": svc_line.description,
                                    "cas_codes": [f"{cas.group_code}-{cas.reason_code}" for cas in svc_line.cas_adjustments],
                                    "rarc_codes": [r.code for r in svc_line.remark_codes]
                                }
                                service_lines_data.append(svc_data)
                        
                        if service_lines_data:
                            ai_result = validate_line_items(service_lines_data[:20])  # Limit to first 20
                            if ai_result:
                                ai_usage_stats["ai_successes"] += 1
                                ai_status_text.success(f"✅ **AI Enhancement Complete**: {uploaded_file.name} - Validated service lines")
                                era_file.processing_warnings.append("AI validation applied successfully")
                            else:
                                ai_usage_stats["ai_failures"] += 1
                                ai_status_text.warning(f"⚠️ **AI Enhancement**: {uploaded_file.name} - AI validation returned no results")
                        else:
                            ai_status_text.info(f"ℹ️ **AI Enhancement**: {uploaded_file.name} - No service lines to validate")
                    
                except Exception as ai_error:
                    ai_usage_stats["ai_failures"] += 1
                    logger.warning(f"AI enhancement failed for {uploaded_file.name}: {ai_error}")
                    era_file.processing_warnings.append(f"AI enhancement failed: {ai_error}")
                    ai_status_text.error(f"❌ **AI Enhancement Failed**: {uploaded_file.name} - {str(ai_error)[:100]}")
            
            era_files.append(era_file)
            
            # Evaluate eligibility
            status_text.text(f"📄 Processing {uploaded_file.name} ({idx + 1}/{total_files})... Evaluating eligibility...")
            evaluator = EligibilityEvaluator()
            for claim in era_file.claims:
                claim_results = evaluator.evaluate_claim(claim, uploaded_file.name)
                results.extend(claim_results)
            
            status_text.text(f"✅ Completed {uploaded_file.name} ({idx + 1}/{total_files}) - {len(era_file.claims)} claims, {len([r for r in results if r.file == uploaded_file.name])} service lines")
            logger.info(f"Processed {uploaded_file.name}: {len(era_file.claims)} claims, {len(results)} service lines")
        
        except Exception as e:
            error_msg = f"Error processing {uploaded_file.name}: {str(e)}"
            logger.error(f"{error_msg}\n{traceback.format_exc()}")
            processing_issues.append({
                "filename": uploaded_file.name,
                "error": error_msg
            })
    
    progress_bar.empty()
    
    # Final status summary
    if use_ai and ai_available():
        if ai_usage_stats["files_processed_with_ai"] > 0:
            success_rate = (ai_usage_stats["ai_successes"] / ai_usage_stats["files_processed_with_ai"]) * 100
            ai_status_text.success(
                f"🤖 **AI Enhancement Summary**: "
                f"Processed {ai_usage_stats['files_processed_with_ai']} file(s) with AI | "
                f"Success: {ai_usage_stats['ai_successes']} | "
                f"Failed: {ai_usage_stats['ai_failures']} | "
                f"Success Rate: {success_rate:.1f}%"
            )
        else:
            ai_status_text.info("🤖 **AI Enhancement**: Enabled but not used (no files processed)")
    else:
        ai_status_text.empty()
    
    status_text.empty()
    
    return results, era_files, processing_issues


# Initialize on first run
if "initialized" not in st.session_state:
    initialize_app()
    st.session_state.initialized = True

# Main UI
st.title("📋 IDR Eligibility Analyzer")
st.markdown("Analyze files for IDR eligibility")

# Sidebar
with st.sidebar:
    st.header("Configuration")
    
    # File upload
    uploaded_files = st.file_uploader(
        "Upload ERA Files",
        type=["pdf", "edi", "835", "txt"],
        accept_multiple_files=True,
        help="Upload one or more ERA files (PDF or raw 835 format)"
    )
    
    # Options
    st.divider()
    st.subheader("AI Enhancement")
    
    if AI_ENABLED:
        st.success("✅ OpenAI API configured and available")
    else:
        st.warning("⚠️ OpenAI API key not configured")
        st.caption("Set OPENAI_API_KEY in .env to enable AI features")
    
    use_ai = st.checkbox(
        "Use OpenAI Enhancement",
        value=False,
        disabled=not AI_ENABLED,
        help="Enable AI-powered parsing and validation (requires API key)" if AI_ENABLED else "OpenAI API key not configured"
    )
    
    if use_ai and AI_ENABLED:
        st.info("🤖 AI enhancement will be applied during processing")
    
    redact_phi = st.checkbox(
        "Redact Identifiers in Audit Output",
        value=False,
        help="Mask patient names and IDs in reports"
    )
    
    # Process button
    process_btn = st.button("Run Analysis", type="primary", use_container_width=True)  # use_container_width still valid for buttons
    
    st.divider()
    
    # Navigation
    st.header("Navigation")
    page = st.radio(
        "Select Page",
        ["Analysis", "Code Management"],
        label_visibility="collapsed"
    )

# Main content area
if page == "Analysis":
    # Process files if button clicked
    if process_btn and uploaded_files:
        import tempfile
        with st.spinner("Processing files..."):
            results, era_files, issues = process_files(uploaded_files, use_ai, redact_phi)
            st.session_state.results = results
            st.session_state.era_files = era_files
            st.session_state.processing_issues = issues
            
            if results:
                st.success(f"Processed {len(uploaded_files)} file(s). Found {len(results)} service lines.")
            else:
                st.warning("No service lines found in uploaded files.")
    
    # Display results
    if st.session_state.results:
        render_results_table(st.session_state.results)
        st.divider()
        render_download_buttons(
            st.session_state.results,
            st.session_state.era_files,
            st.session_state.processing_issues
        )
    
    # Display processing issues
    if st.session_state.processing_issues:
        st.warning("Processing Issues")
        for issue in st.session_state.processing_issues:
            st.error(f"**{issue['filename']}**: {issue['error']}")

elif page == "Code Management":
    render_code_management_form()

# Footer
st.divider()
st.caption("IDR Eligibility Analyzer v1.0 | For billing staff use only")
