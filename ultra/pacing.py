"""Ordonnancement partagé de contenu logique, sans verrou pendant l'attente."""
import threading
import time


class BytePacer:
    def __init__(self, bytes_per_second, clock=None):
        self.rate = bytes_per_second
        self.clock = clock or time.monotonic
        self.deadline = self.clock()
        self.lock = threading.Lock()

    def wait(self, count, cancel):
        if not count:
            return cancel.is_set()
        with self.lock:
            now = self.clock()
            self.deadline = max(now, self.deadline) + count/self.rate
            target = self.deadline
        while True:
            delay = target-self.clock()
            if delay <= 0:
                return cancel.is_set()
            if cancel.wait(min(delay, 1.0)):
                return True
