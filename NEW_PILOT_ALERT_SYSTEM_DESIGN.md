# 🚨 New Australian Pilot Alert System - Push-Based Design

## Overview

Automated push-based system to detect and alert when new Australian pilots complete their first flight with enroute time > 0.

## System Architecture

```
Flight Summaries → Detection Service → Alert Dispatcher → Multiple Channels
                                                         ├─ Webhooks
                                                         ├─ Email
                                                         └─ Discord/Slack
```

## Core Components

### 1. New Pilot Detection Service
- **Purpose**: Monitor `flight_summaries` for new Australian pilots
- **Trigger**: Pilot completes first flight with `total_enroute_time_minutes > 0`
- **Filter**: Australian pilots (name ends with airport code like "YBCG")
- **Frequency**: Check every 5 minutes

### 2. Alert Dispatcher
**Multiple notification channels:**

#### Webhook Notifications
- POST to configured URLs with pilot details
- JSON payload with pilot info and flight details
- Configurable endpoints for external systems

#### Email Alerts
- Send to VATPAC staff/mentors
- Rich email with pilot details and flight summary
- Configurable recipient lists

#### Discord/Slack Integration
- Rich embeds with pilot information
- Channel-specific notifications
- Real-time team communication

### 3. Configuration

```bash
# Core Settings
NEW_PILOT_ALERTS_ENABLED=true
NEW_PILOT_ALERT_INTERVAL=300  # 5 minutes
NEW_PILOT_MIN_ENROUTE_MINUTES=1

# Notification Channels
WEBHOOK_URLS=https://vatpac.org/alerts
ALERT_EMAIL_RECIPIENTS=staff@vatpac.org
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...

# Rate Limiting
MAX_ALERTS_PER_HOUR=50
ALERT_COOLDOWN_MINUTES=60
```

## Detection Logic

**SQL Query**:
```sql
WITH first_appearance AS (
  SELECT cid, MIN(completion_time) as first_completion_time
  FROM flight_summaries 
  WHERE cid IS NOT NULL
    AND LENGTH(name) >= 4 
    AND SUBSTRING(name FROM LENGTH(name) - 3 FOR 1) = 'Y'
    AND total_enroute_time_minutes > 0
  GROUP BY cid
)
SELECT fs.* FROM flight_summaries fs
JOIN first_appearance fa ON fs.cid = fa.cid 
  AND fs.completion_time = fa.first_completion_time
WHERE fs.completion_time >= NOW() - INTERVAL '1 hour'
```

## Alert Data Structure

```json
{
  "alert_type": "new_australian_pilot",
  "timestamp": "2025-01-15T10:30:00Z",
  "pilot": {
    "cid": 1756772,
    "name": "Zane Gowans YBCG",
    "callsign": "QFA20",
    "aircraft_type": "A333",
    "route": "RPLL-YSSY",
    "flight_duration_minutes": 249,
    "enroute_time_minutes": 247,
    "completion_time": "2025-10-18T20:54:52Z"
  },
  "message": "New Australian pilot Zane Gowans YBCG completed first flight QFA20 from RPLL to YSSY"
}
```

## Features

### Rate Limiting & Prevention
- **Duplicate Prevention**: No duplicate alerts for same pilot
- **Cooldown Period**: 60-minute cooldown between alerts
- **Rate Limiting**: Max 50 alerts per hour
- **Backoff Logic**: Reduce frequency during high activity

### Monitoring & Logging
- **Database Logging**: All alerts stored in `new_pilot_alerts` table
- **Delivery Tracking**: Track which channels received alerts
- **Performance Metrics**: Monitor detection accuracy and timing

### Integration
- **Background Service**: Runs continuously with existing FastAPI app
- **Health Checks**: Monitor detection service health
- **Graceful Shutdown**: Proper cleanup on service restart

## Expected Volume

**Based on analysis**:
- **New Australian pilots**: ~45 per day
- **Alert frequency**: ~2 alerts per hour average
- **Peak times**: Higher during Australian evening hours

## Implementation Priority

1. **Phase 1**: Core detection service + webhook notifications
2. **Phase 2**: Email alerts + Discord integration  
3. **Phase 3**: Advanced features + monitoring dashboard
4. **Phase 4**: Machine learning for false positive reduction

## Benefits

- **Real-time Alerts**: Immediate notification of new pilots
- **Automatic Operation**: No manual monitoring required
- **Multi-channel**: Redundant notification methods
- **Scalable**: Handles expected volume efficiently
- **Configurable**: Easy to adjust thresholds and recipients

## Success Metrics

- **Detection Accuracy**: >95% of new Australian pilots detected
- **Alert Delivery**: >99% successful delivery to configured channels
- **False Positive Rate**: <5% alerts for experienced pilots
- **Response Time**: Alerts sent within 10 minutes of flight completion








