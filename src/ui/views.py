"""
Views for displaying results and downloads.
"""
import streamlit as st
import pandas as pd
from typing import List, Optional
from pathlib import Path
import io

from src.models import EligibilityResult
from src.reporter.csv_report import generate_csv_report
from src.reporter.json_report import generate_json_report
from src.reporter.audit_report import generate_audit_reports
from src.models import ERAFile
from src.utils.logging import logger


def render_results_table(results: List[EligibilityResult]):
    """
    Render interactive results table with filters, grouped by Account Number (ACNT).
    
    Args:
        results: List of EligibilityResult objects
    """
    if not results:
        st.info("No results to display. Upload and process files first.")
        return
    
    # Group by Account Number (ACNT) for summary view - only show codes that matched database
    # Preserve order as they appear in the file (top to bottom)
    st.subheader("Summary by Account Number (Codes Matched in Database)")
    acnt_summary = {}
    acnt_order = []  # Track order of first appearance
    
    for r in results:
        acnt = r.patient_id or "Unknown"
        if acnt not in acnt_summary:
            acnt_summary[acnt] = {
                "ACNT": acnt,
                "Claims": set(),
                "CPT Codes": set(),  # Only codes that matched database
                "CAS Codes": set(),  # Only codes that matched database
                "RARC Codes": set(),  # Only codes that matched database
                "Eligible Lines": 0,
                "Total Lines": 0
            }
            acnt_order.append(acnt)  # Track first appearance order
        acnt_summary[acnt]["Claims"].add(r.claim_id)
        # Only add codes if they made the line eligible (i.e., matched database)
        # Parse eligibility_basis to extract matched codes
        if r.eligible_flag and r.eligibility_basis:
            # Extract CPT codes from basis (format: "CPT 99284")
            if r.cpt and f"CPT {r.cpt}" in r.eligibility_basis:
                acnt_summary[acnt]["CPT Codes"].add(r.cpt)
            # Extract CAS codes from basis (format: "CAS CO-45")
            if r.cas_group and r.cas_reason and f"CAS {r.cas_group}-{r.cas_reason}" in r.eligibility_basis:
                acnt_summary[acnt]["CAS Codes"].add(f"{r.cas_group}-{r.cas_reason}")
            # Extract RARC codes from basis (format: "RARC MA130")
            if r.rarc_list:
                for rarc in r.rarc_list:
                    if f"RARC {rarc}" in r.eligibility_basis:
                        acnt_summary[acnt]["RARC Codes"].add(rarc)
        acnt_summary[acnt]["Total Lines"] += 1
        if r.eligible_flag:
            acnt_summary[acnt]["Eligible Lines"] += 1
    
    # Display summary in file order (as they appear top to bottom)
    summary_data = []
    for acnt in acnt_order:  # Use first appearance order instead of sorted()
        data = acnt_summary[acnt]
        summary_data.append({
            "Account Number": data["ACNT"],
            "Claims": len(data["Claims"]),
            "CPT Codes (Matched)": ", ".join(sorted(data["CPT Codes"])) if data["CPT Codes"] else "None",
            "CAS Codes (Matched)": ", ".join(sorted(data["CAS Codes"])) if data["CAS Codes"] else "None",
            "RARC Codes (Matched)": ", ".join(sorted(data["RARC Codes"])) if data["RARC Codes"] else "None",
            "Eligible Lines": data["Eligible Lines"],
            "Total Lines": data["Total Lines"]
        })
    
    summary_df = pd.DataFrame(summary_data)
    if len(summary_df) > 0:
        st.dataframe(summary_df, width='stretch', use_container_width=True)
    else:
        st.info("No codes matched the database. Please ensure codes are configured in the Code Management section.")
    
    st.divider()
    
    # Detailed results table
    # Results are already in file order (top to bottom as read from file)
    st.subheader("Detailed Results")
    
    # Convert to DataFrame - preserve order from results list (file order)
    # Add a sequence number to maintain file order even after filtering
    df_data = []
    for idx, r in enumerate(results):
        df_data.append({
            "_sequence": idx,  # Internal sequence to preserve file order
            "File": r.file,
            "Account Number": r.patient_id or "Unknown",
            "Claim ID": r.claim_id,
            "Line": r.svc_index,
            "CPT": r.cpt or "",
            "Modifiers": ",".join(r.modifiers) if r.modifiers else "",
            "GRP/RC-AMT": f"{r.cas_group or ''}-{r.cas_reason or ''}" if r.cas_group or r.cas_reason else "",
            "Amount": str(r.cas_amount) if r.cas_amount else "",
            "RARC": ",".join(r.rarc_list) if r.rarc_list else "",
            "Eligible": "Yes" if r.eligible_flag else "No",
            "Basis": r.eligibility_basis,
            "Payment Date": r.payment_date.strftime("%Y-%m-%d") if r.payment_date else "",
            "Open Neg End": r.open_negotiation_end.strftime("%Y-%m-%d") if r.open_negotiation_end else "",
            "IDR Window End": r.idr_initiation_window_end.strftime("%Y-%m-%d") if r.idr_initiation_window_end else ""
        })
    df = pd.DataFrame(df_data)
    
    # Filters
    st.subheader("Filters")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        file_filter = st.multiselect("File", options=sorted(df["File"].unique()), default=[])
    with col2:
        acnt_filter = st.multiselect("Account Number", options=sorted(df["Account Number"].unique()), default=[])
    with col3:
        eligible_filter = st.multiselect("Eligible", options=["Yes", "No"], default=[])
    with col4:
        cpt_filter = st.text_input("CPT Code")
    with col5:
        cas_filter = st.text_input("GRP/RC Code")
    
    # Apply filters - preserve file order
    filtered_df = df.copy()
    if file_filter:
        filtered_df = filtered_df[filtered_df["File"].isin(file_filter)]
    if acnt_filter:
        filtered_df = filtered_df[filtered_df["Account Number"].isin(acnt_filter)]
    if eligible_filter:
        filtered_df = filtered_df[filtered_df["Eligible"].isin(eligible_filter)]
    if cpt_filter:
        filtered_df = filtered_df[filtered_df["CPT"].str.contains(cpt_filter, case=False, na=False)]
    if cas_filter:
        filtered_df = filtered_df[filtered_df["GRP/RC-AMT"].str.contains(cas_filter, case=False, na=False)]
    
    # Sort by sequence to maintain file order (top to bottom as read from file)
    filtered_df = filtered_df.sort_values("_sequence")
    
    # Remove internal sequence column before display
    display_df = filtered_df.drop(columns=["_sequence"])
    
    # Display table
    st.subheader(f"Detailed Results ({len(filtered_df)} of {len(df)} lines)")
    st.dataframe(display_df, width='stretch', height=400)
    
    return display_df


def render_download_buttons(
    results: List[EligibilityResult],
    era_files: List[ERAFile],
    processing_issues: Optional[List[dict]] = None
):
    """
    Render download buttons for reports.
    
    Args:
        results: List of EligibilityResult objects
        era_files: List of ERAFile objects
        processing_issues: Optional list of processing issues
    """
    st.subheader("Download Reports")
    
    if not results:
        st.warning("No results available for download.")
        return
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # CSV download
        csv_df = generate_csv_report(results)
        csv_buffer = io.StringIO()
        csv_df.to_csv(csv_buffer, index=False)
        st.download_button(
            label="Download CSV",
            data=csv_buffer.getvalue(),
            file_name="era_results.csv",
            mime="text/csv"
        )
    
    with col2:
        # JSON download
        json_report = generate_json_report(results)
        json_str = __import__("json").dumps(json_report, indent=2, default=str)
        st.download_button(
            label="Download JSON",
            data=json_str,
            file_name="era_results.json",
            mime="application/json"
        )
    
    with col3:
        # HTML download
        from src.reporter.audit_report import generate_audit_report, markdown_to_html
        markdown = generate_audit_report(results, era_files, processing_issues)
        html = markdown_to_html(markdown)
        st.download_button(
            label="Download HTML",
            data=html,
            file_name="audit_report.html",
            mime="text/html"
        )
    
    with col4:
        # PDF download
        from src.reporter.audit_report import generate_audit_report, markdown_to_html, html_to_pdf, is_pdf_available
        import tempfile
        
        try:
            pdf_available = is_pdf_available()
        except Exception as e:
            # Fallback if check itself fails
            pdf_available = False
            logger.debug(f"PDF availability check failed: {e}")
        
        if pdf_available:
            try:
                markdown = generate_audit_report(results, era_files, processing_issues)
                html = markdown_to_html(markdown)
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                    tmp_path = Path(tmp_file.name)
                    if html_to_pdf(html, tmp_path):
                        pdf_bytes = tmp_path.read_bytes()
                        st.download_button(
                            label="Download PDF",
                            data=pdf_bytes,
                            file_name="audit_report.pdf",
                            mime="application/pdf"
                        )
                        tmp_path.unlink()  # Clean up
                    else:
                        st.warning("PDF generation unavailable. Please use HTML download instead.")
            except Exception as e:
                logger.warning(f"PDF generation error: {e}")
                st.warning("PDF generation unavailable. Please use HTML download instead.")
        else:
            st.info("PDF generation requires system libraries. Use HTML download instead.")

