# Database Audit Framework

## 📋 Overview

The Database Audit Framework is a comprehensive, reusable system for validating database schema against configuration files, SQLAlchemy models, and VATSIM API field mappings. It provides automated auditing capabilities to ensure database integrity, performance, and compliance with expected schemas.

## 🎯 Purpose

### **Primary Objectives:**
- **Schema Validation**: Verify database schema matches expected configuration
- **Field Mapping**: Validate VATSIM API field mappings are complete and correct
- **Performance Analysis**: Identify performance bottlenecks and optimization opportunities
- **Data Integrity**: Check for orphaned records, duplicates, and constraint violations
- **Compliance Monitoring**: Ensure database meets operational requirements

### **Audit Types:**

1. **Full Audit** (`--audit-type=full`)
   - Complete schema validation
   - Performance metrics analysis
   - Data integrity checks
   - VATSIM API field mapping validation
   - Index usage analysis
   - Recommendations generation

2. **Schema Audit** (`--audit-type=schema`)
   - Field mapping validation
   - Data type consistency checks
   - Constraint verification
   - Index presence validation
   - Model vs Database comparison

3. **Performance Audit** (`--audit-type=performance`)
   - Index usage statistics
   - Table size analysis
   - Slow query identification
   - Performance recommendations
   - Resource utilization metrics

## 🚀 Usage

### **Basic Usage:**

```bash
# Run full audit
python scripts/database_audit_framework.py --audit-type=full

# Run schema-only audit
python scripts/database_audit_framework.py --audit-type=schema

# Run performance audit
python scripts/database_audit_framework.py --audit-type=performance
```

### **Advanced Usage:**

```bash
# Save report to specific file
python scripts/database_audit_framework.py --audit-type=full --output-file=my_audit_report.json

# Print human-readable summary
python scripts/database_audit_framework.py --audit-type=full --print-summary

# Run with custom configuration
python scripts/database_audit_framework.py --audit-type=full --config-file=custom_config.json
```

### **Docker Environment:**

```bash
# Run audit inside Docker container
docker-compose exec app python scripts/database_audit_framework.py --audit-type=full

# Run with volume mount for output
docker-compose exec app python scripts/database_audit_framework.py --audit-type=full --output-file=/app/audit_reports/latest_audit.json
```

## 📊 Audit Components

### **1. Schema Validation**

**Field Mapping Validation:**
- Compares database fields against SQLAlchemy models
- Validates VATSIM API field mappings
- Checks for missing or extra fields
- Verifies data type consistency

**Example Validation:**
```python
# Expected VATSIM API mapping for controllers
vatsim_api_mapping = {
    "cid": "controller_id",
    "name": "controller_name", 
    "rating": "controller_rating",
    "callsign": "callsign"
}

# Database validation
missing_fields = expected_fields - actual_fields
type_mismatches = compare_data_types(expected, actual)
```

### **2. Performance Analysis**

**Index Usage Analysis:**
```sql
-- Check index usage statistics
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;
```

**Table Size Analysis:**
```sql
-- Check table sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### **3. Data Integrity Checks**

**Orphaned Records Detection:**
```sql
-- Check for flights without controllers
SELECT COUNT(*) as count 
FROM flights f 
LEFT JOIN controllers c ON f.cid = c.controller_id 
WHERE f.cid IS NOT NULL AND c.controller_id IS NULL;
```

**Duplicate Record Detection:**
```sql
-- Check for duplicate callsigns
SELECT COUNT(*) as count 
FROM (
    SELECT callsign, COUNT(*) 
    FROM flights 
    GROUP BY callsign 
    HAVING COUNT(*) > 1
) as duplicates;
```

## ⚙️ Configuration

### **Configuration File Structure:**

The audit framework uses `scripts/database_audit_config.json` for configuration:

```json
{
  "audit_config": {
    "version": "1.0",
    "audit_types": {
      "full": {
        "enabled": true,
        "timeout_seconds": 300
      }
    }
  },
  "expected_schema": {
    "controllers": {
      "required_fields": ["id", "callsign", "facility"],
      "vatsim_api_mapping": {
        "cid": "controller_id",
        "name": "controller_name"
      },
      "indexes": ["idx_controllers_callsign"],
      "constraints": {
        "unique": ["callsign"],
        "not_null": ["callsign", "facility"]
      }
    }
  },
  "validation_rules": {
    "field_mapping": {
      "strict_mode": true,
      "allow_extra_fields": false
    }
  }
}
```

### **Key Configuration Sections:**

1. **`expected_schema`**: Defines expected table structures
2. **`validation_rules`**: Sets validation behavior
3. **`audit_thresholds`**: Defines pass/warn/fail criteria
4. **`performance_metrics`**: Sets performance thresholds
5. **`reporting`**: Configures output format and content

## 📈 Audit Results

### **Status Levels:**

- **PASS** ✅: All validations pass, no issues found
- **WARN** ⚠️: Minor issues detected, recommendations provided
- **FAIL** ❌: Critical issues found, immediate action required

### **Output Formats:**

1. **JSON Report**: Machine-readable audit results
2. **HTML Report**: Human-readable with formatting
3. **Markdown Report**: Documentation-friendly format
4. **Console Summary**: Real-time audit progress

### **Sample Output:**

```json
{
  "audit_timestamp": "2025-01-27T10:30:00",
  "audit_type": "full",
  "database_version": "PostgreSQL 15.0",
  "total_tables": 13,
  "total_fields": 156,
  "total_indexes": 59,
  "overall_status": "pass",
  "table_audits": [
    {
      "table_name": "flights",
      "status": "pass",
      "missing_fields": [],
      "extra_fields": [],
      "type_mismatches": [],
      "index_count": 25,
      "record_count": 15420
    }
  ],
  "recommendations": [
    "Consider adding more indexes to airports table (currently 1)"
  ]
}
```

## 🔧 Customization

### **Adding New Validation Rules:**

1. **Extend Configuration:**
```json
{
  "validation_rules": {
    "custom_checks": {
      "check_flight_completion": true,
      "validate_airport_codes": true
    }
  }
}
```

2. **Implement Custom Validator:**
```python
def custom_flight_completion_check(self, table_audit):
    """Custom validation for flight completion logic"""
    # Implementation here
    pass
```

### **Custom Performance Metrics:**

```python
def custom_performance_check(self):
    """Custom performance analysis"""
    query = """
    SELECT 
        table_name,
        pg_size_pretty(pg_total_relation_size(table_name)) as size
    FROM information_schema.tables
    WHERE table_schema = 'public'
    """
    # Implementation here
    pass
```

## 🛠️ Integration

### **CI/CD Integration:**

```yaml
# GitHub Actions example
- name: Database Audit
  run: |
    python scripts/database_audit_framework.py --audit-type=full
    python scripts/database_audit_framework.py --audit-type=performance
```

### **Scheduled Audits:**

```bash
# Cron job for daily audits
0 2 * * * docker-compose exec app python scripts/database_audit_framework.py --audit-type=full --output-file=/app/audit_reports/daily_$(date +\%Y\%m\%d).json
```

### **Monitoring Integration:**

```python
# Integration with monitoring system
from scripts.database_audit_framework import DatabaseAuditor

with DatabaseAuditor() as auditor:
    result = auditor.run_full_audit()
    if result.overall_status == 'fail':
        # Send alert to monitoring system
        send_alert("Database audit failed", result)
```

## 📋 Maintenance

### **Regular Tasks:**

1. **Update Configuration**: Keep expected schema current
2. **Review Thresholds**: Adjust based on system growth
3. **Monitor Performance**: Track audit execution time
4. **Archive Reports**: Maintain audit history

### **Configuration Updates:**

When database schema changes:

1. Update `expected_schema` in config file
2. Add new validation rules if needed
3. Adjust performance thresholds
4. Test audit with new configuration

### **Troubleshooting:**

**Common Issues:**

1. **Connection Errors**: Check database connectivity
2. **Import Errors**: Verify model imports
3. **Timeout Issues**: Increase timeout in configuration
4. **Memory Issues**: Reduce batch sizes for large tables

**Debug Mode:**

```bash
# Enable debug output
python scripts/database_audit_framework.py --audit-type=full --debug
```

## 📚 Best Practices

### **Audit Frequency:**

- **Development**: Run before each deployment
- **Staging**: Run after schema changes
- **Production**: Run weekly or after major changes
- **Emergency**: Run when issues are suspected

### **Report Management:**

- **Archive**: Keep audit reports for 6 months
- **Trend Analysis**: Track performance over time
- **Alerting**: Set up alerts for failed audits
- **Documentation**: Document any manual fixes

### **Performance Optimization:**

- **Batch Processing**: Process large tables in batches
- **Index Optimization**: Focus on frequently queried fields
- **Query Optimization**: Use efficient SQL queries
- **Resource Management**: Monitor memory and CPU usage

## 🔍 Future Enhancements

### **Planned Features:**

1. **Automated Fixes**: Auto-correct minor issues
2. **Trend Analysis**: Historical performance tracking
3. **Custom Validators**: Plugin system for custom checks
4. **Real-time Monitoring**: Continuous audit monitoring
5. **Integration APIs**: REST API for external systems

### **Extensibility:**

The framework is designed to be easily extensible:

- **Plugin Architecture**: Add custom validators
- **Configuration Driven**: Modify behavior via config
- **Modular Design**: Independent audit components
- **API Integration**: Connect to external systems

---

**Last Updated**: January 27, 2025  
**Version**: 1.0  
**Maintainer**: Database Team
