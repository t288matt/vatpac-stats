# Database Audit Framework - Quick Reference

## 🚀 Quick Start

### **Basic Commands:**

```bash
# Full audit (schema + performance + integrity)
python scripts/database_audit_framework.py --audit-type=full

# Schema-only audit
python scripts/database_audit_framework.py --audit-type=schema

# Performance audit
python scripts/database_audit_framework.py --audit-type=performance

# With summary output
python scripts/database_audit_framework.py --audit-type=full --print-summary

# Save to specific file
python scripts/database_audit_framework.py --audit-type=full --output-file=audit_report.json
```

### **Docker Environment:**

```bash
# Run inside Docker container
docker-compose exec app python scripts/database_audit_framework.py --audit-type=full

# Save to mounted volume
docker-compose exec app python scripts/database_audit_framework.py --audit-type=full --output-file=/app/audit_reports/latest.json
```

## 📊 Audit Types

| Audit Type | Description | Duration | Use Case |
|------------|-------------|----------|----------|
| `full` | Complete audit (schema + performance + integrity) | ~5 min | Production monitoring, deployment validation |
| `schema` | Field mapping and constraint validation | ~2 min | Development, schema changes |
| `performance` | Index usage and query analysis | ~3 min | Performance optimization |

## 📈 Status Levels

| Status | Meaning | Action Required |
|--------|---------|-----------------|
| **PASS** ✅ | All validations pass | None - system is healthy |
| **WARN** ⚠️ | Minor issues detected | Review recommendations |
| **FAIL** ❌ | Critical issues found | Immediate action required |

## 🔍 What Gets Audited

### **Schema Validation:**
- ✅ Field presence (database vs models vs API)
- ✅ Data type consistency
- ✅ Constraint validation
- ✅ Index presence
- ✅ VATSIM API field mapping

### **Performance Analysis:**
- ✅ Index usage statistics
- ✅ Table sizes and growth
- ✅ Slow query identification
- ✅ Resource utilization
- ✅ Connection pool status

### **Data Integrity:**
- ✅ Orphaned record detection
- ✅ Duplicate record checks
- ✅ Foreign key integrity
- ✅ Constraint violations

## 📋 Common Issues & Solutions

### **Missing Fields:**
```bash
# Check specific table
python scripts/database_audit_framework.py --audit-type=schema | grep "missing_fields"
```

**Solution:** Update database schema or adjust expected fields in config

### **Performance Issues:**
```bash
# Focus on performance
python scripts/database_audit_framework.py --audit-type=performance --print-summary
```

**Common Fixes:**
- Add missing indexes
- Optimize slow queries
- Partition large tables
- Clean up unused indexes

### **Data Integrity Issues:**
```bash
# Check for orphaned records
python scripts/database_audit_framework.py --audit-type=full | grep "orphaned"
```

**Solutions:**
- Clean up orphaned records
- Fix foreign key relationships
- Update data migration scripts

## ⚙️ Configuration

### **Key Configuration File:** `scripts/database_audit_config.json`

**Important Sections:**
- `expected_schema`: Define expected table structures
- `validation_rules`: Set validation behavior
- `audit_thresholds`: Define pass/warn/fail criteria
- `performance_metrics`: Set performance thresholds

### **Customizing Validation:**

```json
{
  "validation_rules": {
    "field_mapping": {
      "strict_mode": true,
      "allow_extra_fields": false
    },
    "performance": {
      "max_table_size_mb": 1000,
      "max_slow_query_time_ms": 1000
    }
  }
}
```

## 📊 Output Examples

### **JSON Report Structure:**
```json
{
  "audit_timestamp": "2025-01-27T10:30:00",
  "audit_type": "full",
  "overall_status": "pass",
  "total_tables": 13,
  "total_fields": 156,
  "total_indexes": 59,
  "table_audits": [...],
  "performance_metrics": {...},
  "recommendations": [...]
}
```

### **Console Summary:**
```
🔍 DATABASE AUDIT SUMMARY
============================================================
Audit Type: FULL
Timestamp: 2025-01-27T10:30:00
Database Version: PostgreSQL 15.0
Overall Status: PASS
Total Tables: 13
Total Fields: 156
Total Indexes: 59

📊 Table Status Summary:
  PASS: 12 tables
  WARN: 1 tables

💡 Recommendations (2):
  1. Consider adding more indexes to airports table (currently 1)
  2. Monitor table size growth for flights table
============================================================
```

## 🛠️ Integration Examples

### **CI/CD Pipeline:**
```yaml
# GitHub Actions
- name: Database Audit
  run: |
    python scripts/database_audit_framework.py --audit-type=full
    if [ $? -ne 0 ]; then
      echo "Database audit failed"
      exit 1
    fi
```

### **Scheduled Monitoring:**
```bash
# Cron job for daily audits
0 2 * * * docker-compose exec app python scripts/database_audit_framework.py --audit-type=full --output-file=/app/audit_reports/daily_$(date +\%Y\%m\%d).json
```

### **Python Integration:**
```python
from scripts.database_audit_framework import DatabaseAuditor

with DatabaseAuditor() as auditor:
    result = auditor.run_full_audit()
    if result.overall_status == 'fail':
        # Send alert
        send_alert("Database audit failed", result)
```

## 🔧 Troubleshooting

### **Common Errors:**

1. **Connection Error:**
   ```bash
   # Check database connectivity
   docker-compose exec app python -c "from app.database import SessionLocal; SessionLocal()"
   ```

2. **Import Error:**
   ```bash
   # Check Python path
   python -c "import sys; print(sys.path)"
   ```

3. **Timeout Error:**
   ```bash
   # Increase timeout in config
   # "timeout_seconds": 600
   ```

### **Debug Mode:**
```bash
# Enable verbose output
python scripts/database_audit_framework.py --audit-type=full --debug
```

## 📚 Best Practices

### **Audit Frequency:**
- **Development**: Before each deployment
- **Staging**: After schema changes
- **Production**: Weekly or after major changes
- **Emergency**: When issues suspected

### **Report Management:**
- Archive reports for 6 months
- Track performance trends
- Set up alerts for failures
- Document manual fixes

### **Performance Tips:**
- Run audits during low-traffic periods
- Use schema-only audits for quick checks
- Monitor audit execution time
- Clean up old reports regularly

## 🎯 Quick Commands Reference

| Command | Purpose | Output |
|---------|---------|--------|
| `--audit-type=full` | Complete audit | JSON report + summary |
| `--audit-type=schema` | Schema validation | Field mapping results |
| `--audit-type=performance` | Performance analysis | Index usage + recommendations |
| `--print-summary` | Human-readable output | Console summary |
| `--output-file=file.json` | Save to file | JSON report file |
| `--help` | Show help | Usage information |

## 📞 Support

**Documentation:** `docs/DATABASE_AUDIT_FRAMEWORK.md`  
**Configuration:** `scripts/database_audit_config.json`  
**Test Script:** `scripts/test_audit_framework.py`  
**Main Framework:** `scripts/database_audit_framework.py`

---

**Last Updated:** January 27, 2025  
**Version:** 1.0
