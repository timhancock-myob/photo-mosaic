"""Run the API and the Vite dev server; Ctrl-C stops both. Port comes from MOSAIC_PORT or .env."""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

from mosaic_api.settings import Settings

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", choices=["api", "web"])
    only = parser.parse_args().only
    port = str(Settings().port)

    procs: list[subprocess.Popen[bytes]] = []
    try:
        if only in (None, "api"):
            api_cmd = [sys.executable, "-m", "uvicorn", "mosaic_api.main:app", "--host"]
            api_cmd += ["127.0.0.1", "--port", port, "--reload", "--reload-dir", "packages"]
            procs.append(subprocess.Popen(api_cmd, cwd=ROOT))
        if only in (None, "web"):
            web_env = {**os.environ, "VITE_API_TARGET": f"http://127.0.0.1:{port}"}
            procs.append(subprocess.Popen(["pnpm", "dev"], cwd=ROOT / "web", env=web_env))
        while all(p.poll() is None for p in procs):
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        for p in procs:
            if p.poll() is None:
                p.terminate()
        for p in procs:
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.kill()
    return next((p.returncode for p in procs if p.returncode and p.returncode > 0), 0)


if __name__ == "__main__":
    sys.exit(main())
