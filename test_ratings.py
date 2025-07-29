#!/usr/bin/env python3
"""
Test script for VATSIM rating system
"""

from app.utils.rating_utils import (
    get_all_ratings, 
    get_rating_name, 
    get_rating_level, 
    validate_rating,
    is_valid_rating
)

def test_rating_system():
    """Test the complete rating system"""
    print("🧪 Testing VATSIM Rating System")
    print("=" * 50)
    
    # Test 1: Get all ratings
    print("\n1. All Available Ratings:")
    ratings = get_all_ratings()
    for rating_num, rating_name in ratings.items():
        print(f"   Rating {rating_num}: {rating_name}")
    
    # Test 2: Test known ratings
    print("\n2. Known Ratings:")
    known_ratings = [1, 2, 3, 4, 5, 8, 10, 11]
    for rating in known_ratings:
        name = get_rating_name(rating)
        level = get_rating_level(rating)
        print(f"   Rating {rating}: {name} ({level})")
    
    # Test 3: Test unknown ratings
    print("\n3. Unknown Ratings:")
    unknown_ratings = [6, 7, 9, 12, 13, 14, 15]
    for rating in unknown_ratings:
        name = get_rating_name(rating)
        level = get_rating_level(rating)
        print(f"   Rating {rating}: {name} ({level})")
    
    # Test 4: Test validation
    print("\n4. Rating Validation:")
    test_ratings = [1, 5, 9, 15, 20, None, "invalid"]
    for rating in test_ratings:
        validation = validate_rating(rating)
        print(f"   Rating {rating}: {validation}")
    
    # Test 5: Test edge cases
    print("\n5. Edge Cases:")
    edge_cases = [0, 16, -1, 1.5, "", [], {}]
    for case in edge_cases:
        try:
            validation = validate_rating(case)
            print(f"   Case {case}: {validation}")
        except Exception as e:
            print(f"   Case {case}: Error - {e}")
    
    print("\n✅ Rating system test completed!")

if __name__ == "__main__":
    test_rating_system() 