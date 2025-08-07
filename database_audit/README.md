# Database Audit Framework

This directory contains the comprehensive database audit framework for the VATSIM data project.

## 📁 Contents

- **`database_audit_framework.py`** - Main audit engine script
- **`database_audit_config.json`** - Configuration file with audit rules and expected schema
- **`test_audit_framework.py`** - Test script for validating the framework
- **`DATABASE_AUDIT_FRAMEWORK.md`** - Comprehensive documentation
- **`DATABASE_AUDIT_QUICK_REFERENCE.md`** - Quick reference guide

## 🚀 Quick Start

```bash
# Run full audit
python database_audit_framework.py --audit-type=full

# Run schema-only audit
python database_audit_framework.py --audit-type=schema

# Run performance audit
python database_audit_framework.py --audit-type=performance
```

## 📚 Documentation

- **Full Documentation**: See `DATABASE_AUDIT_FRAMEWORK.md`
- **Quick Reference**: See `DATABASE_AUDIT_QUICK_REFERENCE.md`
- **Configuration**: See `database_audit_config.json`

## 🧪 Testing

```bash
# Run the test suite
python test_audit_framework.py
```

## 📊 Output

Audit reports are saved as JSON files and can be generated in various formats:
- JSON reports for machine processing
- Console summaries for human reading
- HTML reports for web viewing

## 🔧 Configuration

The framework is highly configurable through `database_audit_config.json`:
- Expected schema definitions
- Validation rules
- Performance thresholds
- Audit criteria

## 🛠️ Integration

The framework can be integrated into:
- CI/CD pipelines
- Scheduled monitoring
- Development workflows
- Production monitoring

---

**Last Updated**: January 27, 2025  
**Version**: 1.0
