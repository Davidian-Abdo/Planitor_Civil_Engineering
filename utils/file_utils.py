"""
File utility functions for construction management app
"""

import os
import uuid
from datetime import datetime
from pathlib import Path
import streamlit as st

def safe_file_upload(uploaded_file, allowed_extensions=None, max_size_mb=50):
    """
    Safely handle file uploads with validation
    """
    if allowed_extensions is None:
        allowed_extensions = ['.xlsx', '.xls', '.csv']
    
    # Check file extension
    file_extension = Path(uploaded_file.name).suffix.lower()
    if file_extension not in allowed_extensions:
        return False, f"File type {file_extension} not allowed. Allowed: {', '.join(allowed_extensions)}"
    
    # Check file size
    file_size = uploaded_file.size / 1024 / 1024  # Convert to MB
    if file_size > max_size_mb:
        return False, f"File size {file_size:.2f}MB exceeds maximum {max_size_mb}MB"
    
    return True, "File validated successfully"

def generate_filename(prefix, extension, include_timestamp=True):
    """
    Generate a unique filename for outputs
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    
    if include_timestamp:
        return f"{prefix}_{timestamp}_{unique_id}{extension}"
    else:
        return f"{prefix}_{unique_id}{extension}"

def ensure_directory(directory):
    """Ensure directory exists, create if not"""
    Path(directory).mkdir(parents=True, exist_ok=True)
    return directory