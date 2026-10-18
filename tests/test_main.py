import logging
import importlib
import os
import runpy
import tempfile
import unittest
import builtins
from datetime import datetime as DateTime
from pathlib import Path
from unittest.mock import patch

import main


class MainTests(unittest.TestCase):
    def test_is_valid_url_accepts_http_and_https_urls(self):
        self.assertTrue(main.is_valid_url("http://example.com"))
        self.assertTrue(main.is_valid_url("https://example.com/path"))
        self.assertTrue(main.is_valid_url("ftp://example.com"))

    def test_is_valid_url_rejects_invalid_values(self):
        for url in ("", "not-a-url", None):
            with self.subTest(url=url), self.assertLogs(level=logging.ERROR):
                self.assertFalse(main.is_valid_url(url))

    def test_create_directory_creates_nested_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir) / "nested" / "qr_codes"

            main.create_directory(directory)

            self.assertTrue(directory.is_dir())

    def test_create_directory_exits_when_creation_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir) / "qr_codes"

            with (
                patch.object(Path, "mkdir", side_effect=OSError("permission denied")),
                self.assertLogs(level=logging.ERROR),
                self.assertRaises(SystemExit) as error,
            ):
                main.create_directory(directory)

            self.assertEqual(error.exception.code, 1)

    def test_url_validation_works_without_validators_package(self):
        with patch.object(main, "validators", None):
            self.assertTrue(main.is_valid_url("https://example.com"))

    def test_optional_dependency_import_fallbacks(self):
        original_import = builtins.__import__

        for missing_dependency in ("qrcode", "dotenv", "validators"):
            def import_without_dependency(name, *args, **kwargs):
                if name == missing_dependency:
                    raise ModuleNotFoundError(name=name)
                return original_import(name, *args, **kwargs)

            with self.subTest(dependency=missing_dependency):
                with patch("builtins.__import__", side_effect=import_without_dependency):
                    importlib.reload(main)

                if missing_dependency == "qrcode":
                    self.assertIsNone(main.qrcode)
                elif missing_dependency == "dotenv":
                    self.assertFalse(main.load_dotenv())
                else:
                    self.assertIsNone(main.validators)

        importlib.reload(main)

    def test_generate_qr_code_writes_png_for_valid_url(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "code.png"

            main.generate_qr_code("https://example.com", output)

            self.assertTrue(output.is_file())
            self.assertEqual(output.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")

    def test_generate_qr_code_does_not_write_file_for_invalid_url(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "code.png"

            with self.assertLogs(level=logging.ERROR):
                main.generate_qr_code("not-a-url", output)

            self.assertFalse(output.exists())

    def test_generate_qr_code_reports_missing_qrcode_package(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "code.png"

            with patch.object(main, "qrcode", None):
                with self.assertLogs(level=logging.ERROR) as logs:
                    main.generate_qr_code("https://example.com", output)

            self.assertIn("qrcode", logs.output[0])
            self.assertFalse(output.exists())

    def test_generate_qr_code_logs_generation_errors(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "code.png"

            with (
                patch.object(main.qrcode, "QRCode", side_effect=RuntimeError("generation failed")),
                self.assertLogs(level=logging.ERROR) as logs,
            ):
                main.generate_qr_code("https://example.com", output)

            self.assertIn("generation failed", logs.output[0])
            self.assertFalse(output.exists())

    def test_main_uses_url_argument_and_timestamped_filename(self):
        timestamp = DateTime(2026, 10, 18, 12, 0, 0)
        with tempfile.TemporaryDirectory() as temp_dir:
            with (
                patch("sys.argv", ["main.py", "--url", "https://example.com"]),
                patch.object(main, "QR_DIRECTORY", "output"),
                patch.object(main, "datetime") as mock_datetime,
                patch.object(main, "generate_qr_code") as generate_qr_code,
                patch.object(Path, "cwd", return_value=Path(temp_dir)),
            ):
                mock_datetime.now.return_value = timestamp

                main.main()

            generate_qr_code.assert_called_once_with(
                "https://example.com",
                Path(temp_dir) / "output" / "QRCode_20261018120000.png",
                main.FILL_COLOR,
                main.BACK_COLOR,
            )
            self.assertTrue((Path(temp_dir) / "output").is_dir())

    def test_running_module_as_script_generates_qr_code(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with (
                patch("sys.argv", ["main.py", "--url", "https://example.com"]),
                patch.dict(os.environ, {"QR_CODE_DIR": "output"}),
                patch.object(Path, "cwd", return_value=Path(temp_dir)),
            ):
                runpy.run_path(main.__file__, run_name="__main__")

            output_dir = Path(temp_dir) / "output"
            generated_files = list(output_dir.glob("QRCode_*.png"))
            self.assertEqual(len(generated_files), 1)
            self.assertEqual(generated_files[0].read_bytes()[:8], b"\x89PNG\r\n\x1a\n")


if __name__ == "__main__":
    unittest.main()
