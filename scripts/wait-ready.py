"""Wait for the real local stack; useful for CI browser checks."""

import time
from urllib.request import urlopen

urls = [
    "http://127.0.0.1:8000/health/ready",
    "http://127.0.0.1:8001/health/live",
    "http://127.0.0.1:3000",
]
for url in urls:
    deadline = time.monotonic() + 90
    while True:
        try:
            with urlopen(url, timeout=3) as response:
                assert response.status == 200
            break
        except Exception:
            if time.monotonic() > deadline:
                raise RuntimeError(f"Timed out waiting for {url}") from None
            time.sleep(2)
print("All local endpoints healthy")
