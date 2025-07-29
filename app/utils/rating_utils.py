"""
VATSIM Controller Rating Utilities

This module provides utilities for handling VATSIM controller ratings,
including mapping numeric ratings to human-readable names and validation.
"""

from typing import Dict, Optional, Any

# VATSIM Controller Rating Definitions
VATSIM_RATINGS = {
    1: "Observer",
    2: "Student 1", 
    3: "Student 2",
    4: "Student 3", 
    5: "Controller",
    6: "Unknown Rating 6",
    7: "Unknown Rating 7", 
    8: "Senior Controller",
    9: "Unknown Rating 9",
    10: "Instructor",
    11: "Senior Instructor",
    12: "Unknown Rating 12",
    13: "Unknown Rating 13",
    14: "Unknown Rating 14",
    15: "Unknown Rating 15"
}

# Reverse mapping for lookup
RATING_NAMES = {name: rating for rating, name in VATSIM_RATINGS.items()}

def get_rating_name(rating: int) -> Optional[str]:
    """
    Get the human-readable name for a VATSIM controller rating.
    
    Args:
        rating: Numeric rating (1-15)
        
    Returns:
        Rating name or None if invalid
    """
    if rating is None:
        return None
    
    if not isinstance(rating, int):
        raise ValueError(f"Rating must be an integer, got {type(rating)}")
    
    if rating < 1 or rating > 15:
        raise ValueError(f"Rating must be between 1 and 15, got {rating}")
    
    return VATSIM_RATINGS.get(rating, f"Unknown Rating {rating}")

def get_rating_number(name: str) -> Optional[int]:
    """
    Get the numeric rating for a rating name.
    
    Args:
        name: Rating name (e.g., "Controller", "Instructor")
        
    Returns:
        Numeric rating or None if invalid
    """
    return RATING_NAMES.get(name)

def is_valid_rating(rating: int) -> bool:
    """
    Check if a rating is valid.
    
    Args:
        rating: Numeric rating to validate
        
    Returns:
        True if valid, False otherwise
    """
    if rating is None:
        return False
    
    if not isinstance(rating, int):
        return False
    
    return 1 <= rating <= 15

def get_all_ratings() -> Dict[int, str]:
    """
    Get all available VATSIM controller ratings.
    
    Returns:
        Dictionary mapping rating numbers to names
    """
    return VATSIM_RATINGS.copy()

def get_rating_level(rating: int) -> str:
    """
    Get the level category for a rating.
    
    Args:
        rating: Numeric rating (1-15)
        
    Returns:
        Level category: "Student", "Controller", "Senior", "Instructor", or "Unknown"
    """
    if rating is None:
        return "Unknown"
    
    if not isinstance(rating, int):
        return "Unknown"
    
    if rating < 1 or rating > 15:
        return "Unknown"
    
    if rating in [2, 3, 4]:
        return "Student"
    elif rating == 5:
        return "Controller"
    elif rating == 8:
        return "Senior"
    elif rating in [10, 11]:
        return "Instructor"
    elif rating == 1:
        return "Observer"
    else:
        return "Unknown"

def validate_rating(rating: int) -> Dict[str, Any]:
    """
    Validate a rating and return detailed information.
    
    Args:
        rating: Numeric rating to validate
        
    Returns:
        Dictionary with validation results
    """
    result = {
        "is_valid": False,
        "rating": rating,
        "rating_name": None,
        "rating_level": None,
        "error": None
    }
    
    try:
        if rating is None:
            result["error"] = "Rating is None"
            return result
        
        if not isinstance(rating, int):
            result["error"] = f"Rating must be an integer, got {type(rating)}"
            return result
        
        if rating < 1 or rating > 15:
            result["error"] = f"Rating must be between 1 and 15, got {rating}"
            return result
        
        result["is_valid"] = True
        result["rating_name"] = get_rating_name(rating)
        result["rating_level"] = get_rating_level(rating)
        
        return result
        
    except Exception as e:
        result["error"] = f"Unexpected error validating rating: {str(e)}"
        return result 