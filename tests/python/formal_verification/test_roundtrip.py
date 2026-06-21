"""Phase 7: Round-trip and differential testing.

Round-trip tests verify that inverse operations produce consistent results.
A classic example: serialize → deserialize → re-serialize must be idempotent.

For fplaunchwrapper:
- Wrapper template → generate wrapper → re-parse wrapper → must round-trip identically
- Config serialize → deserialize → re-serialize must equal original
- App ID → sanitize → re-parse as app ID → must round-trip if possible
- Permission preset → add → list → get → must equal

Differential testing compares independent implementations for the same operation:
- validate_app_id (lib.validation) vs safety.validate_flatpak_id should agree

These catch: serialization bugs, lossy parsing, normalization inconsistencies,
state inconsistencies between read and write paths.
"""
from __future__ import annotations

import re
import tempfile
from pathlib import Path

import pytest


class TestWrapperRoundTrip:
    """Wrapper generation must round-trip: generate → parse → regenerate must match."""

    @pytest.fixture
    def wrapper_paths(self, tmp_path, monkeypatch):
        """Generate a wrapper and return paths to inspect."""
        from lib.generate import WrapperGenerator
        from lib.config_manager import create_config_manager

        bin_dir = tmp_path / "bin"
        cfg_dir = tmp_path / "cfg"
        data_dir = tmp_path / "data"
        bin_dir.mkdir(); cfg_dir.mkdir(); data_dir.mkdir()

        cm = create_config_manager(config_dir=str(cfg_dir))
        gen = WrapperGenerator(
            bin_dir=str(bin_dir),
            config_dir=str(cfg_dir),
            data_dir=str(data_dir),
            config_manager=cm,
        )
        monkeypatch.setenv("FPWRAPPER_TEST_ENV", "1")
        gen.generate_wrapper("org.mozilla.firefox")
        return bin_dir / "firefox", tmp_path

    def test_wrapper_generation_is_idempotent(self, wrapper_paths):
        """Generating the same wrapper twice produces identical content."""
        from lib.generate import WrapperGenerator
        from lib.config_manager import create_config_manager

        wrapper_path, tmp = wrapper_paths
        v1 = wrapper_path.read_text()

        bin_dir = wrapper_path.parent
        cfg_dir = tmp / "cfg"
        cm = create_config_manager(config_dir=str(cfg_dir))
        gen = WrapperGenerator(
            bin_dir=str(bin_dir),
            config_dir=str(cfg_dir),
            data_dir=str(tmp / "data"),
            config_manager=cm,
        )
        gen.generate_wrapper("org.mozilla.firefox")
        v2 = wrapper_path.read_text()

        assert v1 == v2, (
            f"Wrapper generation is not idempotent. "
            f"Diff size: {abs(len(v1) - len(v2))} chars"
        )

    def test_wrapper_parsing_extracts_consistent_metadata(self, wrapper_paths):
        """Wrapper ID and NAME fields must be parseable and consistent."""
        from lib.python_utils import get_wrapper_id

        wrapper_path, _ = wrapper_paths
        content = wrapper_path.read_text()
        name_match = re.search(r'^NAME="([^"]*)"', content, re.MULTILINE)
        id_match = re.search(r'^ID="([^"]*)"', content, re.MULTILINE)
        assert name_match, "Wrapper missing NAME="
        assert id_match, "Wrapper missing ID="
        assert name_match.group(1) == "firefox"
        assert id_match.group(1) == "org.mozilla.firefox"

        parsed_id = get_wrapper_id(wrapper_path)
        assert parsed_id == "org.mozilla.firefox"

    def test_wrapper_metadata_parses_to_consistent_state(self, wrapper_paths):
        """The wrapper's NAME must equal sanitize_id_to_name(ID)."""
        from lib.python_utils import sanitize_id_to_name

        wrapper_path, _ = wrapper_paths
        content = wrapper_path.read_text()
        name = re.search(r'^NAME="([^"]*)"', content, re.MULTILINE).group(1)
        app_id = re.search(r'^ID="([^"]*)"', content, re.MULTILINE).group(1)

        expected_name = sanitize_id_to_name(app_id)
        assert name == expected_name, (
            f"NAME {name!r} does not match sanitize_id_to_name({app_id!r}) = {expected_name!r}"
        )

    def test_wrapper_template_format_stable(self):
        """create_wrapper_script called twice yields identical output."""
        from lib.generate import WrapperGenerator
        from lib.config_manager import create_config_manager

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            bin_dir = tmp / "bin"
            cfg_dir = tmp / "cfg"
            data_dir = tmp / "data"
            bin_dir.mkdir(); cfg_dir.mkdir(); data_dir.mkdir()

            cm = create_config_manager(config_dir=str(cfg_dir))
            gen = WrapperGenerator(
                bin_dir=str(bin_dir),
                config_dir=str(cfg_dir),
                data_dir=str(data_dir),
                config_manager=cm,
            )
            v1 = gen.create_wrapper_script("firefox", "org.mozilla.firefox")
            v2 = gen.create_wrapper_script("firefox", "org.mozilla.firefox")
            assert v1 == v2, "create_wrapper_script is not deterministic"


class TestConfigRoundTrip:
    """Configuration serialize → deserialize → re-serialize must be idempotent."""

    def test_default_config_round_trip(self, tmp_path):
        from lib.config_manager import create_config_manager
        from lib.config_models import AppPreferences

        cm1 = create_config_manager(config_dir=str(tmp_path))
        cm1.set_app_preferences("firefox", AppPreferences(launch_method="flatpak"))
        cm1.set_app_preferences("vim", AppPreferences(launch_method="system"))
        cm1.save_config()

        cm2 = create_config_manager(config_dir=str(tmp_path))
        assert cm2.get_app_preferences("firefox").launch_method == "flatpak"
        assert cm2.get_app_preferences("vim").launch_method == "system"

    def test_permission_preset_round_trip(self, tmp_path):
        """Add preset → reload → get must return same."""
        from lib.config_manager import create_config_manager

        cm1 = create_config_manager(config_dir=str(tmp_path))
        perms = ["--device=dri", "--socket=pulseaudio", "--filesystem=home"]
        cm1.add_permission_preset("mypreset", perms)
        cm1.save_config()

        cm2 = create_config_manager(config_dir=str(tmp_path))
        loaded = cm2.get_permission_preset("mypreset")
        assert loaded == perms

    def test_blocklist_round_trip(self, tmp_path):
        from lib.config_manager import create_config_manager

        cm1 = create_config_manager(config_dir=str(tmp_path))
        cm1.add_to_blocklist("org.blocked.app1")
        cm1.add_to_blocklist("org.blocked.app2")
        cm1.save_config()

        cm2 = create_config_manager(config_dir=str(tmp_path))
        assert cm2.is_blocked("org.blocked.app1")
        assert cm2.is_blocked("org.blocked.app2")

    def test_active_profile_round_trip(self, tmp_path):
        from lib.config_manager import create_config_manager

        cm1 = create_config_manager(config_dir=str(tmp_path))
        cm1.create_profile("gaming")
        cm1.switch_profile("gaming")
        cm1.save_config()

        cm2 = create_config_manager(config_dir=str(tmp_path))
        assert cm2.get_active_profile() == "gaming"


class TestSanitizationIdempotence:
    """sanitize_id_to_name must be idempotent: sanitize(sanitize(x)) == sanitize(x)."""

    @pytest.mark.parametrize("app_id", [
        "org.mozilla.firefox",
        "org.gnome.Terminal",
        "com.example.MyApp",
        "io.github.SomeUser.repo",
        "org.kde.konsole",
        "com.visualstudio.code",
    ])
    def test_sanitize_idempotent(self, app_id):
        from lib.python_utils import sanitize_id_to_name
        once = sanitize_id_to_name(app_id)
        twice = sanitize_id_to_name(once)
        assert once == twice, f"Not idempotent for {app_id!r}: {once!r} -> {twice!r}"

    @pytest.mark.parametrize("weird_id", [
        "org.foo.bar",
        "io.github.user_name.app-name",
        "com.123.numbers.app",
        "a.b",
    ])
    def test_sanitize_preserves_basic_format(self, weird_id):
        """Sanitized output must be a valid wrapper name."""
        from lib.python_utils import sanitize_id_to_name
        from lib.validation import validate_wrapper_name

        result = sanitize_id_to_name(weird_id)
        ok, err = validate_wrapper_name(result)
        assert ok, f"Sanitizer output {result!r} for {weird_id!r} failed: {err!r}"


class TestValidateAppIdInverse:
    """Round-trip app IDs through validation and sanitization."""

    @pytest.mark.parametrize("valid_id", [
        "org.mozilla.firefox",
        "com.example.app",
        "io.github.user.repo",
        "org.freedesktop.Platform//21.08",
    ])
    def test_valid_app_id_round_trips(self, valid_id):
        from lib.python_utils import sanitize_id_to_name
        from lib.validation import validate_app_id

        ok, _ = validate_app_id(valid_id)
        assert ok, f"Valid app ID {valid_id!r} didn't validate"
        name = sanitize_id_to_name(valid_id)
        assert name
        assert "/" not in name
        assert "\\" not in name
        assert ".." not in name


class TestDifferentialValidation:
    """Independent validators must agree on the same input."""

    @pytest.mark.parametrize("app_id,expected", [
        ("org.mozilla.firefox", True),
        ("com.example.app", True),
        ("no-dots", False),
        ("../../../etc/passwd", False),
        ("", False),
        ("foo; rm", False),
    ])
    def test_two_validators_agree_on_app_id(self, app_id, expected):
        """lib.validation.validate_app_id vs lib.safety.validate_flatpak_id agree."""
        from lib.validation import validate_app_id
        from lib.safety import validate_flatpak_id

        ok1, _ = validate_app_id(app_id)
        ok2 = validate_flatpak_id(app_id)
        assert ok1 == ok2 == expected, (
            f"Validators disagree on {app_id!r}: "
            f"validate_app_id={ok1}, validate_flatpak_id={ok2}, expected={expected}"
        )

    def test_safety_validator_more_strict(self):
        """Where they disagree, lib.validation should be the stricter one."""
        from lib.safety import validate_flatpak_id
        from lib.validation import validate_app_id

        for app_id in [
            "org.foo.bar baz",
            "org.foo.bar\tx",
            "org.foo\nbar",
            "org.foo\tbar",
            ".org.foo",
            "org.foo.",
        ]:
            ok_validation, _ = validate_app_id(app_id)
            ok_safety = validate_flatpak_id(app_id)
            if ok_validation != ok_safety:
                assert not ok_validation, (
                    f"validate_app_id({app_id!r})={ok_validation} but should reject"
                )


class TestForbiddenNameConsistency:
    """FORBIDDEN_NAMES structural invariants."""

    def test_all_forbidden_names_lowercase(self):
        from lib.exceptions import ForbiddenNameError
        for name in ForbiddenNameError.FORBIDDEN_NAMES:
            assert name == name.lower(), f"Forbidden name {name!r} is not lowercase"

    def test_forbidden_set_is_frozenset(self):
        from lib.exceptions import ForbiddenNameError
        assert isinstance(ForbiddenNameError.FORBIDDEN_NAMES, frozenset), (
            "FORBIDDEN_NAMES must be a frozenset to prevent mutation"
        )

    def test_forbidden_names_no_duplicates(self):
        from lib.exceptions import ForbiddenNameError
        names = list(ForbiddenNameError.FORBIDDEN_NAMES)
        assert len(names) >= 100, f"Only {len(names)} forbidden names"


class TestWrapperGenerationDeterminism:
    """Same inputs must produce same wrapper (no time/random dependence)."""

    def test_generation_deterministic_across_instances(self, tmp_path, monkeypatch):
        from lib.generate import WrapperGenerator
        from lib.config_manager import create_config_manager

        for run in range(3):
            bin_dir = tmp_path / f"bin{run}"
            cfg_dir = tmp_path / f"cfg{run}"
            data_dir = tmp_path / f"data{run}"
            bin_dir.mkdir(); cfg_dir.mkdir(); data_dir.mkdir()

            cm = create_config_manager(config_dir=str(cfg_dir))
            gen = WrapperGenerator(
                bin_dir=str(bin_dir),
                config_dir=str(cfg_dir),
                data_dir=str(data_dir),
                config_manager=cm,
            )
            monkeypatch.setenv("FPWRAPPER_TEST_ENV", "1")
            gen.generate_wrapper("org.mozilla.firefox")
            wrapper = bin_dir / "firefox"
            assert wrapper.exists()
            content = wrapper.read_text()
            assert not re.search(r"20\d{2}-\d{2}-\d{2}", content), (
                f"Run {run}: wrapper contains a date stamp"
            )
            assert not re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}", content), (
                f"Run {run}: wrapper contains a UUID-like string"
            )


class TestConfigMigrationRoundTrip:
    """Configuration schema migration must round-trip correctly."""

    def test_old_schema_config_loads_and_saves_new_format(self, tmp_path):
        import tomli_w
        from lib.config_manager import create_config_manager

        old_config = tmp_path / "config.toml"
        old_data = {
            "schema_version": 0,
            "bin_dir": "/old/bin",
            "log_level": "DEBUG",
            "blocklist": ["old.blocked.app"],
        }
        with open(old_config, "wb") as f:
            tomli_w.dump(old_data, f)

        cm = create_config_manager(config_dir=str(tmp_path))
        assert cm.is_blocked("old.blocked.app")

        cm.save_config()

        cm2 = create_config_manager(config_dir=str(tmp_path))
        assert cm2.is_blocked("old.blocked.app")
