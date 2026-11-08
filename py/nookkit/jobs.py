"""One background job at a time, with live state the front end can poll.

    job = Job(status="idle", percent=0.0)
    if not job.start(work, url):            # False if a job is already running
        return req.error("Busy!", 409)
    def work(job, url):
        job.update(status="working", percent=12.5)
    GET /status → req.json(job.snapshot())
"""
import threading
import time
import traceback

BUSY = {"starting", "working", "downloading", "processing", "updating"}


class Job:
    def __init__(self, **initial):
        self._initial = dict(initial)
        self._state = dict(initial)
        self._lock = threading.Lock()
        self._thread = None
        self.seq = 0  # bumps on every start, so the UI can tell runs apart

    def update(self, **changes):
        with self._lock:
            self._state.update(changes)
            self._state["updated"] = time.time()

    def snapshot(self):
        with self._lock:
            return {**self._state, "seq": self.seq, "busy": self.busy}

    def get(self, key, default=None):
        with self._lock:
            return self._state.get(key, default)

    @property
    def busy(self):
        return self._state.get("status") in BUSY or bool(self._thread and self._thread.is_alive())

    def start(self, fn, *args, **reset):
        """Run fn(job, *args) in a thread. `reset` = fields to set first. Returns False if busy."""
        with self._lock:
            if self._state.get("status") in BUSY or (self._thread and self._thread.is_alive()):
                return False
            self.seq += 1
            self._state = {**self._initial, "status": "starting", **reset, "updated": time.time()}

        def runner():
            try:
                fn(self, *args)
            except Exception as e:  # never leave the UI stuck on "working"
                traceback.print_exc()
                self.update(status="error", message=str(e) or e.__class__.__name__)

        self._thread = threading.Thread(target=runner, daemon=True)
        self._thread.start()
        return True
