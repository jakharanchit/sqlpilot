# ============================================================
# tools/error_handler.py
# Production error handling for SQL Optimization Agent v3.
#
# WHAT THIS REPLACES:
#   V2 pattern (bad):
#       except Exception as e:
#           console.print(f"Error: {e}")
#           return {}       # silent failure, caller gets empty dict
#
#   V3 pattern (good):
#       except pyodbc.Error as e:
#           raise DBConnectionError(str(e)) from e
#
# HOW TO USE:
#   1. Import the exception you need:
#       from tools.error_handler import DBConnectionError, retry
#
#   2. Raise typed exceptions in tool code:
#       raise DBConnectionError("Cannot reach localhost\\SQLEXPRESS")
#
#   3. Catch at the pipeline level with full context:
#       except AgentError as e:
#           log.error(e.full_message())
#           console.print(e.user_message())
#
#   4. Use @retry decorator for Ollama calls:
#       @retry(max_attempts=3, delay=10, exceptions=(OllamaTimeoutError,))
#       def _ask_ollama(...): ...
# ============================================================

import functools
import time
import traceback
from datetime import datetime
from typing import Type


# ============================================================
# BASE EXCEPTION
# ============================================================

class AgentError(Exception):
    """
    Base class for all SQL Optimization Agent errors.

    Every AgentError carries:
    - A user-facing message (plain English, no traceback)
    - A technical message (full detail for logs)
    - A recovery suggestion (what to do next)
    - The tool name that raised it
    - A timestamp
    """

    def __init__(
        self,
        message:    str,
        detail:     str  = "",
        recovery:   str  = "",
        tool:       str  = "",
        retryable:  bool = False,
    ):
        super().__init__(message)
        self.message   = message
        self.detail    = detail
        self.recovery  = recovery
        self.tool      = tool
        self.retryable = retryable
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def user_message(self) -> str:
        """Short, plain-English message for terminal display."""
        parts = [f"✗ {self.message}"]
        if self.recovery:
            parts.append(f"  Fix: {self.recovery}")
        return "\n".join(parts)

    def full_message(self) -> str:
        """Full message for log file — includes all context."""
        parts = [
            f"[{self.timestamp}] {self.__class__.__name__}",
            f"  Tool:     {self.tool or 'unknown'}",
            f"  Message:  {self.message}",
        ]
        if self.detail:
            parts.append(f"  Detail:   {self.detail}")
        if self.recovery:
            parts.append(f"  Recovery: {self.recovery}")
        return "\n".join(parts)

    def __str__(self) -> str:
        return self.user_message()


# ============================================================
# TYPED EXCEPTIONS — one per failure domain
# ============================================================

class DBConnectionError(AgentError):
    """Cannot connect to SQL Server."""
    def __init__(self, detail: str = "", server: str = ""):
        super().__init__(
            message  = f"Cannot connect to SQL Server{f' ({server})' if server else ''}",
            detail   = detail,
            recovery = (
                "1. Check SQL Server is running: Services → SQL Server\n"
                "  2. Verify server name in config.py (try 'localhost\\\\SQLEXPRESS')\n"
                "  3. Check Windows Firewall is not blocking port 1433\n"
                "  4. Run: python agent.py check"
            ),
            tool      = "schema",
            retryable = True,
        )


class DBQueryError(AgentError):
    """A SQL query failed to execute."""
    def __init__(self, query_preview: str = "", detail: str = ""):
        super().__init__(
            message  = f"Query execution failed: {query_preview[:80]}{'...' if len(query_preview) > 80 else ''}",
            detail   = detail,
            recovery = (
                "1. Test the query manually in SSMS first\n"
                "  2. Check for syntax errors or missing table names\n"
                "  3. Verify you are connected to the correct database"
            ),
            tool      = "executor",
            retryable = False,
        )


class DBPermissionError(AgentError):
    """Insufficient SQL Server permissions."""
    def __init__(self, operation: str = "", detail: str = ""):
        super().__init__(
            message  = f"Insufficient SQL Server permissions{f' for: {operation}' if operation else ''}",
            detail   = detail,
            recovery = (
                "The connected SQL Server login needs these permissions:\n"
                "  - VIEW DATABASE STATE (for execution plans)\n"
                "  - VIEW SERVER STATE (for DMVs in lv-monitor)\n"
                "  - CREATE INDEX (for applying optimizations)\n"
                "  - db_owner (for sandbox DB creation)\n"
                "  Ask your DBA to grant these or use Windows Auth with a sysadmin account."
            ),
            tool      = "schema",
            retryable = False,
        )


class OllamaUnavailableError(AgentError):
    """Ollama is not running or not reachable."""
    def __init__(self, url: str = "http://localhost:11434"):
        super().__init__(
            message  = f"Ollama is not running at {url}",
            detail   = "Connection refused or timeout",
            recovery = (
                "1. Start Ollama: open a terminal and run 'ollama serve'\n"
                "  2. Keep that terminal open while using the agent\n"
                "  3. Verify Ollama is running: http://localhost:11434"
            ),
            tool      = "optimizer",
            retryable = True,
        )


class OllamaModelMissingError(AgentError):
    """A required Ollama model is not pulled."""
    def __init__(self, model: str):
        super().__init__(
            message  = f"Model '{model}' is not available in Ollama",
            detail   = f"Model {model} not found in ollama list",
            recovery = f"Pull the model with: ollama pull {model}",
            tool      = "optimizer",
            retryable = False,
        )


class OllamaTimeoutError(AgentError):
    """Ollama took too long to respond."""
    def __init__(self, model: str, timeout_s: int = 300):
        super().__init__(
            message  = f"Ollama timed out after {timeout_s}s (model: {model})",
            detail   = "Model may still be loading or system is under load",
            recovery = (
                "1. Wait 30 seconds and try again — model may still be loading\n"
                "  2. Check Ollama is not running another request\n"
                "  3. Restart Ollama if it's been running for a long time"
            ),
            tool      = "optimizer",
            retryable = True,
        )


class MigrationError(AgentError):
    """Migration file creation or registry operation failed."""
    def __init__(self, migration_num: int = 0, detail: str = ""):
        super().__init__(
            message  = f"Migration {migration_num:03d} failed",
            detail   = detail,
            recovery = (
                "1. Check migrations/ folder is writable\n"
                "  2. Check migrations/registry.json is valid JSON\n"
                "  3. Run: python agent.py migrations to see current state"
            ),
            tool      = "migrator",
            retryable = False,
        )


class SandboxError(AgentError):
    """Shadow DB sandbox operation failed."""
    def __init__(self, operation: str = "", detail: str = ""):
        super().__init__(
            message  = f"Sandbox operation failed{f': {operation}' if operation else ''}",
            detail   = detail,
            recovery = (
                "1. Ensure SQL Server login has CREATE DATABASE permission\n"
                "  2. Check the .bak file path in config.py is correct\n"
                "  3. Check disk space is sufficient for the shadow DB\n"
                "  4. Run: python agent.py sandbox-destroy to clean up any leftover shadow"
            ),
            tool      = "sandbox",
            retryable = False,
        )


class ConfigError(AgentError):
    """Configuration is missing or invalid."""
    def __init__(self, field: str, detail: str = ""):
        super().__init__(
            message  = f"Configuration error: {field}",
            detail   = detail,
            recovery = f"Open config.py and set a valid value for: {field}",
            tool      = "config_validator",
            retryable = False,
        )


class ReportError(AgentError):
    """Report or deployment package generation failed."""
    def __init__(self, detail: str = ""):
        super().__init__(
            message  = "Failed to generate report or deployment package",
            detail   = detail,
            recovery = (
                "1. Check reports/ and deployments/ folders are writable\n"
                "  2. Check disk space\n"
                "  3. Check migrations/registry.json exists and is valid"
            ),
            tool      = "reporter",
            retryable = False,
        )


class GitError(AgentError):
    """Git operation failed."""
    def __init__(self, detail: str = ""):
        super().__init__(
            message  = "Git operation failed — changes saved to disk but not committed",
            detail   = detail,
            recovery = (
                "1. Run: git status to see current state\n"
                "  2. Run: git add . && git commit -m 'manual commit' to commit manually\n"
                "  3. Or set AUTO_COMMIT_GIT = False in config.py to disable auto-commit"
            ),
            tool      = "git_manager",
            retryable = False,
        )


class HistoryDBError(AgentError):
    """history.db SQLite operation failed."""
    def __init__(self, detail: str = ""):
        super().__init__(
            message  = "History database error",
            detail   = detail,
            recovery = (
                "1. Check history.db is not locked by another process\n"
                "  2. If corrupted: delete history.db (history will restart from zero)\n"
                "  3. Check disk space"
            ),
            tool      = "history",
            retryable = False,
        )


class PlanCaptureError(AgentError):
    """Execution plan could not be captured."""
    def __init__(self, detail: str = ""):
        super().__init__(
            message  = "Could not capture execution plan from SQL Server",
            detail   = detail,
            recovery = (
                "1. Verify the query runs successfully in SSMS first\n"
                "  2. Check the SQL Server login has VIEW DATABASE STATE permission\n"
                "  3. Try estimated plan (--no-actual flag) as a fallback"
            ),
            tool      = "executor",
            retryable = False,
        )


# ============================================================
# RETRY DECORATOR
# ============================================================

def retry(
    max_attempts: int               = 3,
    delay:        float             = 10.0,
    backoff:      float             = 2.0,
    exceptions:   tuple             = (OllamaTimeoutError, OllamaUnavailableError),
    on_retry:     callable          = None,
):
    """
    Decorator that retries a function on specified exceptions.

    Args:
        max_attempts: total attempts including the first (default 3)
        delay:        seconds to wait before first retry (default 10)
        backoff:      multiply delay by this on each retry (default 2.0)
                      so: 10s, 20s, 40s
        exceptions:   tuple of exception types that trigger a retry
        on_retry:     optional callback(attempt, exception, wait_secs)
                      called before each retry

    Usage:
        @retry(max_attempts=3, delay=10, exceptions=(OllamaTimeoutError,))
        def _ask_ollama(model, prompt):
            ...

        # With custom retry handler
        @retry(max_attempts=3, on_retry=lambda a, e, w: console.print(f"Retry {a}..."))
        def _ask_ollama(model, prompt):
            ...
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            wait    = delay
            last_ex = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)

                except exceptions as e:
                    last_ex = e

                    if attempt == max_attempts:
                        # Final attempt failed — re-raise
                        raise

                    # Call the on_retry callback if provided
                    if on_retry:
                        try:
                            on_retry(attempt, e, wait)
                        except Exception:
                            pass

                    time.sleep(wait)
                    wait *= backoff

            raise last_ex  # Should not reach here but satisfies type checker

        return wrapper
    return decorator


# ============================================================
# SAFE CALL HELPER
# ============================================================

def safe_call(
    fn:          callable,
    *args,
    fallback     = None,
    log_errors:  bool = True,
    reraise:     bool = False,
    context:     str  = "",
    **kwargs,
):
    """
    Calls fn(*args, **kwargs) safely.

    On success: returns the result.
    On AgentError: logs it, returns fallback.
    On unexpected Exception: wraps in AgentError, logs it, returns fallback.

    Args:
        fn:          the function to call
        fallback:    value to return on error (default None)
        log_errors:  write errors to app logger (default True)
        reraise:     re-raise the exception after logging (default False)
        context:     extra context string for the log entry
        *args/**kwargs: passed to fn

    Usage:
        result = safe_call(get_schema, "measurements", fallback={})
        result = safe_call(optimize_query, query, schema, reraise=True)
    """
    try:
        return fn(*args, **kwargs)

    except AgentError as e:
        if log_errors:
            try:
                from tools.app_logger import get_logger
                logger = get_logger()
                logger.error(f"{context + ': ' if context else ''}{e.full_message()}")
            except Exception:
                pass

        if reraise:
            raise
        return fallback

    except Exception as e:
        # Wrap unexpected exceptions
        agent_err = AgentError(
            message  = f"Unexpected error{f' in {context}' if context else ''}: {type(e).__name__}: {e}",
            detail   = traceback.format_exc(),
            recovery = "Check the log file for full details: logs/agent.log",
            retryable= False,
        )

        if log_errors:
            try:
                from tools.app_logger import get_logger
                logger = get_logger()
                logger.error(agent_err.full_message())
            except Exception:
                pass

        if reraise:
            raise agent_err from e
        return fallback


# ============================================================
# CONTEXT MANAGER: operation block
# ============================================================

class operation:
    """
    Context manager for a named operation block.
    Logs start/end, catches exceptions, prints user-friendly errors.

    Usage:
        with operation("Fetching schema", tool="schema") as op:
            result = get_schema("measurements")
            op.succeed(f"Got {len(result['columns'])} columns")

        # With console output
        with operation("Running benchmark", console=console) as op:
            result = benchmark_query(before, after)
    """

    def __init__(
        self,
        name:    str,
        tool:    str      = "",
        console           = None,
        reraise: bool     = False,
    ):
        self.name    = name
        self.tool    = tool
        self.console = console
        self.reraise = reraise
        self.success = False
        self._start  = None

    def __enter__(self):
        self._start = time.time()
        try:
            from tools.app_logger import get_logger
            get_logger().debug(f"[{self.tool}] START: {self.name}")
        except Exception:
            pass
        return self

    def succeed(self, msg: str = ""):
        """Call this to mark the operation as successful."""
        self.success = True
        elapsed = round(time.time() - self._start, 2)
        try:
            from tools.app_logger import get_logger
            get_logger().info(
                f"[{self.tool}] OK: {self.name} "
                f"{'— ' + msg if msg else ''} ({elapsed}s)"
            )
        except Exception:
            pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = round(time.time() - self._start, 2)

        if exc_type is None:
            if not self.success:
                try:
                    from tools.app_logger import get_logger
                    get_logger().info(f"[{self.tool}] OK: {self.name} ({elapsed}s)")
                except Exception:
                    pass
            return False  # Don't suppress

        # An exception occurred
        if isinstance(exc_val, AgentError):
            try:
                from tools.app_logger import get_logger
                get_logger().error(
                    f"[{self.tool}] FAIL: {self.name} ({elapsed}s)\n"
                    f"{exc_val.full_message()}"
                )
            except Exception:
                pass

            if self.console:
                self.console.print(f"\n[red]{exc_val.user_message()}[/red]")

            return not self.reraise  # Suppress if not reraising

        else:
            # Unexpected exception — wrap and log
            agent_err = AgentError(
                message  = f"{self.name} failed: {type(exc_val).__name__}: {exc_val}",
                detail   = traceback.format_exc(),
                recovery = "Check logs/agent.log for full details",
                tool     = self.tool,
            )
            try:
                from tools.app_logger import get_logger
                get_logger().error(
                    f"[{self.tool}] UNEXPECTED: {self.name} ({elapsed}s)\n"
                    f"{agent_err.full_message()}"
                )
            except Exception:
                pass

            if self.console:
                self.console.print(f"\n[red]{agent_err.user_message()}[/red]")

            if self.reraise:
                return False  # Let the original exception propagate
            return True  # Suppress unexpected exceptions
