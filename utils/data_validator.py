"""
Data Validation Utilities
Helper functions for validating and cleaning extracted data
"""

import pandas as pd
import numpy as np
from typing import Any, Dict, List, Optional, Tuple


def validate_numeric_value(value: Any, min_val: Optional[float] = None, max_val: Optional[float] = None) -> Tuple[bool, Optional[float]]:
    """
    Validate and convert value to numeric
    
    Args:
        value: Value to validate
        min_val: Minimum allowed value (optional)
        max_val: Maximum allowed value (optional)
        
    Returns:
        Tuple of (is_valid, converted_value)
    """
    try:
        # Handle string inputs (remove commas, spaces)
        if isinstance(value, str):
            value = value.replace(',', '').replace(' ', '').strip()
        
        # Convert to float
        num_val = float(value)
        
        # Check range
        if min_val is not None and num_val < min_val:
            return False, None
        if max_val is not None and num_val > max_val:
            return False, None
            
        return True, num_val
        
    except (ValueError, TypeError):
        return False, None


def validate_percentage(value: Any) -> Tuple[bool, Optional[float]]:
    """
    Validate percentage value (should be 0-100)
    
    Args:
        value: Percentage value to validate
        
    Returns:
        Tuple of (is_valid, converted_value)
    """
    return validate_numeric_value(value, min_val=0, max_val=100)


def clean_company_name(name: str) -> str:
    """
    Standardize company name
    
    Args:
        name: Company name to clean
        
    Returns:
        Cleaned company name
    """
    # Remove common suffixes
    suffixes = ['Limited', 'Ltd', 'Ltd.', 'Private', 'Pvt.', 'Pvt', 'Company', 'Co.', 'Inc.', 'Corporation', 'Corp.']
    
    cleaned = name.strip()
    for suffix in suffixes:
        cleaned = cleaned.replace(suffix, '').strip()
        
    return cleaned


def detect_outliers(df: pd.DataFrame, column: str, method: str = 'iqr', threshold: float = 1.5) -> pd.Series:
    """
    Detect outliers in a numeric column
    
    Args:
        df: DataFrame
        column: Column name to check
        method: 'iqr' (Interquartile Range) or 'zscore'
        threshold: Threshold for outlier detection (1.5 for IQR, 3 for zscore)
        
    Returns:
        Boolean Series indicating outliers
    """
    if method == 'iqr':
        Q1 = df[column].quantile(0.25)
        Q3 = df[column].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - threshold * IQR
        upper_bound = Q3 + threshold * IQR
        return (df[column] < lower_bound) | (df[column] > upper_bound)
        
    elif method == 'zscore':
        from scipy import stats
        z_scores = np.abs(stats.zscore(df[column].dropna()))
        return pd.Series(z_scores > threshold, index=df.index)
        
    else:
        raise ValueError(f"Unknown method: {method}")


def validate_esg_score(score: float) -> bool:
    """
    Validate ESG score (should be 0-10)
    
    Args:
        score: ESG score to validate
        
    Returns:
        True if valid, False otherwise
    """
    return 0 <= score <= 10


def check_missing_data(df: pd.DataFrame, threshold: float = 0.5) -> Dict[str, float]:
    """
    Check for missing data in DataFrame
    
    Args:
        df: DataFrame to check
        threshold: Threshold for warning (0.5 = 50% missing)
        
    Returns:
        Dictionary of column names with missing % > threshold
    """
    missing_pct = df.isnull().sum() / len(df)
    problematic = missing_pct[missing_pct > threshold]
    return problematic.to_dict()


def validate_date_format(date_str: str) -> Tuple[bool, Optional[pd.Timestamp]]:
    """
    Validate and parse date string
    
    Args:
        date_str: Date string to validate
        
    Returns:
        Tuple of (is_valid, parsed_date)
    """
    try:
        date = pd.to_datetime(date_str)
        return True, date
    except:
        return False, None


def cross_validate_sum(values: List[float], expected_total: float, tolerance: float = 0.01) -> bool:
    """
    Check if sum of values equals expected total (within tolerance)
    
    Args:
        values: List of values to sum
        expected_total: Expected sum
        tolerance: Acceptable difference (as fraction, e.g., 0.01 = 1%)
        
    Returns:
        True if valid, False otherwise
    """
    actual_sum = sum(values)
    diff = abs(actual_sum - expected_total) / expected_total if expected_total != 0 else float('inf')
    return diff <= tolerance


def validate_csv_structure(csv_path: str, required_columns: List[str]) -> Tuple[bool, List[str]]:
    """
    Validate CSV file structure
    
    Args:
        csv_path: Path to CSV file
        required_columns: List of required column names
        
    Returns:
        Tuple of (is_valid, missing_columns)
    """
    try:
        df = pd.read_csv(csv_path, nrows=1)
        missing = [col for col in required_columns if col not in df.columns]
        return len(missing) == 0, missing
    except Exception as e:
        return False, [f"Error reading file: {e}"]


def standardize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardize column names (lowercase, replace spaces with underscores)
    
    Args:
        df: DataFrame
        
    Returns:
        DataFrame with standardized column names
    """
    df.columns = df.columns.str.lower().str.replace(' ', '_').str.replace('[^a-z0-9_]', '', regex=True)
    return df


def remove_duplicates(df: pd.DataFrame, subset: Optional[List[str]] = None, keep: str = 'first') -> pd.DataFrame:
    """
    Remove duplicate rows
    
    Args:
        df: DataFrame
        subset: Columns to consider for identifying duplicates
        keep: Which duplicates to keep ('first', 'last', False)
        
    Returns:
        DataFrame with duplicates removed
    """
    before_count = len(df)
    df_cleaned = df.drop_duplicates(subset=subset, keep=keep)
    after_count = len(df_cleaned)
    
    if before_count > after_count:
        print(f"Removed {before_count - after_count} duplicate rows")
        
    return df_cleaned


if __name__ == "__main__":
    # Test the utilities
    print("Data Validation Utilities - Ready")
    print("Usage: Import this module in agent scripts")
    
    # Example tests
    print("\nTest validate_numeric_value:")
    print(validate_numeric_value("1,234.56"))  # (True, 1234.56)
    print(validate_numeric_value("abc"))  # (False, None)
    
    print("\nTest validate_percentage:")
    print(validate_percentage("35.8"))  # (True, 35.8)
    print(validate_percentage("150"))  # (False, None)
