#!/usr/bin/env python3
"""
Error Monitoring API Endpoints for VATSIM Data Collection System

This module provides REST API endpoints for accessing error monitoring
data, statistics, and reports.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from ..utils.error_monitoring import get_error_monitor, get_error_reporter
from ..utils.error_handling import get_error_summary
from ..utils.logging import get_logger_for_module

logger = get_logger_for_module(__name__)

router = APIRouter(prefix="/api/errors", tags=["error_monitoring"])


@router.get("/summary")
async def get_error_summary_endpoint() -> Dict[str, Any]:
    """
    Get current error summary.
    
    Returns:
        Dict containing error summary statistics
    """
    try:
        monitor = get_error_monitor()
        summary = get_error_summary()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "error_summary": summary,
            "service_health": monitor.get_service_health(),
            "recent_statistics": monitor.get_error_statistics(timedelta(hours=1))
        }
    except Exception as e:
        logger.error(f"Error getting error summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to get error summary")


@router.get("/statistics")
async def get_error_statistics(
    hours: int = 1
) -> Dict[str, Any]:
    """
    Get error statistics for the specified time window.
    
    Args:
        hours: Number of hours to analyze (default: 1)
    
    Returns:
        Dict containing error statistics
    """
    try:
        monitor = get_error_monitor()
        time_window = timedelta(hours=hours)
        stats = monitor.get_error_statistics(time_window)
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "time_window_hours": hours,
            "statistics": stats
        }
    except Exception as e:
        logger.error(f"Error getting error statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get error statistics")


@router.get("/trends")
async def get_error_trends(
    hours: int = 24
) -> Dict[str, Any]:
    """
    Get error trends over the specified time period.
    
    Args:
        hours: Number of hours to analyze (default: 24)
    
    Returns:
        Dict containing error trends
    """
    try:
        monitor = get_error_monitor()
        trends = monitor.get_error_trends(hours)
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "analysis_period_hours": hours,
            "trends": trends
        }
    except Exception as e:
        logger.error(f"Error getting error trends: {e}")
        raise HTTPException(status_code=500, detail="Failed to get error trends")


@router.get("/service/{service_name}")
async def get_service_error_report(service_name: str) -> Dict[str, Any]:
    """
    Get detailed error report for a specific service.
    
    Args:
        service_name: Name of the service to analyze
    
    Returns:
        Dict containing service-specific error report
    """
    try:
        reporter = get_error_reporter()
        report = await reporter.generate_service_report(service_name)
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "service_report": report
        }
    except Exception as e:
        logger.error(f"Error getting service error report for {service_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get error report for {service_name}")


@router.get("/daily-report")
async def get_daily_error_report() -> Dict[str, Any]:
    """
    Get comprehensive daily error report.
    
    Returns:
        Dict containing daily error report with recommendations
    """
    try:
        reporter = get_error_reporter()
        report = await reporter.generate_daily_report()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "daily_report": report
        }
    except Exception as e:
        logger.error(f"Error generating daily error report: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate daily error report")


@router.get("/health")
async def get_error_monitoring_health() -> Dict[str, Any]:
    """
    Get health status of error monitoring system.
    
    Returns:
        Dict containing monitoring system health
    """
    try:
        monitor = get_error_monitor()
        service_health = monitor.get_service_health()
        
        # Calculate overall health
        total_services = len(service_health)
        healthy_services = len([s for s in service_health.values() if s["status"] == "healthy"])
        unhealthy_services = total_services - healthy_services
        
        overall_health = "healthy" if unhealthy_services == 0 else "degraded" if unhealthy_services < total_services else "unhealthy"
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "monitoring_system": "active",
            "overall_health": overall_health,
            "total_services": total_services,
            "healthy_services": healthy_services,
            "unhealthy_services": unhealthy_services,
            "service_health": service_health
        }
    except Exception as e:
        logger.error(f"Error getting monitoring health: {e}")
        raise HTTPException(status_code=500, detail="Failed to get monitoring health")


@router.post("/reset")
async def reset_error_monitoring() -> Dict[str, Any]:
    """
    Reset error monitoring data (admin only).
    
    Returns:
        Dict confirming reset operation
    """
    try:
        monitor = get_error_monitor()
        monitor.reset_monitoring()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Error monitoring data reset successfully",
            "status": "reset"
        }
    except Exception as e:
        logger.error(f"Error resetting monitoring: {e}")
        raise HTTPException(status_code=500, detail="Failed to reset error monitoring")


@router.get("/alerts")
async def get_error_alerts() -> Dict[str, Any]:
    """
    Get current error alerts and notifications.
    
    Returns:
        Dict containing active alerts
    """
    try:
        monitor = get_error_monitor()
        stats = monitor.get_error_statistics(timedelta(minutes=5))
        service_health = monitor.get_service_health()
        
        alerts = []
        
        # Check for error spikes
        if stats["total_errors"] > 10:
            alerts.append({
                "type": "error_spike",
                "severity": "high",
                "message": f"High error rate detected: {stats['total_errors']} errors in 5 minutes",
                "timestamp": datetime.utcnow().isoformat()
            })
        
        # Check for unhealthy services
        unhealthy_services = [name for name, health in service_health.items() 
                            if health["status"] == "unhealthy"]
        if unhealthy_services:
            alerts.append({
                "type": "service_unhealthy",
                "severity": "medium",
                "message": f"Unhealthy services detected: {', '.join(unhealthy_services)}",
                "services": unhealthy_services,
                "timestamp": datetime.utcnow().isoformat()
            })
        
        # Check for specific error type spikes
        for error_type, count in stats["error_types"].items():
            if count > 5:
                alerts.append({
                    "type": "error_type_spike",
                    "severity": "medium",
                    "message": f"High frequency of {error_type} errors: {count} in 5 minutes",
                    "error_type": error_type,
                    "count": count,
                    "timestamp": datetime.utcnow().isoformat()
                })
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "active_alerts": len(alerts),
            "alerts": alerts
        }
    except Exception as e:
        logger.error(f"Error getting error alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to get error alerts") 