import os
import shutil
import subprocess
import tempfile
import unittest
import uuid
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCKER_AVAILABLE = shutil.which("docker") is not None


@unittest.skipUnless(DOCKER_AVAILABLE, "Docker is required for Dockerfile integration tests")
class DockerfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.image_tag = f"qr-code-generator-test:{uuid.uuid4().hex}"
        subprocess.run(
            ["docker", "build", "--tag", cls.image_tag, str(PROJECT_ROOT)],
            check=True,
            cwd=PROJECT_ROOT,
        )

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "image_tag"):
            subprocess.run(
                ["docker", "image", "rm", "--force", cls.image_tag],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

    def test_image_uses_non_root_user(self):
        result = subprocess.run(
            ["docker", "image", "inspect", "--format", "{{.Config.User}}", self.image_tag],
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.stdout.strip(), "av477")

    def test_container_generates_png_in_mounted_output_directory(self):
        with tempfile.TemporaryDirectory() as output_dir:
            os.chmod(output_dir, 0o777)
            host_output_dir = Path(output_dir).resolve().as_posix()
            result = subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "--mount",
                    f"type=bind,source={host_output_dir},target=/app/qr_codes",
                    self.image_tag,
                    "--url",
                    "https://example.com",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            generated_files = list(Path(output_dir).glob("QRCode_*.png"))
            self.assertEqual(len(generated_files), 1)
            self.assertEqual(generated_files[0].read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
            self.assertIn("QR code successfully saved", result.stdout)


if __name__ == "__main__":
    unittest.main()
