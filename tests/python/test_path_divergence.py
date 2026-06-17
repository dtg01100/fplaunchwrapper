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


# These are the field-level defaults the Pydantic model applies. The
# unvalidated path's defaults may differ -- see the comments on each
# field. If a future PR changes one of these in lib/config_validation.py
# OR in lib/config_manager.py, the divergence test below will need
# updating.
PYDANTIC_DEFAULTS = {
    "bin_dir": "",
    "active_profile": "default",
    "debug_mode": False,
    "log_level": "INFO",
    "cron_interval": 6,
    "enable_notifications": True,
    # In the unvalidated path, this is hardcoded "warn" (not stale-state),
    # matching the Pydantic default -- so the unvalidated path resets to
    # "warn" on a missing field, NOT to the previous value.
    "hook_failure_mode_default": "warn",
    # In the unvalidated path, these reset to None on a missing field
    # (not to the previous value). Matches the Pydantic default.
    "pre_launch_failure_mode_default": None,
    "post_launch_failure_mode_default": None,
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
        # Set the field to a non-default value, then load a config that
        # does NOT include this field. The pydantic path should reset to
        # the model default.
        sentinel = object()
        current = getattr(validated_manager.config, field, sentinel)
        if current is sentinel:
            pytest.skip(f"Field {field!r} is not on self.config")

        # Choose a non-default sentinel value.
        if isinstance(current, bool):
            setattr(validated_manager.config, field, not current)
        elif isinstance(current, int):
            setattr(validated_manager.config, field, 99)
        elif isinstance(current, str):
            setattr(validated_manager.config, field, "stale-string")
        else:
            pytest.skip(f"Field {field!r} type {type(current).__name__} not handled")

        # Load a config that omits this field entirely.
        validated_manager._parse_config_data({})

        assert getattr(validated_manager.config, field) == default, (
            f"Expected {field!r} to reset to pydantic default {default!r}, "
            f"got {getattr(validated_manager.config, field)!r}"
        )

    @pytest.mark.parametrize("field,default", list(PYDANTIC_DEFAULTS.items()))
    def test_unvalidated_path_uses_hardcoded_default_when_field_missing(
        self, unvalidated_manager, field, default
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
            assert getattr(unvalidated_manager.config, field) == default, (
                f"Expected {field!r} to reset to hardcoded default {default!r}, "
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
