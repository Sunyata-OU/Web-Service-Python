import pytest
from datetime import datetime
from unittest.mock import patch, Mock
from freezegun import freeze_time

from src.utils import get_current_date_time


class TestGetCurrentDateTime:
    def test_get_current_date_time_format(self):
        """Test that get_current_date_time returns properly formatted datetime string."""
        with freeze_time("2024-01-15 14:30:45"):
            result = get_current_date_time()
            assert result == "2024-01-15 14:30:45"

    def test_get_current_date_time_format_single_digits(self):
        """Test datetime formatting with single digit values."""
        with freeze_time("2024-01-05 09:05:03"):
            result = get_current_date_time()
            assert result == "2024-01-05 09:05:03"

    def test_get_current_date_time_format_end_of_year(self):
        """Test datetime formatting at end of year."""
        with freeze_time("2024-12-31 23:59:59"):
            result = get_current_date_time()
            assert result == "2024-12-31 23:59:59"

    def test_get_current_date_time_format_beginning_of_year(self):
        """Test datetime formatting at beginning of year."""
        with freeze_time("2024-01-01 00:00:00"):
            result = get_current_date_time()
            assert result == "2024-01-01 00:00:00"

    @patch('src.utils.datetime')
    def test_get_current_date_time_calls_datetime_now(self, mock_datetime):
        """Test that the function calls datetime.now()."""
        mock_now = Mock()
        mock_now.strftime.return_value = "2024-01-15 14:30:45"
        mock_datetime.now.return_value = mock_now
        
        result = get_current_date_time()
        
        mock_datetime.now.assert_called_once()
        mock_now.strftime.assert_called_once_with("%Y-%m-%d %H:%M:%S")
        assert result == "2024-01-15 14:30:45"

    def test_get_current_date_time_return_type(self):
        """Test that the function returns a string."""
        result = get_current_date_time()
        assert isinstance(result, str)

    def test_get_current_date_time_length(self):
        """Test that the returned string has expected length."""
        result = get_current_date_time()
        # Format: "YYYY-MM-DD HH:MM:SS" should be 19 characters
        assert len(result) == 19

    def test_get_current_date_time_contains_expected_separators(self):
        """Test that the returned string contains expected separators."""
        result = get_current_date_time()
        assert "-" in result  # Date separators
        assert ":" in result  # Time separators  
        assert " " in result  # Space between date and time

    def test_get_current_date_time_parseable(self):
        """Test that the returned string can be parsed back to datetime."""
        result = get_current_date_time()
        
        # Should be able to parse the string back to datetime
        parsed_datetime = datetime.strptime(result, "%Y-%m-%d %H:%M:%S")
        assert isinstance(parsed_datetime, datetime)

    def test_get_current_date_time_multiple_calls_different_times(self):
        """Test that multiple calls at different times return different values."""
        with freeze_time("2024-01-15 14:30:45"):
            result1 = get_current_date_time()
        
        with freeze_time("2024-01-15 14:30:46"):
            result2 = get_current_date_time()
        
        assert result1 != result2
        assert result1 == "2024-01-15 14:30:45"
        assert result2 == "2024-01-15 14:30:46"

    def test_get_current_date_time_leap_year(self):
        """Test datetime formatting on leap year date."""
        with freeze_time("2024-02-29 12:00:00"):
            result = get_current_date_time()
            assert result == "2024-02-29 12:00:00"

    def test_get_current_date_time_midnight(self):
        """Test datetime formatting at midnight."""
        with freeze_time("2024-01-15 00:00:00"):
            result = get_current_date_time()
            assert result == "2024-01-15 00:00:00"

    def test_get_current_date_time_noon(self):
        """Test datetime formatting at noon."""
        with freeze_time("2024-01-15 12:00:00"):
            result = get_current_date_time()
            assert result == "2024-01-15 12:00:00"