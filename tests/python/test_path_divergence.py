"""Pin the known divergences between the pydantic and unvalidated paths.

These tests document behavior that was preserved from the pre-existing
unvalidated path. They are not bugs to fix; they are documented
limitations of the fallback path. If a future refactor changes the
behavior, these tests will catch it so the change is intentional.

The pydantic path applies model defaults (e.g. ``cron_interval=6``)
when a field is missing from the input data. The unvalidated path
preserves the current value of that field. This means a partial
config load behaves differently depending on whether pydantic is
installed.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from lib.config_manager import EnhancedConfigManager


# PYDANTIC model defaults (lib/config_validation.py PydanticWrapperConfig).
# These are what the pydantic path resets to when a field is missing.
# If a future PR changes one of these in lib/config_validation.py, the
# pydantic-path test below will need updating.
PYDANTIC_DEFAULTS = {
    "bin_dir": "",
    "active_profile": "default",
    "debug_mode": False,
    "log_level": "INFO",
    "cron_interval": 6,
    "enable_notifications": True,
    "hook_failure_mode_default": "warn",
    "pre_launch_failure_mode_default": "abort",
    "post_launch_failure_mode_default": "warn",
}

# UNVALIDATED path's hardcoded defaults (lib/config_manager.py
# _apply_unvalidated_config). May differ from PYDANTIC_DEFAULTS for
# fields where the unvalidated path uses a different literal (e.g. the
# pre/post_launch_failure_mode_default fields reset to None because
# data.get("x") with no default returns None on a missing key).
UNVALIDATED_DEFAULTS = {
    "bin_dir": "stale-string",  # preserves previous value; placeholder
    "active_profile": "default",  # placeholder; preserves previous
    "debug_mode": False,  # placeholder; preserves previous
    "log_level": "INFO",  # placeholder; preserves previous
    "cron_interval": 99,  # placeholder; preserves previous
    "enable_notifications": True,  # placeholder; preserves previous
    "hook_failure_mode_default": "warn",  # data.get(..., "warn")
    "pre_launch_failure_mode_default": None,  # data.get(...) -> None
    "post_launch_failure_mode_default": None,  # data.get(...) -> None
}

# For each field, True if the unvalidated path preserves the previous
# value (data.get("x", self.config.x)). False if the unvalidated path
# uses a hardcoded default that overrides the previous value.
PRESERVES_PREVIOUS_VALUE = {
    "bin_dir": True,
    "active_profile": True,
    "debug_mode": True,
    "log_level": True,
    "cron_interval": True,
    "enable_notifications": True,
    "hook_failure_mode_default": False,
    "pre_launch_failure_mode_default": False,
    "post_launch_failure_mode_default": False,
}

# The stale value to set on a field whose initial/current value is None
# (i.e. Optional[str] fields defaulting to None). A non-None string lets
# us prove the field was actually reset, not just left as None.
NONE_TYPED_STALE = "stale-string"


@pytest.fixture
def validated_manager():
    with tempfile.TemporaryDirectory() as tmp:
        yield EnhancedConfigManager(config_dir=Path(tmp))


@pytest.fixture
def unvalidated_manager():
    with tempfile.TemporaryDirectory() as tmp, \
         patch("lib.config_manager.PYDANTIC_AVAILABLE", False), \
         patch("lib.config_manager.PydanticWrapperConfig", None):
        yield EnhancedConfigManager(config_dir=Path(tmp))


class TestTopLevelFieldDivergence:
    """The two paths differ in how they handle missing top-level fields.

    Pydantic: applies the model default (e.g. cron_interval=6).
    Unvalidated: keeps the current value (e.g. cron_interval=99 if it
    was 99 before the load).

    This is a pre-existing behavior, not a bug introduced by the
    refactor. These tests pin the behavior so future changes are
    intentional.
    """

    @pytest.mark.parametrize("field,default", list(PYDANTIC_DEFAULTS.items()))
    def test_pydantic_path_resets_to_default_when_field_missing(
        self, validated_manager, field, default
    ) -> None:
        # The whole point of this test is to pin the pydantic path's
        # behavior. If pydantic isn't importable the test is meaningless
        # (we'd be silently exercising the unvalidated path). Skip with a
        # clear reason so CI without pydantic doesn't report a misleading
        # failure.
        from lib.config_manager import PYDANTIC_AVAILABLE
        if not PYDANTIC_AVAILABLE:
            pytest.skip("pydantic not installed; pydantic-path test not applicable")
        # Set the field to a non-default value, then load a config that
        # does NOT include this field. The pydantic path should reset to
        # the model default.
        sentinel = object()
        current = getattr(validated_manager.config, field, sentinel)
        if current is sentinel:
            pytest.skip(f"Field {field!r} is not on self.config")

        # Choose a non-default sentinel value. The dispatch also covers
        # ``None`` -- this happens for Optional[str] fields whose
        # current value is None (e.g. pre/post_launch_failure_mode_default
        # on a fresh manager). A non-None stale value lets us prove the
        # field was actually reset, not just left as None.
        if isinstance(current, bool):
            setattr(validated_manager.config, field, not current)
        elif isinstance(current, int):
            setattr(validated_manager.config, field, 99)
        elif isinstance(current, str):
            setattr(validated_manager.config, field, "stale-string")
        elif current is None:
            setattr(validated_manager.config, field, NONE_TYPED_STALE)
        else:
            pytest.skip(f"Field {field!r} type {type(current).__name__} not handled")

        # Load a config that omits this field entirely.
        validated_manager._parse_config_data({})

        assert getattr(validated_manager.config, field) == default, (
            f"Expected {field!r} to reset to pydantic default {default!r}, "
            f"got {getattr(validated_manager.config, field)!r}"
        )

    @pytest.mark.parametrize(
        "field,expected_default", list(UNVALIDATED_DEFAULTS.items())
    )
    def test_unvalidated_path_uses_hardcoded_default_when_field_missing(
        self, unvalidated_manager, field, expected_default
    ) -> None:
        # Three fields (hook_failure_mode_default, pre_*, post_*) use
        # hardcoded defaults in the unvalidated path. The other six use
        # self.config.x to preserve the previous value. Document both
        # behaviors so any change is intentional.
        sentinel = object()
        current = getattr(unvalidated_manager.config, field, sentinel)
        if current is sentinel:
            pytest.skip(f"Field {field!r} is not on self.config")

        if isinstance(current, bool):
            stale_value = not current
        elif isinstance(current, int):
            stale_value = 99
        elif isinstance(current, str):
            stale_value = "stale-string"
        elif current is None:
            # Optional[str] field whose current value is None. Use a
            # non-None stale value so we can tell "reset to default"
            # apart from "left alone".
            stale_value = NONE_TYPED_STALE
        else:
            pytest.skip(f"Field {field!r} type {type(current).__name__} not handled")

        setattr(unvalidated_manager.config, field, stale_value)
        unvalidated_manager._parse_config_data({})

        if PRESERVES_PREVIOUS_VALUE[field]:
            assert getattr(unvalidated_manager.config, field) == stale_value, (
                f"Expected {field!r} to keep stale value {stale_value!r}, "
                f"but it became {getattr(unvalidated_manager.config, field)!r}. "
                f"This means the unvalidated path behavior changed -- update this test."
            )
        else:
            assert getattr(unvalidated_manager.config, field) == expected_default, (
                f"Expected {field!r} to reset to hardcoded default {expected_default!r}, "
                f"but it kept stale value {getattr(unvalidated_manager.config, field)!r}. "
                f"This means the unvalidated path behavior changed -- update this test."
            )


class TestUnvalidatedPathDoesNotSwallowUnexpectedErrors:
    """The unvalidated path catches only SecurityValidationError, not
    bare ValueError, so unrelated errors propagate."""

    def test_unexpected_value_error_propagates(self, unvalidated_manager) -> None:
        # If a future refactor adds an int() parse or other call in the
        # unvalidated path that raises a bare ValueError, it should NOT
        # be silently re-labeled as a ConfigValidationError.
        with patch.object(
            unvalidated_manager, "_apply_unvalidated_config",
            side_effect=ValueError("unrelated programming error"),
        ):
            with pytest.raises(ValueError) as exc_info:
                unvalidated_manager._parse_config_data({})
        assert "unrelated programming error" in str(exc_info.value)
        assert not isinstance(exc_info.value, type(__import__("lib.config_manager", fromlist=["ConfigValidationError"]).ConfigValidationError))

    def test_security_validation_error_is_wrapped(
        self, unvalidated_manager
    ) -> None:
        # The safety check errors ARE SecurityValidationError, and those
        # SHOULD be wrapped as ConfigValidationError.
        from lib.config_manager import ConfigValidationError

        with pytest.raises(ConfigValidationError):
            unvalidated_manager._parse_config_data(
                {"global_preferences": {"custom_args": ["--filesystem=;rm"]}}
            )
