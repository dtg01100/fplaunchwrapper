#!/usr/bin/env python3
"""Test script to verify cron interval configuration functionality"""

from lib.config_manager import create_config_manager, EnhancedConfigManager
from lib.systemd_setup import SystemdSetup

def test_config_manager():
    print("=== Testing Config Manager ===")
    config = create_config_manager()
    
    # Test default value
    default_interval = config.get_cron_interval()
    print(f"Default cron interval: {default_interval} hours")
    assert default_interval == 6, "Default interval should be 6 hours"
    
    # Test setting and getting
    new_interval = 4
    config.set_cron_interval(new_interval)
    retrieved = config.get_cron_interval()
    print(f"After setting to {new_interval} hours: {retrieved} hours")
    assert retrieved == new_interval, "Should retrieve the set value"
    
    # Test minimum interval validation
    try:
        config.set_cron_interval(0)
        assert False, "Should raise ValueError for interval < 1"
    except ValueError as e:
        print(f"Correctly raised ValueError for interval < 1: {e}")
    
    # Reset to default
    config.set_cron_interval(6)
    assert config.get_cron_interval() == 6, "Should reset to default"
    print("✓ Config manager tests passed")


def test_systemd_setup():
    print("\n=== Testing Systemd Setup ===")
    setup = SystemdSetup(emit_mode=True)
    
    # Test that install_cron_job accepts interval parameter
    try:
        result = setup.install_cron_job(cron_interval=4)
        assert result == True, "Should return True in emit mode"
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