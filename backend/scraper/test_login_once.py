#!/usr/bin/env python3
import pytest
from unittest.mock import Mock, patch
import sys
import os

class TestLoginOnce:
    """Unit tests for login_once.py with 100% coverage"""
    
    @patch('builtins.input', return_value='')
    @patch('playwright.sync_api.sync_playwright')
    def test_login_once_complete_execution(self, mock_playwright, mock_input):
        """Test complete execution of login_once.py"""
        # Setup all mocks
        mock_browser = Mock()
        mock_context = Mock()
        mock_page = Mock()
        
        mock_context.new_page.return_value = mock_page
        mock_browser.new_context.return_value = mock_context
        
        mock_playwright_instance = Mock()
        mock_playwright_instance.chromium.launch.return_value = mock_browser
        mock_playwright.return_value.__enter__.return_value = mock_playwright_instance
        
        # Execute the actual script
        import login_once
        
        # Verify all calls were made correctly
        mock_playwright_instance.chromium.launch.assert_called_once_with(headless=False)
        mock_browser.new_context.assert_called_once()
        mock_context.new_page.assert_called_once()
        mock_page.goto.assert_called_once()
        mock_context.storage_state.assert_called_once_with(path="storage_state.json")
        mock_browser.close.assert_called_once()
        mock_input.assert_called_once()

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--cov=login_once', '--cov-report=term'])