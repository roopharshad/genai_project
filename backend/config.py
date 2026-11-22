"""Runtime configuration, read from environment variables (optionally a .env file)."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
# .env (local development) wins over variables inherited from the shell. In a container there
# is no .env file (see .dockerignore), so the platform's environment variables are used.
load_dotenv(ROOT_DIR / ".env", override=True)


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


# Remote restoration service (internal detail, never exposed to the UI).
RESTORATION_SPACE_URL = os.getenv(
    "RESTORATION_SPACE_URL", "https://randomtable-image-restoration-gfpgan.hf.space"
).rstrip("/")
# Optional Hugging Face token for private / rate-limited Spaces.
HF_TOKEN = os.getenv("HF_TOKEN", "").strip()
RESTORATION_TIMEOUT_SECONDS = _int("RESTORATION_TIMEOUT_SECONDS", 300)

MAX_UPLOAD_MB = _int("MAX_UPLOAD_MB", 10)
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
# Images larger than this (longest side, px) are downscaled before remote processing.
MAX_PROCESS_SIDE = _int("MAX_PROCESS_SIDE", 1600)


def usable_cpus() -> int:
    """CPUs this process may really use. In containers (Render, Docker) os.cpu_count() reports the
    host's cores, not the plan's CPU quota; starting that many threads on a fraction of a CPU
    makes PyTorch/Paddle extremely slow. Override with CPU_THREADS."""
    if os.getenv("CPU_THREADS"):
        return max(1, _int("CPU_THREADS", 1))
    n = os.cpu_count() or 1
    try:
        n = min(n, len(os.sched_getaffinity(0)))
    except (AttributeError, OSError):
        pass
    try:  # cgroup v2: "max 100000" or "50000 100000"
        quota, period = Path("/sys/fs/cgroup/cpu.max").read_text().split()[:2]
        if quota != "max":
            n = min(n, max(1, int(int(quota) / int(period) + 0.999)))
    except (OSError, ValueError):
        try:  # cgroup v1
            q = int(Path("/sys/fs/cgroup/cpu/cpu.cfs_quota_us").read_text())
            p = int(Path("/sys/fs/cgroup/cpu/cpu.cfs_period_us").read_text())
            if q > 0:
                n = min(n, max(1, int(q / p + 0.999)))
        except (OSError, ValueError):
            pass
    return max(1, n)


# Thread pools must be sized before torch / numpy / paddle are imported.
for _var in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ.setdefault(_var, str(usable_cpus()))
