
import subprocess
import os

def test_path_check(tmp_path, capsys):
    # Print PATH from within test
    print(f"PATH inside test: {os.environ['PATH'][:200]}...")
    
    # Check if mock_bin is in PATH
    has_mock = 'mock_bin' in os.environ['PATH']
    print(f"Has mock_bin in PATH: {has_mock}")
    
    # Call flatpak to see which one gets used
    result = subprocess.run(['flatpak', '--version'], capture_output=True, text=True)
    print(f"flatpak version output: {result.stdout}")
    print(f"flatpak version stderr: {result.stderr}")
