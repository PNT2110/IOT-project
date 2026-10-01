import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, r"c:\Users\pnt21\OneDrive\Máy tính\IOT\backend")
from app.serial_io import UsbPortCoordinator

def test_symlink_deduplication(tmp_path):
    # Create a real file and two symlinks to it
    real_device = tmp_path / "ttyUSB0"
    real_device.write_text("fake dev")
    
    symlink1 = tmp_path / "by-path-p1"
    try:
        symlink1.symlink_to(real_device)
        has_symlink = True
    except (OSError, NotImplementedError):
        has_symlink = False

    coord = UsbPortCoordinator()
    
    if has_symlink:
        # Mock comports returning the symlink, and glob returning the real device
        mock_p1 = MagicMock()
        mock_p1.device = str(symlink1)
        mock_p2 = MagicMock()
        mock_p2.device = str(real_device)

        with patch("serial.tools.list_ports.comports", return_value=[mock_p1, mock_p2]), \
             patch("glob.glob", return_value=[str(real_device)]):
            candidates = coord.find_candidate_ports()
            print("Found candidates with symlinks:", candidates)
            # Both must resolve to the same canonical path
            assert len(candidates) == 1, f"Expected 1 deduplicated candidate, got {candidates}"
            assert candidates[0] == str(real_device.resolve())
            print("Symlink resolution test passed with real symlink!")
    else:
        # Fallback simulation if Windows non-admin cannot create symlinks
        print("Symlink creation not permitted on this Windows user account; testing logic via mocks")
        p_mock = MagicMock()
        p_mock.device = "/dev/serial/by-path/test1"
        with patch("serial.tools.list_ports.comports", return_value=[p_mock]), \
             patch("pathlib.Path.is_symlink", return_value=True), \
             patch("pathlib.Path.resolve", return_value=Path("/dev/ttyUSB0")):
            candidates = coord.find_candidate_ports()
            print("Mocked symlink resolved to:", candidates)
            assert "/dev/ttyUSB0" in candidates

test_symlink_deduplication(Path(r"c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\reviewer_4\tmp_test"))
print("Symlink resolution verification complete.")
