from pathlib import Path


def test_required_keeper_suite_files_tripwire_still_sees_expected_files():
    test_dir = Path(__file__).resolve().parent

    assert (test_dir / "test_regression_fixes.py").exists(), (
        "lightweight tripwire expected file test_regression_fixes.py to be present"
    )
    assert (test_dir / "test_missing_cli_coverage.py").exists(), (
        "lightweight tripwire expected file test_missing_cli_coverage.py to be present"
    )
    assert (test_dir / "test_subcommands_no_crash.py").exists(), (
        "lightweight tripwire expected file test_subcommands_no_crash.py to be present"
    )


def test_keeper_suite_anchor_name_tripwire_matches_textually():
    test_dir = Path(__file__).resolve().parent
    keeper_suite_anchor_test_names = {
        "test_regression_fixes.py": [
            "test_sensitive_directories_are_rejected",
            "test_pref_alias_invokes_set_pref_logic",
        ],
        "test_missing_cli_coverage.py": [
            "test_manifest_calls_flatpak_correctly",
        ],
        "test_subcommands_no_crash.py": [
            "test_help_pages_return_zero",
        ],
    }

    for filename, test_names in keeper_suite_anchor_test_names.items():
        contents = (test_dir / filename).read_text(encoding="utf-8")
        for test_name in test_names:
            assert f"def {test_name}" in contents, (
                f"lightweight textual tripwire expected {filename} to retain anchor name {test_name}"
            )


def test_tests_readme_mentions_pytest_and_not_deleted_files():
    readme = (Path(__file__).resolve().parents[1] / "README.md").read_text()

    assert "pytest tests/python -v" in readme
    assert "test_comprehensive.py" not in readme
    assert "test_focused.py" not in readme
