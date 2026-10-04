from __future__ import annotations

import atexit
import logging
import os
import sys
from logging.handlers import QueueHandler, QueueListener, RotatingFileHandler
from pathlib import Path
from queue import Queue

APP_NAME = "CleanSheet"
LOGGER_NAME = "cleansheet"

# 5 MiB per log file, keep 3 backups.
MAX_LOG_SIZE = 5 * 1024 * 1024
BACKUP_COUNT = 3

_log_queue: Queue[logging.LogRecord] | None = None
_listener: QueueListener | None = None
_queue_handler: QueueHandler | None = None
_initialized = False


def get_log_directory() -> Path:
    """Return the platform-appropriate directory for application logs."""

    if sys.platform == "win32":
        # Preferred Windows location:
        # C:\\Users\\<user>\\AppData\\Local\\CleanSheet\\Logs
        local_app_data = os.environ.get("LOCALAPPDATA")

        if local_app_data:
            return Path(local_app_data) / APP_NAME / "Logs"

        # Fallback if LOCALAPPDATA is unavailable.
        return Path.home() / "AppData" / "Local" / APP_NAME / "Logs"

    # Linux / other Unix-like systems.
    #
    # Respect XDG_STATE_HOME when available.
    #
    # Example:
    # ~/.local/state/cleansheet/logs
    xdg_state_home = os.environ.get("XDG_STATE_HOME")

    if xdg_state_home:
        return Path(xdg_state_home) / LOGGER_NAME / "logs"

    return Path.home() / ".local" / "state" / LOGGER_NAME / "logs"


def get_log_file() -> Path:
    """Return the path to the current application's log file."""

    return get_log_directory() / "cleansheet.log"


def setup_logging() -> None:
    """Initialize application-wide logging."""

    global _log_queue
    global _listener
    global _queue_handler
    global _initialized

    # Prevent duplicate handlers/listeners if called more than once.
    if _initialized:
        return

    log_directory = get_log_directory()
    log_directory.mkdir(parents=True, exist_ok=True)

    log_file = get_log_file()

    _log_queue = Queue()

    # ---------------------------------------------------------
    # Formatter
    # ---------------------------------------------------------

    formatter = logging.Formatter(
        fmt=("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"),
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # ---------------------------------------------------------
    # File handler
    # ---------------------------------------------------------

    file_handler = RotatingFileHandler(
        filename=log_file,
        maxBytes=MAX_LOG_SIZE,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )

    # File receives everything from DEBUG upward.
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # ---------------------------------------------------------
    # Console handler
    # ---------------------------------------------------------

    console_handler = logging.StreamHandler()

    # Console only receives INFO and above.
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # ---------------------------------------------------------
    # Queue listener
    # ---------------------------------------------------------

    # Pass the handlers here for queue to handle
    _listener = QueueListener(
        _log_queue,
        file_handler,
        console_handler,
        respect_handler_level=True,
    )

    # ---------------------------------------------------------
    # Application logger
    # ---------------------------------------------------------

    logger = logging.getLogger(LOGGER_NAME)

    logger.setLevel(logging.DEBUG)

    # Make sure this logger does not send records to the root
    # logger and accidentally produce duplicate output.
    logger.propagate = False

    # QueueHandler is the only handler attached to the application
    # logger. Actual output is handled by QueueListener.
    _queue_handler = QueueHandler(_log_queue)

    logger.addHandler(_queue_handler)

    # Start the background listener.
    _listener.start()

    _initialized = True

    # Make sure the listener is stopped when Python exits.
    atexit.register(shutdown_logging)

    logger.info("Logging initialized")
    logger.debug("Log file: %s", log_file)


def shutdown_logging() -> None:
    """Stop the logging listener and release logging resources."""

    global _listener
    global _log_queue
    global _queue_handler
    global _initialized

    logger = logging.getLogger(LOGGER_NAME)

    if _listener is not None:
        _listener.stop()
        _listener = None

    # Remove QueueListener after stopping
    if _queue_handler is not None:
        logger.removeHandler(_queue_handler)
        _queue_handler = None

    _log_queue = None
    _initialized = False
