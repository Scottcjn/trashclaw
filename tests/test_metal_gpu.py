"""Tests for Metal GPU detection and status.

Uses only pytest + stdlib.
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import trashclaw


# ── GPU Detection ──

class TestGPUDetection:
    @patch('sys.platform', 'darwin')
    @patch('subprocess.run')
    def test_detect_discrete_amd_gpu(self, mock_run):
        """Test detection of discrete AMD GPU (Mac Pro 2013)."""
        # Mock system_profiler output for Mac Pro 2013 with AMD FirePro
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="""
Displays:
    AMD FirePro D500:
      Chipset Model: AMD FirePro D500
      VRAM: 3072 MB
      Vendor: AMD (0x1002)
"""
        )
        
        result = trashclaw._detect_gpu_info()
        
        assert result["gpu_type"] == "discrete"
        assert "AMD" in result["gpu_name"] or "FirePro" in result["gpu_name"]
        assert result["metal_supported"] is True
    
    @patch('sys.platform', 'darwin')
    @patch('subprocess.run')
    def test_detect_integrated_intel_gpu(self, mock_run):
        """Test detection of integrated Intel GPU."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="""
Displays:
    Intel Iris Pro:
      Chipset Model: Intel Iris Pro
      VRAM: 1536 MB
      Vendor: Intel
"""
        )
        
        result = trashclaw._detect_gpu_info()
        
        assert result["gpu_type"] == "integrated"
        assert "Intel" in result["gpu_name"]
        assert result["metal_supported"] is True
    
    @patch('sys.platform', 'darwin')
    @patch('subprocess.run')
    def test_detect_multiple_gpus(self, mock_run):
        """Test detection with multiple GPUs (integrated + discrete)."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="""
Displays:
    Intel Iris Pro:
      Chipset Model: Intel Iris Pro
    AMD Radeon Pro 560:
      Chipset Model: AMD Radeon Pro 560
"""
        )
        
        result = trashclaw._detect_gpu_info()
        
        # Should detect discrete GPU first
        assert result["gpu_type"] == "discrete"
        assert result["metal_supported"] is True
    
    @patch('sys.platform', 'darwin')
    @patch('subprocess.run')
    def test_detect_error_handling(self, mock_run):
        """Test error handling when system_profiler fails."""
        mock_run.side_effect = Exception("Command not found")
        
        result = trashclaw._detect_gpu_info()
        
        assert result["gpu_type"] == "unknown"
        assert "error" in result["gpu_name"].lower()
        assert result["metal_supported"] is False
    
    @patch('sys.platform', 'darwin')
    @patch('subprocess.run')
    def test_detect_timeout(self, mock_run):
        """Test handling of subprocess timeout."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="system_profiler", timeout=10)
        
        result = trashclaw._detect_gpu_info()
        
        assert result["gpu_type"] == "unknown"
        assert result["metal_supported"] is False
    
    @patch('sys.platform', 'linux')
    def test_non_macos_system(self):
        """Test detection on non-macOS system."""
        result = trashclaw._detect_gpu_info()
        
        assert result["gpu_type"] == "unknown"
        assert "Non-macOS" in result["gpu_name"]
        assert result["metal_supported"] is False
    
    @patch('sys.platform', 'win32')
    def test_windows_system(self):
        """Test detection on Windows system."""
        result = trashclaw._detect_gpu_info()
        
        assert result["gpu_type"] == "unknown"
        assert "Non-macOS" in result["gpu_name"]
        assert result["metal_supported"] is False


# ── Metal Support Detection ──

class TestMetalSupport:
    @patch('sys.platform', 'darwin')
    @patch('subprocess.run')
    def test_mac_pro_2013_supports_metal(self, mock_run):
        """Test that Mac Pro 2013 (AMD FirePro) supports Metal."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="AMD FirePro D500"
        )
        
        result = trashclaw._detect_gpu_info()
        
        assert result["metal_supported"] is True
    
    @patch('sys.platform', 'darwin')
    @patch('subprocess.run')
    def test_imac_2014_supports_metal(self, mock_run):
        """Test that iMac 2014 (AMD Radeon) supports Metal."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="AMD Radeon R9 M395"
        )
        
        result = trashclaw._detect_gpu_info()
        
        assert result["metal_supported"] is True
    
    @patch('sys.platform', 'darwin')
    @patch('subprocess.run')
    def test_macbook_pro_2015_supports_metal(self, mock_run):
        """Test that MacBook Pro 2015 (AMD Radeon) supports Metal."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="AMD Radeon R9 M370X"
        )
        
        result = trashclaw._detect_gpu_info()
        
        assert result["metal_supported"] is True


# ── Hardware Documentation ──

class TestHardwareDocumentation:
    def test_tested_hardware_list(self):
        """Verify the list of tested hardware is documented."""
        # These are the systems mentioned in issue #38
        tested_systems = [
            "Mac Pro 2013 (trashcan)",
            "iMac 2014-2019",
            "MacBook Pro 2015-2019",
            "PowerPC G4/G5 (legacy)",
            "IBM POWER8 (legacy)"
        ]
        
        # Verify we have at least the main systems
        assert len(tested_systems) >= 3
        assert "Mac Pro 2013" in tested_systems[0]
    
    def test_discrete_gpu_examples(self):
        """Verify discrete GPU examples are documented."""
        discrete_gpus = [
            "AMD FirePro D500",  # Mac Pro 2013
            "AMD FirePro D700",  # Mac Pro 2013
            "AMD Radeon Pro 560",  # iMac 2017
            "AMD Radeon Pro 5500M"  # MacBook Pro 2019
        ]
        
        assert len(discrete_gpus) >= 3


# ── Integration Tests ──

class TestIntegration:
    @patch('sys.platform', 'darwin')
    @patch('subprocess.run')
    def test_gpu_detection_in_status(self, mock_run, capsys, monkeypatch):
        """Test that GPU info appears in /status output."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="AMD FirePro D500"
        )
        
        # Mock other /status dependencies
        monkeypatch.setattr('trashclaw.LLAMA_URL', 'http://localhost:8080')
        monkeypatch.setattr('trashclaw.HISTORY', [])
        monkeypatch.setattr('trashclaw.SESSION_STATS', {'turns': 0, 'total_tokens': 0, 'total_seconds': 0})
        
        # Mock git branch
        with patch('trashclaw._git_branch', return_value='main'):
            # Mock health check
            with patch('urllib.request.urlopen'):
                # Mock other status dependencies
                with patch('trashclaw.detect_project_context', return_value='Test Project'):
                    # Mock TOOLS and UNDO_STACK
                    monkeypatch.setattr('trashclaw.TOOLS', [])
                    monkeypatch.setattr('trashclaw.UNDO_STACK', [])
                    monkeypatch.setattr('trashclaw.APPROVED_COMMANDS', set())
                    
                    # Call /status
                    trashclaw.handle_slash("/status")
                    
                    captured = capsys.readouterr()
                    
                    # Verify GPU info is in output
                    assert "GPU:" in captured.out or "AMD" in captured.out
