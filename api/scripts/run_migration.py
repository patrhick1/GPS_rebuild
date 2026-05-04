"""One-off migration runner: alembic upgrade head with explicit logging."""
print("startup", flush=True)
import sys, time
print("imports begin", flush=True)
sys.path.insert(0, '.')

from alembic.config import Config
from alembic import command
print("imports done", flush=True)

t0 = time.time()
print(f"[{time.time()-t0:5.1f}s] Loading alembic config...", flush=True)
cfg = Config("alembic.ini")
print(f"[{time.time()-t0:5.1f}s] Running upgrade head...", flush=True)
command.upgrade(cfg, "head")
print(f"[{time.time()-t0:5.1f}s] Done.", flush=True)
