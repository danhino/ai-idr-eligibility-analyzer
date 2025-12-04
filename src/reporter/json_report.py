"""
JSON report generation.
"""
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import date

from src.models import EligibilityResult
from src.utils.logging import logger


def serialize_date(obj):
    """JSON serializer for date objects."""
    if isinstance(obj, date):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


def generate_json_report(results: List[EligibilityResult], output_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Generate JSON report from eligibility results.
    
    Args:
        results: List of EligibilityResult objects
        output_path: Optional path to save JSON file
    
    Returns:
        Dict with hierarchical structure
    """
    # Group by file
    by_file: Dict[str, Dict[str, Any]] = {}
    
    for result in results:
        if result.file not in by_file:
            by_file[result.file] = {
                "filename": result.file,
                "claims": {}
            }
        
        file_data = by_file[result.file]
        
        if result.claim_id not in file_data["claims"]:
            file_data["claims"][result.claim_id] = {
                "claim_id": result.claim_id,
                "patient_id": result.patient_id,
                "payment_date": result.payment_date.isoformat() if result.payment_date else None,
                "check_eft": result.check_eft,
                "service_lines": []
            }
        
        claim_data = file_data["claims"][result.claim_id]
        
        line_data = {
            "svc_index": result.svc_index,
            "cpt": result.cpt,
            "modifiers": result.modifiers,
            "cas_group": result.cas_group,
            "cas_reason": result.cas_reason,
            "cas_amount": str(result.cas_amount) if result.cas_amount else None,
            "rarc_list": result.rarc_list,
            "eligible_flag": result.eligible_flag,
            "eligibility_basis": result.eligibility_basis,
            "open_negotiation_end": result.open_negotiation_end.isoformat() if result.open_negotiation_end else None,
            "idr_initiation_window_end": result.idr_initiation_window_end.isoformat() if result.idr_initiation_window_end else None,
            "errors_warnings": result.errors_warnings
        }
        
        claim_data["service_lines"].append(line_data)
    
    # Convert to list structure
    report = {
        "files": list(by_file.values()),
        "summary": {
            "total_files": len(by_file),
            "total_claims": sum(len(f["claims"]) for f in by_file.values()),
            "total_service_lines": len(results),
            "eligible_lines": sum(1 for r in results if r.eligible_flag)
        }
    }
    
    if output_path:
        try:
            with open(output_path, 'w') as f:
                json.dump(report, f, indent=2, default=serialize_date)
            logger.info(f"JSON report saved to {output_path}")
        except Exception as e:
            logger.error(f"Failed to save JSON report: {e}")
    
    return report

