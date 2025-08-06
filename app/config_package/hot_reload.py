#!/usr/bin/env python3
"""
Configuration Hot-Reload for VATSIM Data Collection System

This module provides dynamic configuration reloading capabilities
to update configuration without restarting the application.
"""

import os
import asyncio
import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timezone
from pathlib import Path
import json

from ..utils.logging import get_logger_for_module
from ..utils.error_handling import handle_service_errors, log_operation
from .database import DatabaseConfig
from .vatsim import VATSIMConfig
from .service import ServiceConfig


class ConfigHotReload:
    """Configuration hot-reload manager."""
    
    def __init__(self):
        self.logger = get_logger_for_module(__name__)
        self.watchers: Dict[str, Callable] = {}
        self.config_files: Dict[str, Path] = {}
        self.last_modified: Dict[str, float] = {}
        self.reload_task: Optional[asyncio.Task] = None
        self.running = False
    
    @handle_service_errors
    @log_operation("register_config_watcher")
    async def register_config_watcher(self, config_name: str, config_file: str, 
                                    reload_callback: Callable) -> bool:
        """Register a configuration file watcher."""
        try:
            config_path = Path(config_file)
            if not config_path.exists():
                self.logger.warning(f"Config file {config_file} does not exist")
                return False
            
            self.config_files[config_name] = config_path
            self.watchers[config_name] = reload_callback
            self.last_modified[config_name] = config_path.stat().st_mtime
            
            self.logger.info(f"Registered config watcher for {config_name}: {config_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register config watcher for {config_name}: {e}")
            return False
    
    @handle_service_errors
    @log_operation("start_config_monitoring")
    async def start_config_monitoring(self, interval: int = 30) -> bool:
        """Start configuration file monitoring."""
        try:
            self.running = True
            self.reload_task = asyncio.create_task(self._config_monitoring_loop(interval))
            self.logger.info(f"Started config monitoring with {interval}s interval")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start config monitoring: {e}")
            return False
    
    @handle_service_errors
    @log_operation("stop_config_monitoring")
    async def stop_config_monitoring(self) -> bool:
        """Stop configuration file monitoring."""
        try:
            self.running = False
            if self.reload_task:
                self.reload_task.cancel()
                try:
                    await self.reload_task
                except asyncio.CancelledError:
                    pass
            self.logger.info("Stopped config monitoring")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop config monitoring: {e}")
            return False
    
    async def _config_monitoring_loop(self, interval: int) -> None:
        """Background loop for configuration file monitoring."""
        while self.running:
            try:
                await self._check_config_files()
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in config monitoring loop: {e}")
                await asyncio.sleep(interval)
    
    async def _check_config_files(self) -> None:
        """Check all monitored configuration files for changes."""
        for config_name, config_path in self.config_files.items():
            try:
                if not config_path.exists():
                    self.logger.warning(f"Config file {config_path} no longer exists")
                    continue
                
                current_mtime = config_path.stat().st_mtime
                last_mtime = self.last_modified.get(config_name, 0)
                
                if current_mtime > last_mtime:
                    self.logger.info(f"Config file {config_name} has changed, triggering reload")
                    await self._reload_config(config_name, config_path)
                    self.last_modified[config_name] = current_mtime
                    
            except Exception as e:
                self.logger.error(f"Error checking config file {config_name}: {e}")
    
    async def _reload_config(self, config_name: str, config_path: Path) -> None:
        """Reload a specific configuration."""
        try:
            callback = self.watchers.get(config_name)
            if callback is None:
                self.logger.warning(f"No callback registered for config {config_name}")
                return
            
            # Execute the reload callback
            if asyncio.iscoroutinefunction(callback):
                await callback(config_path)
            else:
                callback(config_path)
            
            self.logger.info(f"Successfully reloaded config {config_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to reload config {config_name}: {e}")
    
    @handle_service_errors
    @log_operation("reload_database_config")
    async def reload_database_config(self, config_path: Path) -> bool:
        """Reload database configuration."""
        try:
            # Update environment variables from config file
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config_data = json.load(f)
                
                for key, value in config_data.items():
                    os.environ[f"DATABASE_{key.upper()}"] = str(value)
            
            self.logger.info("Database configuration reloaded")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to reload database config: {e}")
            return False
    
    @handle_service_errors
    @log_operation("reload_vatsim_config")
    async def reload_vatsim_config(self, config_path: Path) -> bool:
        """Reload VATSIM configuration."""
        try:
            # Update environment variables from config file
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config_data = json.load(f)
                
                for key, value in config_data.items():
                    os.environ[f"VATSIM_{key.upper()}"] = str(value)
            
            self.logger.info("VATSIM configuration reloaded")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to reload VATSIM config: {e}")
            return False
    
    @handle_service_errors
    @log_operation("reload_service_config")
    async def reload_service_config(self, config_path: Path) -> bool:
        """Reload service configuration."""
        try:
            # Update environment variables from config file
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config_data = json.load(f)
                
                for key, value in config_data.items():
                    os.environ[f"SERVICE_{key.upper()}"] = str(value)
            
            self.logger.info("Service configuration reloaded")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to reload service config: {e}")
            return False
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get configuration monitoring status."""
        return {
            "running": self.running,
            "monitored_configs": list(self.config_files.keys()),
            "config_files": {
                name: str(path) for name, path in self.config_files.items()
            },
            "last_modified": {
                name: datetime.fromtimestamp(mtime, timezone.utc).isoformat()
                for name, mtime in self.last_modified.items()
            }
        }


# Global config hot-reload instance
_config_hot_reload: Optional[ConfigHotReload] = None


async def get_config_hot_reload() -> ConfigHotReload:
    """Get the global config hot-reload instance."""
    global _config_hot_reload
    if _config_hot_reload is None:
        _config_hot_reload = ConfigHotReload()
    return _config_hot_reload


async def start_config_monitoring() -> bool:
    """Start configuration monitoring."""
    config_hot_reload = await get_config_hot_reload()
    return await config_hot_reload.start_config_monitoring()


async def stop_config_monitoring() -> bool:
    """Stop configuration monitoring."""
    config_hot_reload = await get_config_hot_reload()
    return await config_hot_reload.stop_config_monitoring() 