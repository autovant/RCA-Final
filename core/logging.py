"""
Structured logging module for RCA Engine.
Provides comprehensive logging with JSON formatting and context.
"""

import logging
import sys
import json
from datetime import datetime
from typing import Any, Dict, Optional
from pythonjsonlogger import jsonlogger
from core.config import settings


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter for structured logging."""
    
    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]):
        """
        Add custom fields to log record.
        
        Args:
            log_record: Log record dictionary
            record: Original log record
            message_dict: Message dictionary
        """
        super().add_fields(log_record, record, message_dict)
        
        # Add timestamp
        log_record['timestamp'] = datetime.utcnow().isoformat()
        
        # Add log level
        log_record['level'] = record.levelname
        
        # Add logger name
        log_record['logger'] = record.name
        
        # Add module and function info
        log_record['module'] = record.module
        log_record['function'] = record.funcName
        log_record['line'] = record.lineno
        
        # Add application info
        log_record['app'] = settings.APP_NAME
        log_record['version'] = settings.APP_VERSION
        log_record['environment'] = settings.ENVIRONMENT
        
        # Add process and thread info
        log_record['process_id'] = record.process
        log_record['thread_id'] = record.thread
        
        # Add exception info if present
        if record.exc_info:
            log_record['exception'] = self.formatException(record.exc_info)


class ContextFilter(logging.Filter):
    """Filter to add contextual information to log records."""
    
    def __init__(self, context: Optional[Dict[str, Any]] = None):
        """
        Initialize context filter.
        
        Args:
            context: Optional context dictionary
        """
        super().__init__()
        self.context = context or {}
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Add context to log record.
        
        Args:
            record: Log record
            
        Returns:
            bool: Always True to allow the record
        """
        for key, value in self.context.items():
            setattr(record, key, value)
        return True


def setup_logging(
    log_level: Optional[str] = None,
    log_format: Optional[str] = None
) -> None:
    """
    Setup logging configuration.
    
    Args:
        log_level: Optional log level override
        log_format: Optional log format override ('json' or 'text')
    """
    level = log_level or settings.LOG_LEVEL
    format_type = log_format or settings.LOG_FORMAT
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))
    
    # Set formatter based on format type
    if format_type.lower() == 'json':
        formatter = CustomJsonFormatter(
            '%(timestamp)s %(level)s %(logger)s %(message)s'
        )
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Set log levels for third-party libraries
    logging.getLogger('uvicorn').setLevel(logging.INFO)
    logging.getLogger('fastapi').setLevel(logging.INFO)
    logging.getLogger('sqlalchemy').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    
    logging.info(f"Logging configured: level={level}, format={format_type}")


def get_logger(name: str, context: Optional[Dict[str, Any]] = None) -> logging.Logger:
    """
    Get a logger with optional context.
    
    Args:
        name: Logger name
        context: Optional context dictionary
        
    Returns:
        logging.Logger: Configured logger
    """
    logger = logging.getLogger(name)
    
    if context:
        context_filter = ContextFilter(context)
        logger.addFilter(context_filter)
    
    return logger


class LoggerAdapter(logging.LoggerAdapter):
    """Custom logger adapter for adding context to log messages."""
    
    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
        """
        Process log message with context.
        
        Args:
            msg: Log message
            kwargs: Keyword arguments
            
        Returns:
            tuple: Processed message and kwargs
        """
        # Add extra context to kwargs
        if 'extra' not in kwargs:
            kwargs['extra'] = {}
        
        kwargs['extra'].update(self.extra)
        
        return msg, kwargs


def create_logger_with_context(
    name: str,
    **context: Any
) -> LoggerAdapter:
    """
    Create a logger with context.
    
    Args:
        name: Logger name
        **context: Context key-value pairs
        
    Returns:
        LoggerAdapter: Logger adapter with context
    """
    logger = logging.getLogger(name)
    return LoggerAdapter(logger, context)


# Convenience functions for common logging patterns
def log_api_request(
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    user_id: Optional[str] = None,
    **extra: Any
) -> None:
    """
    Log API request with standard format.
    
    Args:
        method: HTTP method
        path: Request path
        status_code: Response status code
        duration_ms: Request duration in milliseconds
        user_id: Optional user ID
        **extra: Additional context
    """
    logger = logging.getLogger('api')
    logger.info(
        f"{method} {path} - {status_code}",
        extra={
            'method': method,
            'path': path,
            'status_code': status_code,
            'duration_ms': duration_ms,
            'user_id': user_id,
            **extra
        }
    )


def log_job_event(
    job_id: str,
    event_type: str,
    message: str,
    **extra: Any
) -> None:
    """
    Log job event with standard format.
    
    Args:
        job_id: Job ID
        event_type: Event type
        message: Log message
        **extra: Additional context
    """
    logger = logging.getLogger('jobs')
    logger.info(
        message,
        extra={
            'job_id': job_id,
            'event_type': event_type,
            **extra
        }
    )


def log_error(
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
    logger_name: str = 'error'
) -> None:
    """
    Log error with context.
    
    Args:
        error: Exception object
        context: Optional context dictionary
        logger_name: Logger name
    """
    logger = logging.getLogger(logger_name)
    logger.error(
        f"Error: {str(error)}",
        extra=context or {},
        exc_info=True
    )


# Export commonly used items
__all__ = [
    'setup_logging',
    'get_logger',
    'create_logger_with_context',
    'LoggerAdapter',
    'CustomJsonFormatter',
    'ContextFilter',
    'log_api_request',
    'log_job_event',
    'log_error',
]
