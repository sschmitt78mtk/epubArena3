import unittest
import os
import tempfile
from errorLog import Logfiles


class TestLogfileLimiting(unittest.TestCase):
    """Tests to verify that log file limiting works properly."""

    def _create_logfile(self, max_chars: int = 100) -> Logfiles:
        """Create a Logfiles instance with a small maxChars for testing."""
        log = Logfiles()
        log.maxChars = max_chars
        return log

    # --- _ensure_max_chars tests ---

    def test_ensure_max_chars_truncates_long_text(self):
        log = self._create_logfile(max_chars=50)
        long_text = "0123456789" * 10  # 100 chars
        result = log._ensure_max_chars(long_text)
        self.assertEqual(len(result), 50)
        self.assertEqual(result, "01234567890123456789012345678901234567890123456789")

    def test_ensure_max_chars_keeps_short_text(self):
        log = self._create_logfile(max_chars=100)
        short_text = "Hello"
        result = log._ensure_max_chars(short_text)
        self.assertEqual(result, "Hello")

    def test_ensure_max_chars_exact_size(self):
        log = self._create_logfile(max_chars=10)
        exact_text = "0123456789"
        result = log._ensure_max_chars(exact_text)
        self.assertEqual(result, exact_text)

    # --- log() truncation test ---

    def test_log_truncates_logfiletext(self):
        log = self._create_logfile(max_chars=50)
        log.log("First message")
        log.log("Second message that is very long and should cause truncation")
        self.assertLessEqual(len(log.Logfiletext), 50)

    def test_log_truncates_sessiontext(self):
        log = self._create_logfile(max_chars=50)
        log.log("First message")
        log.log("Second message that is very long and should cause truncation")
        self.assertLessEqual(len(log.Sessiontext), 50)

    # --- print() truncation test ---

    def test_print_truncates_sessiontext(self):
        log = self._create_logfile(max_chars=50)
        log.print("First message")
        log.print("Second message that is very long and should cause truncation")
        self.assertLessEqual(len(log.Sessiontext), 50)

    def test_print_does_not_affect_logfiletext(self):
        log = self._create_logfile(max_chars=50)
        log.print("Print-only message")
        self.assertEqual(log.Logfiletext, "")

    # --- printlog() truncation test ---

    def test_printlog_truncates_both_buffers(self):
        log = self._create_logfile(max_chars=50)
        log.printlog("First message")
        log.printlog("Second message that is very long and should cause truncation")
        self.assertLessEqual(len(log.Sessiontext), 50)
        self.assertLessEqual(len(log.Logfiletext), 50)

    # --- warning() truncation test ---

    def test_warning_truncates_and_adds_prefix(self):
        log = self._create_logfile(max_chars=100)
        log.warning("Something broke")
        self.assertIn("WARNUNG:", log.Logfiletext)
        self.assertLessEqual(len(log.Logfiletext), 100)

    # --- error() truncation test ---

    def test_error_truncates_all_buffers(self):
        log = self._create_logfile(max_chars=50)
        log.error("Critical failure")
        log.error("Another long error message that should cause all buffers to be truncated")
        self.assertLessEqual(len(log.Logfiletext), 50)
        self.assertLessEqual(len(log.Sessiontext), 50)
        self.assertLessEqual(len(log.errorLogfiletext), 50)

    def test_error_increments_errorcount(self):
        log = self._create_logfile()
        self.assertEqual(log.errorcount, 0)
        log.error("First error")
        self.assertEqual(log.errorcount, 1)
        log.error("Second error")
        self.assertEqual(log.errorcount, 2)

    def test_error_adds_error_prefix(self):
        log = self._create_logfile()
        log.error("Test error")
        self.assertIn("FEHLER:", log.errorLogfiletext)
        self.assertIn("FEHLER:", log.Logfiletext)

    # --- saveFile() truncation removal test ---

    def test_saveFile_writes_truncated_content(self):
        log = self._create_logfile(max_chars=50)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False, dir='.') as f:
            log.LogFileName = f.name
            log.log("A" * 200)  # Should be truncated to 50 chars
        try:
            log.saveFile()
            with open(log.LogFileName, 'r', encoding='utf-8') as f:
                content = f.read()
            self.assertLessEqual(len(content), 50)
        finally:
            os.unlink(log.LogFileName)

    def test_saveFile_error_log_written_when_errors_exist(self):
        log = self._create_logfile(max_chars=100)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False, dir='.') as f:
            log.LogFileName = f.name
            with tempfile.NamedTemporaryFile(mode='w', suffix='.err', delete=False, dir='.') as ef:
                log.errorLogFilename = ef.name
                log.error("An error occurred")
        try:
            log.saveFile()
            with open(log.errorLogFilename, 'r', encoding='utf-8') as f:
                content = f.read()
            self.assertIn("FEHLER:", content)
        finally:
            os.unlink(log.LogFileName)
            os.unlink(log.errorLogFilename)

    def test_saveFile_does_not_write_error_log_when_no_errors(self):
        log = self._create_logfile(max_chars=100)
        log.LogFileName = ""
        log.errorLogFilename = ""
        log.saveFile()  # Should not raise, no files to write

    # --- _shortenifneeded removed test ---

    def test_shortenifneeded_method_removed(self):
        log = self._create_logfile()
        self.assertFalse(hasattr(log, '_shortenifneeded'),
                         "_shortenifneeded method should be removed")


if __name__ == '__main__':
    unittest.main()