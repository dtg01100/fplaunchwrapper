#!/usr/bin/env python3
"""Test script to verify cron interval configuration functionality"""

import pytest
from lib.config_manager import create_config_manager
from lib.systemd_setup import SystemdSetup


def test_config_manager(isolated_home):
    """Test configuration manager with isolated environment."""
    print("=== Testing Config Manager ===")
    config = create_config_manager()
    config.config_dir = isolated_home.config_dir

    default_interval = config.get_cron_interval()
    print(f"Default cron interval: {default_interval} hours")
    assert default_interval == 6, "Default interval should be 6 hours"

    new_interval = 4
    config.set_cron_interval(new_interval)
    retrieved = config.get_cron_interval()
    print(f"After setting to {new_interval} hours: {retrieved} hours")
    assert retrieved == new_interval, "Should retrieve the set value"

    with pytest.raises(ValueError):
        config.set_cron_interval(0)

    config.set_cron_interval(6)
    assert config.get_cron_interval() == 6, "Should reset to default"
    print("✓ Config manager tests passed")


def test_systemd_setup(isolated_home):
    """Test systemd setup with isolated environment."""
    print("\n=== Testing Systemd Setup ===")
    setup = SystemdSetup(emit_mode=True)

    try:
        result = setup.install_cron_job(cron_interval=4)
        assert result, "Should return True in emit mode"
        print("✓ SystemdSetup.install_cron_job accepts interval parameter")
    except Exception as e:
        print(f"✗ Error: {e}")
        raise


if __name__ == "__main__":
    try:
        test_config_manager()
        test_systemd_setup()
        print("\n✅ All tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        print(traceback.format_exc())
