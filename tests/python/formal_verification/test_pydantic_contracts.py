"""Phase 14: Pydantic contract verification.

These tests verify the runtime contracts encoded in the Pydantic models at
``lib/config_validation.py`` -- the ones the rest of the suite relies on
indirectly (via ``load_config()``) but never exercises directly. A future
PR that silently weakens one of these constraints will be caught here.

Coverage dimensions:

1. **Direct-construction boundary tests**: every ``pattern=`` and ``ge=``
   constraint on ``PydanticWrapperConfig`` and ``PydanticAppPreferences``
   is enforced for both valid and invalid values.

2. **End-to-end round-trip**: hostile TOML files fed to
   ``EnhancedConfigManager.load_config()`` raise ``ConfigValidationError``
   via the pydantic path, regardless of which field the constraint lives
   on.

3. **Cross-path agreement on security-critical fields**: already covered
   by ``tests/python/test_unvalidated_security.py``. These tests
   additionally pin down the **documented divergence** on non-security
   fields (log_level / cron_interval / notification_level / launch_method
   pattern): the unvalidated path is silent on these. The tests assert
   that documented contract so a future regression that accidentally
   starts enforcing it (or stops documenting it) is flagged.

4. **Deduplicated-import contract**: ``lib.config_manager`` re-exports
   the same pydantic objects as ``lib.config_validation``. After the
   refactor that removes the duplicated ``try/except`` import block,
   ``config_manager.BaseModel`` etc. MUST be the same object as
   ``config_validation.BaseModel`` -- otherwise callers that compare
   ``type(exc) is config_manager.ValidationError`` would silently break.
"""
from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

pytest.importorskip("pydantic")

from lib.config_manager import (  # noqa: E402
    EnhancedConfigManager,
    PYDANTIC_AVAILABLE,
)
from lib.config_validation import (  # noqa: E402
    PydanticAppPreferences,
    PydanticWrapperConfig,
)


# ---------------------------------------------------------------------------
# 1. Direct-construction boundary tests
# ---------------------------------------------------------------------------


class TestLaunchMethodPattern:
    """``PydanticAppPreferences.launch_method`` enforces
    ``^(auto|system|flatpak)$``."""

    @pytest.mark.parametrize("good", ["auto", "system", "flatpak"])
    def test_accepts_valid(self, good: str) -> None:
        prefs = PydanticAppPreferences(launch_method=good)
        assert prefs.launch_method == good

    @pytest.mark.parametrize(
        "bad",
        [
            "AUTO",  # case-sensitive
            "Flatpak",  # case-sensitive
            "auto ",  # trailing whitespace
            " auto",  # leading whitespace
            "auto\n",  # trailing newline (Bug #14 territory)
            "auto;system",  # injection
            "",  # empty (matches pattern but is rejected by other validators? -- here pattern is permissive)
            "systemx",  # superset
        ],
    )
    def test_rejects_invalid(self, bad: str) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            PydanticAppPreferences(launch_method=bad)


class TestLogLevelPattern:
    """``PydanticWrapperConfig.log_level`` enforces
    ``^(DEBUG|INFO|WARN|ERROR)$``."""

    @pytest.mark.parametrize("good", ["DEBUG", "INFO", "WARN", "ERROR"])
    def test_accepts_valid(self, good: str) -> None:
        cfg = PydanticWrapperConfig(log_level=good)
        assert cfg.log_level == good

    @pytest.mark.parametrize(
        "bad",
        ["debug", "info", "warn", "error", "TRACE", "FATAL", "DEBG", "", "INFO; rm -rf /"],
    )
    def test_rejects_invalid(self, bad: str) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            PydanticWrapperConfig(log_level=bad)


class TestNotificationLevelPattern:
    """``PydanticWrapperConfig.notification_level`` enforces
    ``^(debug|info|warning|error|none)$``."""

    @pytest.mark.parametrize(
        "good", ["debug", "info", "warning", "error", "none"]
    )
    def test_accepts_valid(self, good: str) -> None:
        cfg = PydanticWrapperConfig(notification_level=good)
        assert cfg.notification_level == good

    @pytest.mark.parametrize(
        "bad", ["DEBUG", "warn", "fatal", "off", "all", " warning", ""]
    )
    def test_rejects_invalid(self, bad: str) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            PydanticWrapperConfig(notification_level=bad)


class TestGeConstraints:
    """``ge=`` constraints on integer fields are enforced at exactly the
    boundary, including the rejection of negative values."""

    @pytest.mark.parametrize(
        "field",
        [
            "schema_version",
            "cron_interval",
            "update_check_interval",
            "launch_timeout",
            "log_rotation_size",
            "log_retention_days",
        ],
    )
    @pytest.mark.parametrize("good", [1, 2, 100])
    def test_ge_field_accepts_at_or_above_minimum(self, field: str, good: int) -> None:
        cfg = PydanticWrapperConfig(**{field: good})
        assert getattr(cfg, field) == good

    @pytest.mark.parametrize(
        "field,minimum",
        [
            ("schema_version", 0),
            ("cron_interval", 1),
            ("update_check_interval", 1),
            ("launch_timeout", 1),
            ("log_rotation_size", 1),
            ("log_retention_days", 1),
        ],
    )
    @pytest.mark.parametrize("bad", [-1, -100])
    def test_ge_field_rejects_below_minimum(
        self, field: str, minimum: int, bad: int
    ) -> None:
        from pydantic import ValidationError

        if bad >= minimum:
            pytest.skip("not actually below minimum")
        with pytest.raises(ValidationError):
            PydanticWrapperConfig(**{field: bad})

    @pytest.mark.parametrize(
        "field,minimum",
        [
            ("schema_version", 0),
            ("cron_interval", 1),
            ("update_check_interval", 1),
            ("launch_timeout", 1),
            ("log_rotation_size", 1),
            ("log_retention_days", 1),
        ],
    )
    def test_ge_field_rejects_below_minimum_by_one(self, field: str, minimum: int) -> None:
        """Off-by-one boundary: ``minimum - 1`` is rejected."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            PydanticWrapperConfig(**{field: minimum - 1})

    @pytest.mark.parametrize(
        "field,minimum",
        [
            ("schema_version", 0),
            ("cron_interval", 1),
            ("update_check_interval", 1),
            ("launch_timeout", 1),
            ("log_rotation_size", 1),
            ("log_retention_days", 1),
        ],
    )
    def test_ge_field_accepts_exact_minimum(self, field: str, minimum: int) -> None:
        """Boundary: ``minimum`` is accepted."""
        cfg = PydanticWrapperConfig(**{field: minimum})
        assert getattr(cfg, field) == minimum


# ---------------------------------------------------------------------------
# 2. End-to-end hostile TOML round-trip
# ---------------------------------------------------------------------------


class TestLoadConfigRejectsHostileToml:
    """``load_config()`` rejects hostile TOML via the pydantic path."""

    @pytest.fixture
    def manager(self) -> EnhancedConfigManager:
        with tempfile.TemporaryDirectory() as tmp:
            yield EnhancedConfigManager(config_dir=Path(tmp))

    @pytest.mark.parametrize(
        "toml_text,description",
        [
            ("log_level = 'BOGUS'\n", "invalid log_level"),
            ("log_level = 'debug'\n", "wrong-case log_level"),
            ("cron_interval = 0\n", "cron_interval below 1"),
            ("cron_interval = -1\n", "negative cron_interval"),
            ("update_check_interval = 0\n", "update_check_interval below 1"),
            ("launch_timeout = 0\n", "launch_timeout below 1"),
            ("log_rotation_size = 0\n", "log_rotation_size below 1"),
            ("log_retention_days = 0\n", "log_retention_days below 1"),
            ("notification_level = 'fatal'\n", "invalid notification_level"),
            (
                "[global_preferences]\nlaunch_method = 'AUTO'\n",
                "wrong-case launch_method",
            ),
            (
                "[global_preferences]\ncustom_args = ['--flag;rm -rf /']\n",
                "dangerous char in custom_args",
            ),
            (
                "[global_preferences]\npre_launch_failure_mode = 'bogus'\n",
                "invalid hook failure mode",
            ),
        ],
    )
    def test_rejects(
        self, manager: EnhancedConfigManager, toml_text: str, description: str
    ) -> None:
        from lib.exceptions import ConfigValidationError

        manager.config_file.write_text(toml_text)
        manager.config_file.chmod(0o600)
        with pytest.raises(ConfigValidationError):
            manager.load_config()

    def test_pydantic_path_uses_pydanticwrapperconfig(
        self, manager: EnhancedConfigManager
    ) -> None:
        """When ``PYDANTIC_AVAILABLE`` is True, the pydantic path is used.

        This is the assumption the rest of these tests rely on. If a
        future change flips the pydantic import to a shim, the
        pattern-based constraints will silently stop firing -- and this
        test is the canary.
        """
        assert PYDANTIC_AVAILABLE is True
        # Sanity: load_config on a known-bad value raises with a pydantic-
        # flavored error path (ConfigValidationError, not silent pass).
        manager.config_file.write_text("log_level = 'BOGUS'\n")
        manager.config_file.chmod(0o600)
        from lib.exceptions import ConfigValidationError

        with pytest.raises(ConfigValidationError):
            manager.load_config()


# ---------------------------------------------------------------------------
# 3. Documented divergence: pydantic-vs-unvalidated on non-security fields
# ---------------------------------------------------------------------------


class TestDocumentedPydanticOnlyConstraints:
    """The unvalidated path is documented to skip pydantic-only field
    constraints (``log_level`` pattern, ``cron_interval`` ``ge=``,
    ``notification_level`` pattern, ``launch_method`` pattern).

    These tests pin that contract: the unvalidated path *silently
    accepts* values the pydantic path rejects. If a future change makes
    the unvalidated path enforce these constraints, the tests in
    ``TestUnvalidatedPathIsSilentOnPydanticOnlyFields`` would fail --
    but that is a desirable outcome and should prompt a documentation
    update rather than a test deletion. Conversely, if the pydantic
    path stops enforcing them, ``TestPydanticPathEnforcesFieldConstraints``
    would fail.

    The current contract (preserved here) is:

    - Security-critical constraints are enforced in BOTH paths
      (already covered by ``test_unvalidated_security.py``).
    - Non-security pydantic-only constraints are enforced ONLY in the
      pydantic path.
    """

    @pytest.fixture
    def unvalidated_manager(self) -> EnhancedConfigManager:
        with tempfile.TemporaryDirectory() as tmp:
            import lib.config_manager as cm

            with patch.object(cm, "PYDANTIC_AVAILABLE", False), patch.object(
                cm, "PydanticWrapperConfig", None
            ):
                yield EnhancedConfigManager(config_dir=Path(tmp))

    @pytest.fixture
    def validated_manager(self) -> EnhancedConfigManager:
        with tempfile.TemporaryDirectory() as tmp:
            yield EnhancedConfigManager(config_dir=Path(tmp))

    @pytest.mark.parametrize(
        "data,field,invalid_value",
        [
            ({"log_level": "BOGUS"}, "log_level", "BOGUS"),
            ({"log_level": "trace"}, "log_level", "trace"),
            ({"cron_interval": 0}, "cron_interval", 0),
            ({"cron_interval": -7}, "cron_interval", -7),
            ({"update_check_interval": 0}, "update_check_interval", 0),
            ({"launch_timeout": 0}, "launch_timeout", 0),
            ({"log_rotation_size": 0}, "log_rotation_size", 0),
            ({"log_retention_days": 0}, "log_retention_days", 0),
            ({"notification_level": "FATAL"}, "notification_level", "FATAL"),
            (
                {"global_preferences": {"launch_method": "AUTO"}},
                "launch_method",
                "AUTO",
            ),
        ],
    )
    def test_pydantic_path_enforces_field_constraints(
        self,
        validated_manager: EnhancedConfigManager,
        data: dict,
        field: str,
        invalid_value: object,
    ) -> None:
        """The pydantic path raises ConfigValidationError on every
        pydantic-only constraint, regardless of whether the field is
        security-critical."""
        from lib.exceptions import ConfigValidationError

        with pytest.raises(ConfigValidationError):
            validated_manager._parse_config_data(data)

    @pytest.mark.parametrize(
        "data,field,invalid_value",
        [
            ({"log_level": "BOGUS"}, "log_level", "BOGUS"),
            ({"log_level": "trace"}, "log_level", "trace"),
            ({"cron_interval": 0}, "cron_interval", 0),
            ({"cron_interval": -7}, "cron_interval", -7),
        ],
    )
    def test_unvalidated_path_is_silent_on_pydantic_only_fields(
        self,
        unvalidated_manager: EnhancedConfigManager,
        data: dict,
        field: str,
        invalid_value: object,
    ) -> None:
        """The unvalidated path silently accepts these values.

        This is the **documented** behavior, not a bug. If the test
        starts failing, the divergence has changed -- and either the
        documentation or the unvalidated path needs to be updated.
        """
        unvalidated_manager._parse_config_data(data)
        assert getattr(unvalidated_manager.config, field) == invalid_value


# ---------------------------------------------------------------------------
# 4. Re-export contract (post-refactor)
# ---------------------------------------------------------------------------


class TestConfigManagerValidationErrorIsThePydanticOne:
    """``lib.config_manager.ValidationError`` MUST be the actual pydantic
    ``ValidationError`` class, not a shim.

    The pydantic and unvalidated paths in ``_parse_config_data`` both use
    this name to ``except`` over Pydantic's own validation errors. If
    ``config_manager.ValidationError`` were a stub or the wrong class,
    real pydantic errors would propagate as ``ConfigParseError`` instead
    of ``ConfigValidationError``, defeating the entire two-path safety
    model.
    """

    def test_validation_error_is_pydantic_validation_error(self) -> None:
        import lib.config_manager as cm
        from pydantic import ValidationError as PydanticValidationError

        assert cm.ValidationError is PydanticValidationError

    def test_validation_error_re_exported_from_config_validation(self) -> None:
        """``config_manager`` re-exports the same object as
        ``config_validation`` -- not a copy or subclass."""
        import lib.config_manager as cm
        import lib.config_validation as cv

        assert cm.ValidationError is cv.ValidationError

    def test_pydantic_app_preferences_re_export(self) -> None:
        """``PydanticAppPreferences`` is re-exported for tests."""
        import lib.config_manager as cm
        import lib.config_validation as cv

        assert cm.PydanticAppPreferences is cv.PydanticAppPreferences

    def test_pydantic_available_flag_consistent(self) -> None:
        """``PYDANTIC_AVAILABLE`` agrees across modules."""
        import lib.config_manager as cm
        import lib.config_validation as cv

        assert cm.PYDANTIC_AVAILABLE == cv.PYDANTIC_AVAILABLE
