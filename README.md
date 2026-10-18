# QR Code Generator

A command-line Python application that creates a PNG QR code for a URL. Generated images are timestamped and saved in the `qr_codes` directory by default.

## Requirements

- Python 3.12 or later
- Docker ( for containerized use)

## Run locally

Create and activate a virtual environment, then install the application dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Generate a QR code:

```powershell
python main.py --url https://example.com
```

If `--url` is omitted, the application uses `https://github.com/av477`. The QR image is saved as `qr_codes/QRCode_<timestamp>.png`.

## Configuration

The application reads these optional environment variables (a `.env` file is also loaded when `python-dotenv` is installed):

| Variable | Default | Description |
| --- | --- | --- |
| `QR_CODE_DIR` | `qr_codes` | Directory where generated images are saved |
| `FILL_COLOR` | `red` | QR code foreground color |
| `BACK_COLOR` | `white` | QR code background color |

## Run with Docker

Build the image:

```powershell
docker build -t qr-code-generator .
```

```powershell
docker run -d --name qr-generator qr-code-generator
```

Run it with a URL and mount the output directory so the generated image is available on the host:

```powershell
New-Item -ItemType Directory -Force .\qr_codes | Out-Null
docker run --rm `
  --mount "type=bind,source=$((Get-Location).Path)\qr_codes,target=/app/qr_codes" `
  qr-code-generator --url https://example.com
```

The container runs the generator once and exits. The generated PNG remains in the host's `qr_codes` directory. If no URL is passed, the image uses the default URL.

## Tests and coverage

Install the application and development dependencies, then run the tests with a 90% minimum line-coverage requirement:

```powershell
python -m pip install -r requirements-dev.txt
python -m coverage run --source=main -m unittest discover -s tests -v
python -m coverage report --fail-under=90
```

GitHub Actions runs the same tests and coverage check on pushes and pull requests, then builds the Docker image. The workflow fails if `main.py` coverage is below 90%.
