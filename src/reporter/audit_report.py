"""
Audit report generation (Markdown -> HTML -> PDF).
"""
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
from jinja2 import Template

from src.models import EligibilityResult, ERAFile
from src.utils.logging import logger


AUDIT_TEMPLATE = """# ERA IDR Eligibility Audit Report

**Generated:** {{ generated_date }}  
**Total Files Processed:** {{ total_files }}  
**Total Claims:** {{ total_claims }}  
**Total Service Lines:** {{ total_lines }}  
**Eligible Lines:** {{ eligible_lines }}  
**Eligibility Rate:** {{ eligibility_rate }}%

---

## Summary by File

{% for file_summary in file_summaries %}
### {{ file_summary.filename }}

- **Claims:** {{ file_summary.claim_count }}
- **Service Lines:** {{ file_summary.line_count }}
- **Eligible Lines:** {{ file_summary.eligible_count }}
- **Payment Date:** {{ file_summary.payment_date or "Not found" }}
- **Check/EFT:** {{ file_summary.check_eft or "Not found" }}

{% if file_summary.errors %}
**Processing Errors:**
{% for error in file_summary.errors %}
- {{ error }}
{% endfor %}
{% endif %}

{% if file_summary.warnings %}
**Processing Warnings:**
{% for warning in file_summary.warnings %}
- {{ warning }}
{% endfor %}
{% endif %}

{% endfor %}

---

## Matched Codes & Rationale

{% for result in eligible_results %}
### File: {{ result.file }} | Claim: {{ result.claim_id }} | Line: {{ result.svc_index }}

- **CPT:** {{ result.cpt or "N/A" }}{% if result.modifiers %} (Modifiers: {{ result.modifiers|join(", ") }}){% endif %}
- **CAS:** {{ result.cas_group or "N/A" }}-{{ result.cas_reason or "N/A" }}{% if result.cas_amount %} (${{ result.cas_amount }}){% endif %}
- **RARC:** {{ result.rarc_list|join(", ") if result.rarc_list else "N/A" }}
- **Eligibility Basis:** {{ result.eligibility_basis }}
- **Payment Date:** {{ result.payment_date.strftime("%Y-%m-%d") if result.payment_date else "Not found" }}
- **Open Negotiation End:** {{ result.open_negotiation_end.strftime("%Y-%m-%d") if result.open_negotiation_end else "N/A" }}
- **IDR Initiation Window End:** {{ result.idr_initiation_window_end.strftime("%Y-%m-%d") if result.idr_initiation_window_end else "N/A" }}

{% if result.errors_warnings %}
**Warnings:**
{% for warning in result.errors_warnings %}
- {{ warning }}
{% endfor %}
{% endif %}

---

{% endfor %}

## Non-Compliant or Indeterminate Items

{% for result in non_eligible_results %}
### File: {{ result.file }} | Claim: {{ result.claim_id }} | Line: {{ result.svc_index }}

- **CPT:** {{ result.cpt or "N/A" }}
- **CAS:** {{ result.cas_group or "N/A" }}-{{ result.cas_reason or "N/A" }}
- **RARC:** {{ result.rarc_list|join(", ") if result.rarc_list else "N/A" }}
- **Reason:** No matching codes found in database
{% if result.errors_warnings %}
- **Issues:** {{ result.errors_warnings|join("; ") }}
{% endif %}

---

{% endfor %}

## Processing Issues

{% if processing_issues %}
{% for issue in processing_issues %}
- **{{ issue.filename }}:** {{ issue.error }}
{% endfor %}
{% else %}
No processing issues encountered.
{% endif %}

---

*End of Report*
"""


def generate_audit_report(
    results: List[EligibilityResult],
    era_files: List[ERAFile],
    processing_issues: Optional[List[Dict[str, str]]] = None,
    redact: bool = False
) -> str:
    """
    Generate human-readable audit report in Markdown format.
    
    Args:
        results: List of EligibilityResult objects
        era_files: List of ERAFile objects
        processing_issues: List of dicts with 'filename' and 'error' keys
        redact: Whether to redact PHI
    
    Returns:
        Markdown report string
    """
    processing_issues = processing_issues or []
    
    # Separate eligible and non-eligible
    eligible_results = [r for r in results if r.eligible_flag]
    non_eligible_results = [r for r in results if not r.eligible_flag]
    
    # Build file summaries
    file_summaries = []
    files_by_name = {f.filename: f for f in era_files}
    
    for filename in set(r.file for r in results):
        file_results = [r for r in results if r.file == filename]
        era_file = files_by_name.get(filename)
        
        file_summaries.append({
            "filename": filename,
            "claim_count": len(set(r.claim_id for r in file_results)),
            "line_count": len(file_results),
            "eligible_count": sum(1 for r in file_results if r.eligible_flag),
            "payment_date": file_results[0].payment_date if file_results and file_results[0].payment_date else None,
            "check_eft": file_results[0].check_eft if file_results and file_results[0].check_eft else None,
            "errors": era_file.processing_errors if era_file else [],
            "warnings": era_file.processing_warnings if era_file else []
        })
    
    # Calculate summary stats
    total_files = len(file_summaries)
    total_claims = sum(fs["claim_count"] for fs in file_summaries)
    total_lines = len(results)
    eligible_lines = len(eligible_results)
    eligibility_rate = (eligible_lines / total_lines * 100) if total_lines > 0 else 0
    
    # Render template
    template = Template(AUDIT_TEMPLATE)
    report = template.render(
        generated_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        total_files=total_files,
        total_claims=total_claims,
        total_lines=total_lines,
        eligible_lines=eligible_lines,
        eligibility_rate=f"{eligibility_rate:.1f}",
        file_summaries=file_summaries,
        eligible_results=eligible_results,
        non_eligible_results=non_eligible_results,
        processing_issues=processing_issues
    )
    
    return report


def markdown_to_html(markdown: str) -> str:
    """
    Convert Markdown to HTML (simple implementation).
    
    Args:
        markdown: Markdown string
    
    Returns:
        HTML string
    """
    import re
    
    html = markdown
    
    # Headers
    html = re.sub(r'^### (.*?)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.*?)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.*?)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
    
    # Bold
    html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)
    
    # Lists
    html = re.sub(r'^- (.*?)$', r'<li>\1</li>', html, flags=re.MULTILINE)
    html = re.sub(r'(<li>.*?</li>)', r'<ul>\1</ul>', html, flags=re.DOTALL)
    
    # Line breaks
    html = html.replace('\n', '<br>\n')
    
    # Horizontal rule
    html = html.replace('---', '<hr>')
    
    # Wrap in HTML structure
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>ERA IDR Eligibility Audit Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
        h1 {{ color: #333; border-bottom: 2px solid #333; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; }}
        h3 {{ color: #777; margin-top: 20px; }}
        ul {{ margin-left: 20px; }}
        hr {{ margin: 20px 0; border: none; border-top: 1px solid #ddd; }}
        strong {{ color: #000; }}
    </style>
</head>
<body>
{html}
</body>
</html>"""
    
    return html


def html_to_pdf(html: str, output_path: Path) -> bool:
    """
    Convert HTML to PDF using WeasyPrint.
    
    Args:
        html: HTML string
        output_path: Path to save PDF
    
    Returns:
        True if successful
    """
    try:
        from weasyprint import HTML
        HTML(string=html).write_pdf(output_path)
        logger.info(f"PDF report saved to {output_path}")
        return True
    except ImportError as e:
        logger.warning(f"WeasyPrint not available: {e}")
        return False
    except OSError as e:
        # Windows-specific: missing system libraries (libgobject, etc.)
        logger.warning(f"PDF generation failed - system libraries missing: {e}")
        logger.warning("WeasyPrint requires system libraries. See: https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation")
        return False
    except Exception as e:
        logger.error(f"Failed to generate PDF: {e}")
        return False


def is_pdf_available() -> bool:
    """
    Check if PDF generation is available.
    
    Returns:
        True if WeasyPrint and required libraries are available
    """
    import sys
    import io
    from contextlib import redirect_stderr
    
    # Suppress WeasyPrint's error messages during import check
    try:
        # Redirect stderr to suppress WeasyPrint's library loading errors
        stderr_capture = io.StringIO()
        with redirect_stderr(stderr_capture):
            # Try importing the module first
            import weasyprint
            # Then try importing HTML class
            from weasyprint import HTML
        # If we get here, import succeeded
        return True
    except OSError:
        # OSError occurs when system libraries (libgobject, etc.) are missing
        # This is the most common failure mode on Windows
        return False
    except ImportError:
        # WeasyPrint package not installed
        return False
    except Exception:
        # Catch any other import-time errors
        return False


def generate_audit_reports(
    results: List[EligibilityResult],
    era_files: List[ERAFile],
    output_dir: Path,
    processing_issues: Optional[List[Dict[str, str]]] = None,
    redact: bool = False
) -> Dict[str, Path]:
    """
    Generate all audit report formats (Markdown, HTML, PDF).
    
    Args:
        results: List of EligibilityResult objects
        era_files: List of ERAFile objects
        output_dir: Directory to save reports
        processing_issues: List of processing issues
        redact: Whether to redact PHI
    
    Returns:
        Dict with 'markdown', 'html', 'pdf' keys pointing to file paths
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Generate Markdown
    markdown = generate_audit_report(results, era_files, processing_issues, redact)
    md_path = output_dir / f"audit_report_{timestamp}.md"
    md_path.write_text(markdown, encoding='utf-8')
    
    # Generate HTML
    html = markdown_to_html(markdown)
    html_path = output_dir / f"audit_report_{timestamp}.html"
    html_path.write_text(html, encoding='utf-8')
    
    # Generate PDF
    pdf_path = output_dir / f"audit_report_{timestamp}.pdf"
    html_to_pdf(html, pdf_path)
    
    return {
        "markdown": md_path,
        "html": html_path,
        "pdf": pdf_path
    }

