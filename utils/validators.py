"""
Data validation utilities for construction management app
"""

import pandas as pd
import re
from typing import Dict, List, Tuple

def validate_uploaded_file(file, required_columns: List[str], file_type: str = "excel") -> Dict:
    """
    Validate uploaded construction data files
    Returns dict with validation results
    """
    try:
        if file_type == "excel":
            df = pd.read_excel(file)
        elif file_type == "csv":
            df = pd.read_csv(file)
        else:
            return {"valid": False, "error": f"Unsupported file type: {file_type}"}
        
        # Check for required columns
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        # Basic data validation
        if df.empty:
            return {"valid": False, "error": "File is empty"}
        
        # Check for negative quantities (if applicable)
        quantity_columns = [col for col in df.columns if 'quantity' in col.lower() or 'qty' in col.lower()]
        for col in quantity_columns:
            if col in df.columns and (df[col] < 0).any():
                return {"valid": False, "error": f"Negative values found in {col}"}
        
        return {
            "valid": len(missing_columns) == 0,
            "missing_columns": missing_columns,
            "row_count": len(df),
            "columns_found": list(df.columns)
        }
        
    except Exception as e:
        return {"valid": False, "error": f"File validation failed: {str(e)}"}

def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_construction_quantity(value, min_value=0, max_value=1000000) -> Tuple[bool, str]:
    """Validate construction quantity values"""
    try:
        float_value = float(value)
        if float_value < min_value:
            return False, f"Value must be at least {min_value}"
        if float_value > max_value:
            return False, f"Value must be less than {max_value}"
        return True, "Valid"
    except (ValueError, TypeError):
        return False, "Value must be a number"