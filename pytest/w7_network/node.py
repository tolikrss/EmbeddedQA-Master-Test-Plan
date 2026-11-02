"""Black-box driver for the W7 IoT node running on the host model.

Talks to the firmware only through UART lines (and GPIO events printed by the HAL).
Every received line is kept with device time, so the transcript is the evidence.
"""
import json
import subprocess
import threading
import time


class Node:
    def __init__(self, binary, scale=5.0, log_path=None):
        self.scale = scale
        self.p = subprocess.Popen([binary], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  env={"HAL_SCALE": str(scale)}, bufsize=0)
        self.lines = []          # (device_ms, kind, text)
        self.lock = threading.Lock()
        self.log = open(log_path, "w") if log_path else None
        threading.Thread(target=self._reader, daemon=True).start()
        self.wait_for(lambda l: "ready" in l[2].lower() or "BOOT" in l[2], timeout_dev_ms=3000)

    def _reader(self):
        for raw in iter(self.p.stdout.readline, b""):
            s = raw.decode("utf-8", "replace").rstrip("\n")
            parts = s.split(" ", 2)
            if len(parts) < 2:
                continue
            kind, t = parts[0], float(parts[1])
            text = parts[2] if len(parts) > 2 else ""
            with self.lock:
                self.lines.append((t, kind, text))
                if self.log and not self.log.closed:
                    self.log.write(f"[{t:10.1f} ms] {'RX' if kind == '@T' else 'HW'} {text}\n")
                    self.log.flush()

    def note(self, msg):
        if self.log:
            self.log.write(f"# {msg}\n")
            self.log.flush()

    def mark(self):
        with self.lock:
            return len(self.lines)

    def since(self, idx):
        with self.lock:
            return list(self.lines[idx:])

    def send(self, cmd):
        if self.log:
            t = self.lines[-1][0] if self.lines else 0
            self.log.write(f"[~{t:9.1f} ms] TX {cmd}\n")
            self.log.flush()
        self.p.stdin.write((cmd + "\n").encode())
        self.p.stdin.flush()

    def wait_dev(self, dev_ms):
        time.sleep(dev_ms / 1000.0 / self.scale)

    def wait_for(self, pred, timeout_dev_ms=2000, start=0):
        end = time.time() + timeout_dev_ms / 1000.0 / self.scale
        while time.time() < end:
            with self.lock:
                for l in self.lines[start:]:
                    if pred(l):
                        return l
            time.sleep(0.005)
        return None

    def cmd(self, c, settle_dev_ms=600):
        i = self.mark()
        self.send(c)
        self.wait_dev(settle_dev_ms)
        return [l for l in self.since(i) if l[1] == "@T"]

    def status(self):
        i = self.mark()
        self.send("STATUS")
        l = self.wait_for(lambda l: l[1] == "@T" and l[2].startswith("{") and '"net"' in l[2],
                          timeout_dev_ms=2000, start=i)
        self.wait_dev(300)
        return json.loads(l[2]) if l else None

    def close(self):
        try:
            self.p.kill()
        except Exception:
            pass
        try:
            self.p.wait(timeout=2)
        except Exception:
            pass
        if self.log:
            with self.lock:
                self.log.close()
