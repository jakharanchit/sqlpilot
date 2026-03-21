# ============================================================
# tests/test_error_handler.py
# Tests for tools/error_handler.py
#
# Covers:
#   - All typed exception classes (message, detail, recovery)
#   - @retry decorator (retries, backoff, max attempts)
#   - safe_call() helper (fallback, logging, reraise)
#   - operation() context manager (success, failure, suppression)
# ============================================================

import time
from unittest.mock import MagicMock, patch

import pytest

from tools.error_handler import (
    AgentError,
    ConfigError,
    DBConnectionError,
    DBQueryError,
    GitError,
    HistoryDBError,
    MigrationError,
    OllamaModelMissingError,
    OllamaTimeoutError,
    OllamaUnavailableError,
    PlanCaptureError,
    ReportError,
    SandboxError,
    operation,
    retry,
    safe_call,
)


# ============================================================
# AgentError base class
# ============================================================

class TestAgentError:
    def test_basic_message(self):
        err = AgentError("something went wrong")
        assert "something went wrong" in str(err)
        assert "something went wrong" in err.user_message()

    def test_recovery_in_user_message(self):
        err = AgentError("failed", recovery="try this fix")
        assert "try this fix" in err.user_message()

    def test_full_message_includes_all_fields(self):
        err = AgentError(
            message  = "test error",
            detail   = "full technical detail",
            recovery = "do this to fix",
            tool     = "optimizer",
        )
        full = err.full_message()
        assert "test error"            in full
        assert "full technical detail" in full
        assert "do this to fix"        in full
        assert "optimizer"             in full

    def test_timestamp_set(self):
        err = AgentError("msg")
        assert err.timestamp != ""
        assert "2026" in err.timestamp or "20" in err.timestamp  # year prefix

    def test_retryable_flag(self):
        retryable     = AgentError("msg", retryable=True)
        not_retryable = AgentError("msg", retryable=False)
        assert retryable.retryable is True
        assert not_retryable.retryable is False

    def test_inherits_from_exception(self):
        err = AgentError("msg")
        assert isinstance(err, Exception)


# ============================================================
# Typed exception classes
# ============================================================

class TestTypedExceptions:
    def test_db_connection_error_has_recovery(self):
        err = DBConnectionError("connection refused", server="localhost")
        assert "localhost" in err.message
        assert err.recovery != ""
        assert err.retryable is True

    def test_db_query_error_truncates_long_query(self):
        long_query = "SELECT * FROM " + "x" * 200
        err = DBQueryError(query_preview=long_query)
        assert len(err.message) < 200
        assert "..." in err.message

    def test_ollama_unavailable_has_serve_instruction(self):
        err = OllamaUnavailableError()
        assert "ollama serve" in err.recovery.lower()
        assert err.retryable is True

    def test_ollama_model_missing_has_pull_command(self):
        err = OllamaModelMissingError("qwen2.5-coder:14b")
        assert "ollama pull qwen2.5-coder:14b" in err.recovery
        assert err.retryable is False

    def test_ollama_timeout_shows_model_name(self):
        err = OllamaTimeoutError("deepseek-r1:14b", timeout_s=300)
        assert "deepseek-r1:14b" in err.message
        assert "300" in err.message
        assert err.retryable is True

    def test_migration_error_formats_number(self):
        err = MigrationError(migration_num=4)
        assert "004" in err.message

    def test_sandbox_error(self):
        err = SandboxError(operation="create shadow DB")
        assert "create shadow DB" in err.message
        assert err.recovery != ""

    def test_config_error_shows_field(self):
        err = ConfigError("DB_CONFIG['database']")
        assert "DB_CONFIG['database']" in err.message
        assert "config.py" in err.recovery

    def test_git_error_mentions_manual_commit(self):
        err = GitError()
        assert "git" in err.recovery.lower()

    def test_all_typed_errors_are_agent_errors(self):
        errors = [
            DBConnectionError(),
            DBQueryError(),
            OllamaUnavailableError(),
            OllamaModelMissingError("model"),
            OllamaTimeoutError("model"),
            MigrationError(),
            SandboxError(),
            ConfigError("field"),
            ReportError(),
            GitError(),
            HistoryDBError(),
            PlanCaptureError(),
        ]
        for err in errors:
            assert isinstance(err, AgentError), f"{type(err)} should be AgentError"


# ============================================================
# @retry decorator
# ============================================================

class TestRetryDecorator:
    def test_succeeds_on_first_attempt(self):
        call_count = [0]

        @retry(max_attempts=3, delay=0)
        def always_succeeds():
            call_count[0] += 1
            return "ok"

        result = always_succeeds()
        assert result == "ok"
        assert call_count[0] == 1

    def test_retries_on_specified_exception(self):
        call_count = [0]

        @retry(max_attempts=3, delay=0, exceptions=(OllamaTimeoutError,))
        def fails_twice():
            call_count[0] += 1
            if call_count[0] < 3:
                raise OllamaTimeoutError("model")
            return "ok after retries"

        result = fails_twice()
        assert result == "ok after retries"
        assert call_count[0] == 3

    def test_raises_after_max_attempts(self):
        call_count = [0]

        @retry(max_attempts=3, delay=0, exceptions=(OllamaTimeoutError,))
        def always_fails():
            call_count[0] += 1
            raise OllamaTimeoutError("model")

        with pytest.raises(OllamaTimeoutError):
            always_fails()

        assert call_count[0] == 3

    def test_does_not_retry_non_specified_exception(self):
        call_count = [0]

        @retry(max_attempts=3, delay=0, exceptions=(OllamaTimeoutError,))
        def raises_different():
            call_count[0] += 1
            raise ValueError("not retryable")

        with pytest.raises(ValueError):
            raises_different()

        assert call_count[0] == 1  # No retries

    def test_on_retry_callback_called(self):
        retry_calls = []

        def on_retry_cb(attempt, exc, wait):
            retry_calls.append((attempt, type(exc).__name__))

        call_count = [0]

        @retry(max_attempts=3, delay=0, exceptions=(OllamaTimeoutError,), on_retry=on_retry_cb)
        def fails_twice():
            call_count[0] += 1
            if call_count[0] < 3:
                raise OllamaTimeoutError("model")
            return "ok"

        fails_twice()
        assert len(retry_calls) == 2
        assert retry_calls[0] == (1, "OllamaTimeoutError")
        assert retry_calls[1] == (2, "OllamaTimeoutError")

    def test_preserves_function_name(self):
        @retry(max_attempts=2, delay=0)
        def my_function():
            return "ok"

        assert my_function.__name__ == "my_function"


# ============================================================
# safe_call() helper
# ============================================================

class TestSafeCall:
    def test_returns_result_on_success(self):
        def add(a, b): return a + b
        result = safe_call(add, 2, 3, fallback=0)
        assert result == 5

    def test_returns_fallback_on_agent_error(self):
        def raises_agent_error():
            raise DBConnectionError("no connection")

        result = safe_call(raises_agent_error, fallback="fallback_value", log_errors=False)
        assert result == "fallback_value"

    def test_returns_fallback_on_unexpected_exception(self):
        def raises_unexpected():
            raise RuntimeError("unexpected crash")

        result = safe_call(raises_unexpected, fallback={}, log_errors=False)
        assert result == {}

    def test_reraise_propagates_agent_error(self):
        def raises_db():
            raise DBConnectionError("no DB")

        with pytest.raises(DBConnectionError):
            safe_call(raises_db, reraise=True, log_errors=False)

    def test_reraise_wraps_unexpected_exception(self):
        def raises_unexpected():
            raise RuntimeError("crash")

        with pytest.raises(AgentError):
            safe_call(raises_unexpected, reraise=True, log_errors=False)

    def test_none_fallback_by_default(self):
        def raises():
            raise AgentError("err")

        result = safe_call(raises, log_errors=False)
        assert result is None

    def test_passes_args_and_kwargs(self):
        def greet(name, greeting="Hello"):
            return f"{greeting}, {name}!"

        result = safe_call(greet, "World", greeting="Hi", fallback="")
        assert result == "Hi, World!"


# ============================================================
# operation() context manager
# ============================================================

class TestOperation:
    def test_succeeds_silently(self):
        """A successful operation should not raise."""
        with operation("test op", tool="test"):
            x = 1 + 1
        assert x == 2

    def test_succeed_method(self):
        with operation("test op") as op:
            op.succeed("all good")
        assert op.success is True

    def test_suppresses_agent_error_by_default(self):
        """AgentErrors should be suppressed (not reraise by default)."""
        with operation("test op", reraise=False):
            raise DBConnectionError("no DB")
        # Should not propagate — reaches here

    def test_reraise_propagates_agent_error(self):
        with pytest.raises(DBConnectionError):
            with operation("test op", reraise=True):
                raise DBConnectionError("no DB")

    def test_suppresses_unexpected_exception_by_default(self):
        """Unexpected exceptions should also be suppressed by default."""
        with operation("test op", reraise=False):
            raise ValueError("unexpected")
        # Should not propagate

    def test_reraise_propagates_unexpected_exception(self):
        with pytest.raises(ValueError):
            with operation("test op", reraise=True):
                raise ValueError("unexpected")

    def test_console_output_on_failure(self):
        mock_console = MagicMock()

        with operation("test op", console=mock_console, reraise=False):
            raise DBConnectionError("no DB")

        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args[0][0]
        assert "DB" in call_args or "connect" in call_args.lower()
