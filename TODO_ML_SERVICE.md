# ML Service TODO List

## Overview
The ML Service (`app/services/ml_service.py`) has placeholder implementations that need to be replaced with real ML functionality. This document outlines all issues and provides detailed notes for future implementation.

## Critical Issues

### 1. Pattern Recognition Methods (Lines 562-588)
**Status:** ❌ Placeholder implementations
**Files:** `app/services/ml_service.py`

#### Issues:
- `_detect_peak_traffic_patterns()` - Returns hardcoded patterns
- `_detect_workload_patterns()` - Returns hardcoded patterns  
- `_detect_sector_correlations()` - Returns hardcoded patterns

#### Current Implementation:
```python
async def _detect_peak_traffic_patterns(self, db: Session) -> List[PatternRecognition]:
    return [
        PatternRecognition(
            pattern_type="peak_traffic",
            sector_name="General",
            confidence=0.7,
            description="Peak traffic typically occurs between 14:00-18:00 UTC",
            historical_frequency=0.8
        )
    ]
```

#### What Needs Implementation:
- Analyze historical traffic data from `Flight` table
- Use time-series analysis to identify actual peak hours
- Calculate confidence based on data consistency
- Detect patterns per sector, not just "General"
- Use statistical methods (Fourier analysis, clustering) for pattern detection

#### Implementation Notes:
```python
# Pseudo-code for real implementation:
async def _detect_peak_traffic_patterns(self, db: Session) -> List[PatternRecognition]:
    # Query historical flight data
    flights = db.query(Flight).filter(
        Flight.last_updated >= datetime.utcnow() - timedelta(days=30)
    ).all()
    
    # Group by hour and sector
    hourly_data = defaultdict(lambda: defaultdict(int))
    for flight in flights:
        hour = flight.last_updated.hour
        sector = flight.sector_id
        hourly_data[sector][hour] += 1
    
    # Analyze patterns using statistical methods
    patterns = []
    for sector_id, hourly_counts in hourly_data.items():
        # Find peak hours using statistical analysis
        peak_hours = self._find_peak_hours(hourly_counts)
        confidence = self._calculate_pattern_confidence(hourly_counts)
        
        patterns.append(PatternRecognition(
            pattern_type="peak_traffic",
            sector_name=sector_id,
            confidence=confidence,
            description=f"Peak traffic at hours: {peak_hours}",
            historical_frequency=self._calculate_frequency(hourly_counts)
        ))
    
    return patterns
```

### 2. Controller Model References (Lines 600-616)
**Status:** ❌ Wrong model references
**Files:** `app/services/ml_service.py`

#### Issues:
- References `Controller` model that doesn't exist
- Should use `ATCPosition` model instead

#### Current Implementation:
```python
controllers = db.query(Controller).filter(Controller.status == "online").all()
```

#### What Needs Fixing:
- Replace `Controller` with `ATCPosition`
- Update field references (`callsign` vs `position_name`)
- Update status field references

#### Implementation Notes:
```python
# Correct implementation:
async def _find_optimal_controller(self, sector: Sector, db: Session) -> Optional[str]:
    """Find optimal controller for a sector."""
    # Use ATCPosition instead of Controller
    atc_positions = db.query(ATCPosition).filter(
        ATCPosition.status == "online"
    ).all()
    
    if not atc_positions:
        return None
    
    # Find controller with lowest workload
    optimal_controller = min(atc_positions, key=lambda c: c.workload_score or 0)
    return optimal_controller.position_name  # Use position_name instead of callsign
```

### 3. Simple Heuristics Instead of ML (Lines 629-659)
**Status:** ❌ Basic if/else logic instead of ML
**Files:** `app/services/ml_service.py`

#### Issues:
- `_calculate_efficiency_score()` - Uses simple if/else
- `_generate_optimization_recommendations()` - Uses simple rules

#### Current Implementation:
```python
async def _calculate_efficiency_score(self, sector: Sector, controller: str, db: Session) -> float:
    flight_count = db.query(Flight).filter(Flight.sector_id == sector.id).count()
    
    if flight_count == 0:
        return 0.0
    elif flight_count <= 5:
        return 0.8
    elif flight_count <= 10:
        return 0.6
    else:
        return 0.4
```

#### What Needs Implementation:
- Use ML models for efficiency scoring
- Consider multiple factors: flight count, controller experience, sector complexity
- Use historical performance data for training
- Implement regression models for scoring

#### Implementation Notes:
```python
# Pseudo-code for ML-based implementation:
async def _calculate_efficiency_score(self, sector: Sector, controller: str, db: Session) -> float:
    # Collect features for ML model
    features = {
        'flight_count': db.query(Flight).filter(Flight.sector_id == sector.id).count(),
        'controller_experience': self._get_controller_experience(controller, db),
        'sector_complexity': self._calculate_sector_complexity(sector, db),
        'time_of_day': datetime.utcnow().hour,
        'day_of_week': datetime.utcnow().weekday(),
        'weather_conditions': self._get_weather_conditions(sector, db)
    }
    
    # Use trained ML model for prediction
    efficiency_score = self.efficiency_predictor.predict([list(features.values())])[0]
    return max(0.0, min(1.0, efficiency_score))  # Clamp between 0 and 1
```

### 4. Missing Model Training (Lines 726-756)
**Status:** ❌ Incomplete training implementation
**Files:** `app/services/ml_service.py`

#### Issues:
- `_train_pattern_recognizer()` - Not implemented
- Models not properly saved/loaded
- No model validation

#### Current Implementation:
```python
async def _train_pattern_recognizer(self, training_data: List[Dict]):
    if len(training_data) < 10:
        return  # Early return - no training
```

#### What Needs Implementation:
- Implement proper model training
- Add model persistence (save/load)
- Add model validation and performance metrics
- Implement cross-validation

#### Implementation Notes:
```python
# Pseudo-code for complete training implementation:
async def _train_pattern_recognizer(self, training_data: List[Dict]):
    if len(training_data) < 10:
        self.logger.warning("Insufficient training data for pattern recognizer")
        return
    
    # Prepare features and labels
    features = []
    labels = []
    
    for data in training_data:
        feature_vector = [
            data.get('flight_count', 0),
            data.get('avg_altitude', 0),
            data.get('avg_speed', 0),
            data.get('hour', 0),
            data.get('weekday', 0),
            data.get('sector_complexity', 0)
        ]
        features.append(feature_vector)
        labels.append(data.get('pattern_type', 'normal'))
    
    # Split data for training/validation
    X_train, X_val, y_train, y_val = train_test_split(
        features, labels, test_size=0.2, random_state=42
    )
    
    # Train model
    self.pattern_recognizer.fit(X_train, y_train)
    
    # Validate model
    val_score = self.pattern_recognizer.score(X_val, y_val)
    self.logger.info(f"Pattern recognizer validation score: {val_score}")
    
    # Save model
    await self._save_model('pattern_recognizer', self.pattern_recognizer)
```

## Implementation Priority

### High Priority (Critical for ML functionality)
1. **Fix Controller References** - Blocks other functionality
2. **Implement Real Pattern Recognition** - Core ML feature
3. **Add Model Training & Persistence** - Required for ML to work

### Medium Priority (Enhancement)
4. **Replace Heuristics with ML** - Improve accuracy
5. **Add Model Validation** - Ensure quality
6. **Implement Cross-Validation** - Robust training

### Low Priority (Optimization)
7. **Add Performance Metrics** - Monitor ML performance
8. **Implement A/B Testing** - Compare model versions
9. **Add Model Explainability** - Understand predictions

## Technical Requirements

### Dependencies to Add:
```python
# Additional ML libraries needed:
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import cross_val_score
import numpy as np
import pandas as pd
```

### Database Queries Needed:
```sql
-- For pattern recognition
SELECT 
    sector_id,
    EXTRACT(HOUR FROM last_updated) as hour,
    COUNT(*) as flight_count,
    AVG(altitude) as avg_altitude,
    AVG(speed) as avg_speed
FROM flights 
WHERE last_updated >= NOW() - INTERVAL '30 days'
GROUP BY sector_id, EXTRACT(HOUR FROM last_updated);

-- For controller optimization
SELECT 
    position_name,
    status,
    workload_score,
    experience_level
FROM atc_positions 
WHERE status = 'online';
```

### Configuration Updates:
```python
# Add to config.py
@dataclass
class MLConfig:
    # Model parameters
    min_training_data: int = 100
    model_save_path: str = "models/"
    validation_split: float = 0.2
    
    # Pattern recognition
    pattern_confidence_threshold: float = 0.7
    min_pattern_frequency: float = 0.1
    
    # Anomaly detection
    anomaly_threshold: float = 0.8
    isolation_forest_contamination: float = 0.1
```

## Testing Strategy

### Unit Tests Needed:
1. **Pattern Recognition Tests**
   - Test with synthetic traffic data
   - Verify pattern detection accuracy
   - Test edge cases (no data, single data point)

2. **Model Training Tests**
   - Test model saving/loading
   - Test with insufficient data
   - Test model validation

3. **Controller Optimization Tests**
   - Test with no controllers online
   - Test with single controller
   - Test workload distribution calculation

### Integration Tests Needed:
1. **End-to-End ML Pipeline**
   - Data collection → Training → Prediction
   - Verify predictions are reasonable
   - Test error handling

2. **Performance Tests**
   - Test with large datasets
   - Monitor memory usage
   - Test concurrent access

## Monitoring & Logging

### Metrics to Track:
- Model training accuracy
- Prediction confidence scores
- Pattern detection frequency
- Anomaly detection rate
- Model performance over time

### Logging Requirements:
```python
# Add to ML service methods:
self.logger.info(f"Training {model_name} with {len(training_data)} samples")
self.logger.info(f"Model validation score: {score}")
self.logger.warning(f"Low confidence prediction: {confidence}")
self.logger.error(f"Model training failed: {error}")
```

## Future Enhancements

### Advanced ML Features:
1. **Deep Learning Models**
   - LSTM for time-series prediction
   - Neural networks for complex patterns

2. **Real-time Learning**
   - Online model updates
   - Adaptive thresholds

3. **Multi-modal Analysis**
   - Weather data integration
   - Event correlation analysis

### Performance Optimizations:
1. **Model Caching**
   - Cache trained models
   - Cache predictions

2. **Batch Processing**
   - Process multiple sectors simultaneously
   - Async model training

3. **Distributed Training**
   - Multi-GPU training
   - Distributed model serving

## Notes for Implementation

### Data Quality Considerations:
- Handle missing data gracefully
- Validate input data types
- Implement data preprocessing pipelines
- Consider data drift detection

### Model Management:
- Version control for models
- Model rollback capabilities
- A/B testing framework
- Model performance monitoring

### Error Handling:
- Graceful degradation when ML fails
- Fallback to simple heuristics
- Comprehensive error logging
- User-friendly error messages

### Security Considerations:
- Validate all inputs
- Sanitize model outputs
- Implement rate limiting
- Monitor for adversarial inputs

---

**Last Updated:** $(date)
**Status:** Ready for implementation
**Estimated Effort:** 2-3 weeks for complete implementation 