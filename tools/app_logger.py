# ============================================================
# tools/app_logger.py
# Structured rotating log file for SQL Optimization Agent v3.
#
# V2 PROBLEM:
#   All output went to the terminal only. If a run silently
#   failed or produced wrong results, there was no record of
#   what happened, in what order, or why.
#
# V3 SOLUTION:
#   Every operation is written to a rotating daily log file
#   alongside the terminal. The log file survives terminal
#   sessions and provides a full audit trail.
#
# LOG LOCATION:
#   logs/agent_2026_03_21.log   (daily file)
#   logs/agent.log              (always points to today's log)
#
# LOG FORMAT:
#   2026-03-21 14:32:01 INFO  [optimizer]   Starting 9-step pipeline
#   2026-03-21 14:32:04 INFO  [executor]    Plan captured — 847ms
#   2026-03-21 14:33:13 ERROR [git_manager] Commit failed: repo is dirty
#
# USAGE:
#   from tools.app_logger import get_logger, log_operation
#
#   log = get_logger()
#   log.info("Schema fetched — 14 columns, 3 indexes")
#   log.error("Connection failed — check config.py")
#
#   # Or use the context manager from error_handler:
#   with operation("Fetching schema", tool="schema"):
#       result = get_schema("measurements")
# ============================================================

import logging
import logging.handlers
import os
import sys
from datetime import date, datetime
from pathlib import Path

# Lazy import to avoid circular dependency
_logger_instance = None

LOG_DIR  = None   # set from config on first call
LOG_NAME = "agent"


# ============================================================
# SETUP
# ============================================================

def _get_log_dir() -> Path:
    """Get log directory from config, create if needed."""
    global LOG_DIR
    if LOG_DIR is None:
        try:
            from config import BASE_DIR
            LOG_DIR = Path(BASE_DIR) / "logs"
        except ImportError:
            LOG_DIR = Path("logs")
    p = Path(LOG_DIR)
    p.mkdir(parents=True, exist_ok=True)
    return p


class _DailyFileHandler(logging.handlers.TimedRotatingFileHandler):
    """
    Rotating file handler that creates a new file each day.
    Also maintains a symlink/copy at logs/agent.log pointing
    to today's log for easy access.
    """

    def __init__(self, log_dir: Path):
        today    = date.today().strftime("%Y_%m_%d")
        log_file = log_dir / f"{LOG_NAME}_{today}.log"

        super().__init__(
            filename   = str(log_file),
            when       = "midnight",
            interval   = 1,
            backupCount= 30,        # keep 30 days of logs
            encoding   = "utf-8",
            utc        = False,
        )

        # On Windows, create a copy named agent.log pointing to today
        # (Windows doesn't support symlinks without admin rights)
        self._latest_path = log_dir / f"{LOG_NAME}.log"
        self._update_latest_link(log_file)

    def _update_latest_link(self, log_file: Path):
        """Keep agent.log up to date with today's log."""
        try:
            latest = self._latest_path
            if sys.platform == "win32":
                # Windows: just write a pointer file
                latest.write_text(
                    f"Latest log: {log_file.name}\n"
                    f"Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
                    encoding="utf-8",
                )
            else:
                # Unix: proper symlink
                if latest.exists() or latest.is_symlink():
                    latest.unlink()
                latest.symlink_to(log_file.name)
        except Exception:
            pass  # Non-critical — log file still works without the link


class _ColorTerminalHandler(logging.StreamHandler):
    """
    Terminal handler that suppresses log output to avoid
    duplicating what the Rich console already shows.

    Only writes WARNING and above to stderr — these are
    things that should be visible even when Rich isn't printing.
    """

    LEVEL_COLORS = {
        "DEBUG":    "\033[36m",   # cyan
        "INFO":     "\033[32m",   # green
        "WARNING":  "\033[33m",   # yellow
        "ERROR":    "\033[31m",   # red
        "CRITICAL": "\033[35m",   # magenta
    }
    RESET = "\033[0m"

    def emit(self, record: logging.LogRecord):
        # Only show WARNING+ on terminal to avoid noise
        # (Rich console handles INFO output)
        if record.levelno < logging.WARNING:
            return
        try:
            color = self.LEVEL_COLORS.get(record.levelname, "")
            msg   = self.format(record)
            sys.stderr.write(f"{color}{msg}{self.RESET}\n")
            sys.stderr.flush()
        except Exception:
            self.handleError(record)


# ============================================================
# FORMATTER
# ============================================================

class _AgentFormatter(logging.Formatter):
    """
    Custom log formatter.
    Format: YYYY-MM-DD HH:MM:SS LEVEL  [tool]  message
    """

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        level   = f"{record.levelname:<8}"
        tool    = getattr(record, "tool", "agent")
        tool_str = f"[{tool:<14}]"
        message  = record.getMessage()

        # For multiline messages (e.g. tracebacks), indent continuation lines
        if "\n" in message:
            lines   = message.splitlines()
            indent  = " " * (len(timestamp) + 1 + len(level) + 1 + len(tool_str) + 2)
            message = ("\n" + indent).join(lines)

        return f"{timestamp} {level} {tool_str} {message}"


# ============================================================
# MAIN API: get_logger
# ============================================================

def get_logger(tool: str = "") -> "AgentLogger":
    """
    Returns the singleton logger instance.
    Creates it on first call.

    Args:
        tool: optional tool name prefix for this logger context
              e.g. "optimizer", "schema", "benchmarker"

    Returns:
        AgentLogger instance

    Usage:
        from tools.app_logger import get_logger

        log = get_logger("optimizer")
        log.info("Starting 9-step pipeline")
        log.error("Ollama timed out")
        log.debug("Schema has 14 columns")
    """
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = _create_logger()
    return AgentLogger(_logger_instance, tool)


def _create_logger() -> logging.Logger:
    """Create and configure the underlying Python logger."""
    logger = logging.getLogger("sql_agent")

    if logger.handlers:
        return logger  # Already configured

    logger.setLevel(logging.DEBUG)

    log_dir   = _get_log_dir()
    formatter = _AgentFormatter()

    # File handler — all levels, daily rotation
    try:
        file_handler = _DailyFileHandler(log_dir)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        # Log dir not writable — continue without file logging
        print(f"Warning: Could not create log file in {log_dir}: {e}", file=sys.stderr)

    # Terminal handler — WARNING and above only
    terminal_handler = _ColorTerminalHandler()
    terminal_handler.setLevel(logging.WARNING)
    terminal_handler.setFormatter(formatter)
    logger.addHandler(terminal_handler)

    # Don't propagate to root logger
    logger.propagate = False

    return logger


# ============================================================
# AGENT LOGGER WRAPPER
# ============================================================

class AgentLogger:
    """
    Thin wrapper around Python's Logger that adds:
    - Tool name context to every log entry
    - Convenience methods for common patterns
    - Timing helpers
    """

    def __init__(self, logger: logging.Logger, tool: str = ""):
        self._logger = logger
        self._tool   = tool

    def _extra(self) -> dict:
        return {"tool": self._tool or "agent"}

    def debug(self, msg: str):
        self._logger.debug(msg, extra=self._extra())

    def info(self, msg: str):
        self._logger.info(msg, extra=self._extra())

    def warning(self, msg: str):
        self._logger.warning(msg, extra=self._extra())

    def error(self, msg: str):
        self._logger.error(msg, extra=self._extra())

    def critical(self, msg: str):
        self._logger.critical(msg, extra=self._extra())

    def tool(self, name: str) -> "AgentLogger":
        """Return a new logger with a different tool context."""
        return AgentLogger(self._logger, name)

    def pipeline_start(self, name: str, query_preview: str = ""):
        """Log the start of a pipeline run."""
        self.info(
            f"PIPELINE START: {name}"
            + (f" — query: {query_preview[:80]}..." if len(query_preview) > 80
               else f" — query: {query_preview}" if query_preview else "")
        )

    def pipeline_step(self, step: int, total: int, label: str):
        """Log a pipeline step."""
        self.debug(f"Step {step}/{total}: {label}")

    def pipeline_end(self, name: str, elapsed_s: float, success: bool = True):
        """Log the end of a pipeline run."""
        status = "COMPLETE" if success else "FAILED"
        self.info(f"PIPELINE {status}: {name} ({elapsed_s:.1f}s)")

    def benchmark_result(
        self,
        label:          str,
        before_ms:      float,
        after_ms:       float,
        improvement_pct:float,
    ):
        """Log a benchmark result."""
        self.info(
            f"BENCHMARK: {label} — "
            f"{before_ms}ms → {after_ms}ms ({improvement_pct}% improvement)"
        )

    def migration_created(self, number: int, filename: str):
        """Log a migration file creation."""
        self.info(f"MIGRATION CREATED: {number:03d} — {filename}")

    def git_committed(self, commit_type: str, message: str, hash_: str = ""):
        """Log a Git commit."""
        self.info(
            f"GIT COMMIT: [{commit_type}] {message}"
            + (f" ({hash_})" if hash_ else "")
        )

    def schema_change(self, severity: str, object_: str, detail: str):
        """Log a schema change detected by watcher."""
        level = self.error if severity == "HIGH" else self.warning
        level(f"SCHEMA CHANGE [{severity}]: {object_} — {detail}")


# ============================================================
# CONVENIENCE: log_operation decorator
# ============================================================

def log_operation(tool: str = "", log_args: bool = False):
    """
    Decorator that logs function entry/exit and any exceptions.

    Args:
        tool:     tool name for the log context
        log_args: whether to log function arguments (default False
                  — avoid logging sensitive data like queries)

    Usage:
        @log_operation(tool="schema")
        def get_schema(table_name: str) -> dict:
            ...

        @log_operation(tool="optimizer", log_args=False)
        def optimize_query(query: str, schema_list: list) -> dict:
            ...
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            import functools
            log     = get_logger(tool)
            fn_name = func.__name__
            start   = datetime.now()

            log.debug(
                f"CALL: {fn_name}"
                + (f"({args[0] if args else ''})" if log_args else "()")
            )

            try:
                result = func(*args, **kwargs)
                elapsed = (datetime.now() - start).total_seconds()
                log.debug(f"RETURN: {fn_name} ({elapsed:.2f}s)")
                return result

            except Exception as e:
                elapsed = (datetime.now() - start).total_seconds()
                log.error(f"ERROR in {fn_name} ({elapsed:.2f}s): {type(e).__name__}: {e}")
                raise

        return wrapper

    # Handle being called with or without arguments
    import functools
    if callable(tool):
        # Called as @log_operation without arguments
        fn = tool
        tool = ""
        return decorator(fn)
    return decorator


# ============================================================
# LOG READER — for diagnostics and the check command
# ============================================================

def get_recent_log_lines(n: int = 50, level: str = None) -> list:
    """
    Returns the last N lines from today's log file.

    Args:
        n:     number of lines (default 50)
        level: filter to this level only — "ERROR", "WARNING", etc.

    Returns:
        list of log line strings

    Usage:
        lines = get_recent_log_lines(20, level="ERROR")
    """
    log_dir  = _get_log_dir()
    today    = date.today().strftime("%Y_%m_%d")
    log_file = log_dir / f"{LOG_NAME}_{today}.log"

    if not log_file.exists():
        return []

    try:
        lines = log_file.read_text(encoding="utf-8", errors="ignore").splitlines()

        if level:
            lines = [l for l in lines if f" {level} " in l or f" {level:<8}" in l]

        return lines[-n:]
    except Exception:
        return []


def get_log_stats() -> dict:
    """
    Returns counts of each log level from today's log.

    Returns:
        dict with error_count, warning_count, info_count, debug_count
    """
    lines = get_recent_log_lines(n=10000)
    return {
        "error_count":   sum(1 for l in lines if " ERROR    " in l),
        "warning_count": sum(1 for l in lines if " WARNING  " in l),
        "info_count":    sum(1 for l in lines if " INFO     " in l),
        "debug_count":   sum(1 for l in lines if " DEBUG    " in l),
        "total_lines":   len(lines),
        "log_date":      date.today().isoformat(),
    }
