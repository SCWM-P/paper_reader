"""One OS process lock for cooperative CLI and GUI writes."""
from contextlib import contextmanager
import os
import time
from .models import StoreError
from .repository import roots, safe_path, runtime_root

@contextmanager
def write_lock(workspace):
    workspace, _ = roots(workspace)
    store = runtime_root(workspace)
    store.mkdir(parents=True, exist_ok=True)
    path = safe_path(store / '.write.lock', workspace)
    with path.open('a+b') as stream:
        if os.name == 'nt':
            import msvcrt
            if stream.seek(0, 2) == 0:
                stream.write(b'0')
                stream.flush()
            def acquire():
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            def release():
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            def acquire():
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            def release():
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        deadline = time.monotonic() + 5
        while True:
            try:
                acquire()
                break
            except (BlockingIOError, OSError):
                if time.monotonic() >= deadline:
                    raise StoreError('Another writer is active; retry after it completes', 'conflict', path)
                time.sleep(0.05)
        try:
            yield
        finally:
            release()
