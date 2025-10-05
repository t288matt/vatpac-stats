# Machine Learning for Data Integrity Detection

## Training ML Models on the VATSIM System

This guide explains how to train machine learning models to detect database relationship and integrity issues in the VATSIM data collection system.

---

## Overview: ML for Database Integrity

Machine learning can detect relationship and integrity issues between database tables and fields by:

1. **Foreign Key Relationship Detection** - Finding orphaned records and missing relationships
2. **Field Consistency Across Tables** - Detecting format mismatches and value inconsistencies
3. **Cardinality Violations** - Identifying unexpected one-to-many or many-to-many relationships
4. **Data Type & Range Inconsistencies** - Finding mismatched types and precision issues
5. **Temporal Relationship Violations** - Detecting impossible timestamp orderings
6. **Derived Field Validation** - Verifying calculated fields match their formulas

---

## 1. What to Train On

### Training Data Sources from VATSIM System

**A. Historical "Clean" Data:**
- Flights from successful enrichment cycles
- Flight summaries with complete ATC detection
- Sector occupancy records with proper entry/exit timestamps
- Controller sessions with matching transceivers

**B. Features to Extract:**
```python
# Relationship features:
- flights.callsign → flight_summaries.callsign (exists/doesn't exist)
- flights.cid → flight_summaries.cid (matches/differs/null)
- transceivers.entity_id → flights.id (valid foreign key)

# Value pattern features:
- callsign format (uppercase, length, special chars)
- timestamp ordering (logon < entry < exit < completion)
- derived field calculations (controller_time matches percentage)

# Cardinality features:
- flights per callsign count
- sectors per flight count
- transceivers per controller count
```

### Natural Labels from Existing Issues

You already have labeled data from past issues:
- Records from `fix_controller_callsigns_format.sql` migration = bad
- Records from `add_missing_atc_columns.sql` errors = bad
- Records with enrichment status = 'completed' = good
- Orphaned transceivers from past data issues = bad
- Timestamp inconsistencies (thy3pt issues) = bad

---

## 2. Schema-Specific Integrity Issues ML Can Detect

### Foreign Key Relationship Detection

**Schema Context:**
- `transceivers.entity_id` references either `flights.id` or `controllers.id`
- `flight_summaries.callsign` should match `flights.callsign`
- `flight_sector_occupancy.callsign` references `flights.callsign`

**Detectable Issues:**
```sql
-- Orphaned Records:
SELECT * FROM transceivers 
WHERE entity_type='flight' AND entity_id NOT IN (SELECT id FROM flights);

-- Missing Relationships:
SELECT * FROM flight_summaries 
WHERE callsign NOT IN (SELECT callsign FROM flights);

-- Missing Sector Data:
SELECT * FROM flight_summaries fs
LEFT JOIN flight_sector_occupancy fso ON fs.callsign = fso.callsign
WHERE fso.callsign IS NULL;
```

**ML Approach:** Graph Neural Networks (GNNs)
- Train on known-good data relationships
- Flag when record patterns deviate from learned topology
- Detect "bridge" records that should exist but don't

### Field Consistency Across Tables

**Detectable Issues:**

```sql
-- Callsign Format Inconsistencies:
flights.callsign: 'QFA123'
flight_summaries.callsign: 'qfa123'  -- Case mismatch
flight_sector_occupancy.callsign: 'QFA 123'  -- Space added

-- CID Value Mismatches:
flights.cid: 1234567
flight_summaries.cid: NULL  -- Should be populated from flights

-- Timestamp Precision Issues:
flights.logon_time: TIMESTAMP(0)  -- No subseconds
flight_summaries.logon_time: TIMESTAMP(6)  -- Full precision
```

**ML Technique:** Clustering + Anomaly Detection
- Learn expected value distributions per field
- Detect outliers (nulls where there shouldn't be, format variations)
- Identify statistical anomalies in linked fields

### Cardinality Violations

**Expected Cardinalities:**
```
One flight → Many sector occupancy records (1:N)
One flight → One flight summary (1:1)
One callsign → Multiple transceiver entries over time (1:N)
```

**ML-Detected Violations:**
```sql
-- Flight with ZERO sector occupancy records (should have at least one)
SELECT callsign FROM flights 
WHERE callsign NOT IN (SELECT DISTINCT callsign FROM flight_sector_occupancy);

-- Flight with TWO flight summaries (duplicate processing)
SELECT callsign, COUNT(*) FROM flight_summaries 
GROUP BY callsign HAVING COUNT(*) > 1;

-- Callsign with transceivers but NO flight record (orphan data)
SELECT DISTINCT callsign FROM transceivers 
WHERE entity_type='flight' AND callsign NOT IN (SELECT callsign FROM flights);
```

**ML Method:** Association Rule Learning
- Mine patterns like: "IF flights.callsign EXISTS THEN flight_summaries.callsign EXISTS"
- Detect violations with high confidence scores
- Learn cardinality constraints from data patterns

### Data Type & Range Inconsistencies

**Examples from VATSIM Schema:**

```sql
-- Field Type Mismatches:
flights.altitude: INTEGER (feet)
flight_sector_occupancy.entry_altitude: INTEGER (feet)
-- ✓ Consistent

flights.groundspeed: INTEGER (knots)
flight_summaries.avg_groundspeed: FLOAT  -- Type change, okay
flight_summaries.max_groundspeed: INTEGER  -- Inconsistent precision

flights.latitude: DOUBLE PRECISION
flight_sector_occupancy.entry_lat: DECIMAL(10,8)  -- Different precision!
```

**Missing Columns Detected:**
```sql
-- Migration: add_missing_atc_columns.sql shows these were added after the fact
-- ML would have detected: "Code calculates total_controller_time_minutes but column doesn't exist"
total_controller_time_minutes  -- Added retroactively
interactions_detected  -- Added retroactively
```

**ML Technique:** Schema Embedding Models
- Represent each field as a vector (type, range, nullability, relationships)
- Learn field "neighborhoods" (similar fields cluster together)
- Flag fields that should be similar but aren't

### Temporal Relationship Violations

**Expected Temporal Order:**
```sql
flights.logon_time < 
  flight_sector_occupancy.entry_timestamp < 
  flight_sector_occupancy.exit_timestamp < 
  flight_summaries.created_at
```

**ML-Detected Violations:**
```sql
-- Impossible timestamp orderings
SELECT * FROM flight_summaries fs
JOIN flight_sector_occupancy fso ON fs.callsign = fso.callsign
WHERE fs.created_at < fso.entry_timestamp;

-- Exit before entry
SELECT * FROM flight_sector_occupancy
WHERE exit_timestamp < entry_timestamp;

-- Mismatched logon times
SELECT f.callsign, f.logon_time, fs.logon_time
FROM flights f
JOIN flight_summaries fs ON f.callsign = fs.callsign
WHERE f.logon_time != fs.logon_time;
```

**ML Approach:** Temporal Pattern Mining
- Learn event sequences from clean data
- Detect impossible orderings
- Flag timestamp inconsistencies

### Derived Field Validation

**VATSIM Schema's Calculated Fields:**

```sql
-- From add_missing_atc_columns.sql migration:
total_controller_time_minutes = 
  ROUND(controller_time_percentage * time_online_minutes / 100)

interactions_detected = 
  jsonb_array_length(controller_callsigns)
```

**ML Can Verify:**
```python
# Learn the formula from existing data
# Then detect when it doesn't hold:
if total_controller_time_minutes != round(controller_time_percentage * time_online_minutes / 100):
    flag_integrity_issue()

# Detect when JSON array length doesn't match count
if interactions_detected != len(controller_callsigns):
    flag_inconsistency()
```

**ML Method:** Invariant Detection via Daikon or Custom Models
- Automatically discover mathematical relationships between fields
- Flag violations of learned invariants
- No manual specification required

---

## 3. Practical Implementation Plan

### Phase 1: Data Collection & Labeling

**Step 1: Export Training Data**

From PostgreSQL database, extract known-good and known-bad examples:

```python
# Run inside Docker container
# Extract features from your database

# Known-Good Examples (Label: 0):
- Flights with complete enrichment (status='completed')
- Matching records across flights/summaries/sectors
- Proper timestamp ordering
- Valid foreign key relationships

# Known-Bad Examples (Label: 1):
- Orphaned transceivers (from past data issues)
- Missing flight summaries (enrichment failures)
- Timestamp inconsistencies (thy3pt issues fixed)
- Mismatched callsigns (controller_callsigns format issues)
```

**Step 2: Label Your Data**

Natural labels already exist from your issues:
- Records from migrations like `fix_controller_callsigns_format.sql` = bad
- Records from `add_missing_atc_columns.sql` errors = bad
- Successful enrichment records = good

### Phase 2: Model Selection

**Three Model Types for Your Use Case:**

#### A. Isolation Forest (Recommended First)
- **Best for:** Detecting outliers in field relationships
- **Training time:** Minutes on your dataset
- **Why:** No labels needed (unsupervised)
- **Library:** scikit-learn (already common)
- **Complexity:** Low

#### B. Random Forest Classifier
- **Best for:** Predicting if a record has integrity issues
- **Training time:** 5-10 minutes
- **Why:** Interpretable (shows which features cause problems)
- **Library:** scikit-learn
- **Complexity:** Medium

#### C. AutoEncoder Neural Network
- **Best for:** Learning normal data patterns
- **Training time:** 30-60 minutes
- **Why:** Good for complex multi-table relationships
- **Library:** TensorFlow/PyTorch
- **Complexity:** High

**Recommendation:** Start with A, progress to B if needed, skip C unless necessary.

### Phase 3: Training Environment Setup

**Docker Environment Configuration:**

Add to `docker-compose.yml`:

```yaml
services:
  # Existing services...
  
  ml_trainer:
    build:
      context: .
      dockerfile: Dockerfile.ml  # New lightweight ML container
    volumes:
      - ./ml_models:/app/models
      - ./ml_training:/app/training
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - TRAINING_SAMPLE_SIZE=10000
    depends_on:
      - postgres
```

**Dependencies to Add to `requirements.txt`:**
```
scikit-learn==1.3.0
pandas==2.0.3
numpy==1.24.3
joblib==1.3.2  # For model persistence
psycopg2-binary==2.9.7  # Already have
```

### Phase 4: Training Script Structure

**High-Level Flow:**

```python
# 1. Connect to PostgreSQL database
# 2. Extract feature vectors from tables
# 3. Split into train/validation sets
# 4. Train model
# 5. Evaluate performance
# 6. Save model to disk
# 7. Deploy for inference

# Training Data Query Example:
# - Join flights + flight_summaries + flight_sector_occupancy
# - Extract timestamps, IDs, counts, nullability patterns
# - Create feature vectors (numeric representation)
# - Label based on known issues (optional for unsupervised)
```

**Feature Engineering Example:**

```python
# For each flight record, create feature vector:
features = [
    has_summary,                        # 0/1
    has_sectors,                        # 0/1
    callsign_matches,                   # 0/1
    cid_matches,                        # 0/1
    timestamp_order_valid,              # 0/1
    controller_time_calculated_matches, # 0/1
    interactions_count_matches,         # 0/1
    sector_count,                       # integer
    transceiver_count,                  # integer
    duration_minutes,                   # float
    # ... (20-50 features total)
]
```

### Phase 5: Actual Training Process

**Timeline on VATSIM System:**

```
Step 1: Data extraction from Postgres:      ~5 minutes
Step 2: Feature engineering:                 ~2 minutes
Step 3: Model training (Isolation Forest):   ~1-3 minutes
Step 4: Validation:                          ~1 minute
Step 5: Save model:                          ~5 seconds

Total: ~10-15 minutes for first model
```

**Training Frequency:**
```
Initial training: Once on historical data
Retraining: Weekly or monthly as you collect more data
Incremental: Update with new failure patterns as discovered
```

### Phase 6: Inference (Using the Trained Model)

**Runtime Integration:**

```
When: After enrichment, before committing flight_summaries
Where: New validation step in your data pipeline
How: Load model → Pass record features → Get integrity score

If score > threshold:
  - Flag for manual review
  - Log to monitoring
  - Don't commit (or commit with warning flag)
```

**Integration Point:**
```python
# In enrichment pipeline, after processing but before commit:
integrity_score = ml_model.predict(flight_features)
if integrity_score < threshold:
    logger.warning(f"Integrity issue detected for {callsign}")
    # Handle accordingly
```

---

## 4. Decision Analysis: Should You Train ML?

### Arguments FOR Training ML

✓ **Significant historical data** - Thousands of flights with various patterns
✓ **Recurring integrity issues** - Callsigns, timestamps, missing columns
✓ **Pattern complexity** - Multi-table relationships across 5+ tables
✓ **Ongoing data collection** - Continuous benefit from trained model
✓ **Automated detection** - Catch issues before they cause problems

### Arguments AGAINST

✗ **Added complexity to maintain** - ML models require versioning, monitoring
✗ **Docker environment overhead** - Additional dependencies and resources
✗ **May be overkill** - Deterministic checks might catch 95% of issues
✗ **Rule-based validation** - Often simpler and more maintainable
✗ **Explainability** - Rules are easier to understand than ML predictions

---

## 5. Recommended Hybrid Approach

### Option A: Statistical Anomaly Detection (No Training Required)

**Concept:**
```python
# Calculate statistics from clean data:
- Mean/std of controller_time_percentage per sector
- Expected transceiver count ranges per entity_type
- Valid callsign format patterns (regex)
- Timestamp delta distributions

# At runtime, flag outliers:
- Values > 3 standard deviations from mean
- Patterns that don't match regex
- Timestamps outside expected ranges
```

**Advantages:**
- No training phase needed
- No model files to version
- Transparent and explainable
- Easy to update thresholds
- Simpler to maintain

**Implementation Effort:** Low (1-2 days)

### Option B: Great Expectations Framework

Pre-built data quality framework with built-in anomaly detection:

```python
# Install in Docker container
pip install great-expectations

# Define expectations (no training needed):
expect_column_values_to_be_in_set('entity_type', ['flight', 'atc'])
expect_column_pair_values_to_be_equal('flights.callsign', 'summaries.callsign')
expect_compound_columns_to_be_unique(['callsign', 'entry_timestamp'])

# Run validation automatically
# Built-in ML for learning value distributions
```

**Advantages:**
- 80% of ML benefits without custom training
- Well-documented framework
- Active community support
- Built-in profiling and documentation

**Implementation Effort:** Low-Medium (2-3 days)

### Option C: Custom ML Training (Full Implementation)

Build custom Isolation Forest or Random Forest model:

**Advantages:**
- Tailored to your specific patterns
- Can detect complex multi-feature anomalies
- Adaptable as patterns change

**Disadvantages:**
- Higher complexity
- Requires ongoing maintenance
- Model versioning needed
- More infrastructure

**Implementation Effort:** High (1-2 weeks)

---

## 6. Recommended Path Forward

### Phase 1: Start Simple (Recommended)

1. **Implement rule-based validation** for known issues:
   - Foreign key checks
   - Timestamp ordering validation
   - Derived field formula verification
   - Callsign format validation

2. **Add statistical thresholds** for outlier detection:
   - Field value ranges (from percentiles)
   - Record count expectations
   - Time delta bounds

### Phase 2: Evaluate Results

After 1-2 weeks of running Phase 1:
- Measure false positive rate
- Track issues caught vs missed
- Assess maintenance burden

### Phase 3: Decide on ML

If Phase 1 catches <90% of issues:
- Implement Great Expectations framework
- Or build custom Isolation Forest model

If Phase 1 catches >90% of issues:
- Continue with rule-based approach
- Add more rules as new patterns emerge

---

## 7. Example Implementation Snippets

### Rule-Based Validation

```python
def validate_flight_integrity(flight_id):
    """
    Rule-based integrity checks for a flight record.
    Returns list of integrity issues found.
    """
    issues = []
    
    # Check 1: Flight should have summary
    if not flight_has_summary(flight_id):
        issues.append("Missing flight_summary record")
    
    # Check 2: Callsign format
    callsign = get_flight_callsign(flight_id)
    if not re.match(r'^[A-Z]{3}\d{1,4}[A-Z]?$', callsign):
        issues.append(f"Invalid callsign format: {callsign}")
    
    # Check 3: Timestamp ordering
    logon, entry, exit, completion = get_flight_timestamps(flight_id)
    if not (logon < entry < exit < completion):
        issues.append("Invalid timestamp ordering")
    
    # Check 4: Derived field verification
    summary = get_flight_summary(flight_id)
    expected_time = round(summary.controller_time_percentage * summary.time_online_minutes / 100)
    if summary.total_controller_time_minutes != expected_time:
        issues.append(f"Controller time mismatch: {summary.total_controller_time_minutes} != {expected_time}")
    
    return issues
```

### Statistical Anomaly Detection

```python
import numpy as np
from scipy import stats

def detect_statistical_anomalies(flight_data, historical_stats):
    """
    Detect anomalies using z-scores from historical data.
    """
    anomalies = []
    
    # Check controller_time_percentage
    z_score = stats.zscore([flight_data.controller_time_percentage], 
                           historical_stats.controller_time_mean,
                           historical_stats.controller_time_std)
    if abs(z_score) > 3:
        anomalies.append(f"Unusual controller_time_percentage: {flight_data.controller_time_percentage}")
    
    # Check sector count
    if flight_data.total_enroute_sectors not in range(
        historical_stats.sector_count_min, 
        historical_stats.sector_count_max
    ):
        anomalies.append(f"Unusual sector count: {flight_data.total_enroute_sectors}")
    
    return anomalies
```

### Simple ML with Isolation Forest

```python
from sklearn.ensemble import IsolationForest
import joblib

def train_isolation_forest(training_data):
    """
    Train Isolation Forest on historical clean data.
    """
    # Extract features
    X = extract_features(training_data)
    
    # Train model (contamination=0.1 means expect 10% anomalies)
    model = IsolationForest(contamination=0.1, random_state=42)
    model.fit(X)
    
    # Save model
    joblib.dump(model, 'models/integrity_checker.pkl')
    
    return model

def predict_integrity_issues(flight_data, model_path='models/integrity_checker.pkl'):
    """
    Use trained model to detect integrity issues.
    Returns: 1 for normal, -1 for anomaly
    """
    model = joblib.load(model_path)
    features = extract_features([flight_data])
    prediction = model.predict(features)
    return prediction[0]
```

---

## 8. Success Metrics

### Validation Metrics

**Precision:** Of flagged issues, how many are real problems?
- Target: >80%
- Low precision = too many false alarms

**Recall:** Of actual problems, how many did we catch?
- Target: >90%
- Low recall = missing real issues

**False Positive Rate:** How often do we flag good records?
- Target: <5%
- High FPR = operational burden

### Operational Metrics

**Detection Latency:** Time from issue occurrence to detection
- Target: <1 hour for real-time checks

**Remediation Time:** Time from detection to fix
- Depends on issue type

**Issue Recurrence:** Do fixed issues stay fixed?
- Target: <5% recurrence

---

## 9. Next Steps

### Immediate Actions

1. **Review existing integrity issues** from migrations and past fixes
2. **Catalog known patterns** of good vs bad data
3. **Decide on approach**: Rule-based, statistical, or full ML

### Implementation Timeline

**Week 1: Assessment**
- Analyze historical data quality issues
- Identify top 10 recurring patterns
- Estimate detection complexity

**Week 2-3: Implementation**
- Build rule-based validator
- Add statistical thresholds
- Test on historical data

**Week 4: Deployment**
- Integrate into enrichment pipeline
- Monitor false positive rate
- Tune thresholds

**Week 5+: Iteration**
- Add new rules as patterns emerge
- Consider ML if rule-based insufficient

---

## 10. Conclusion

For the VATSIM data integrity use case:

**Best Approach:** Start with **hybrid rule-based + statistical validation**
- Simpler to implement and maintain
- Covers 90%+ of known issues
- Transparent and debuggable
- Low operational overhead

**Consider ML if:**
- Rule-based approach misses >10% of issues
- New patterns emerge that can't be captured by rules
- You have dedicated time for ML infrastructure

**Avoid full ML if:**
- Current issues are deterministic
- Team lacks ML expertise
- Maintenance burden outweighs benefits
- Explainability is critical

The key principle: **Start simple, add complexity only when needed.**



