# core_files/safe_runner.py
"""
Generic process-based safety wrapper untuk operasi yang bicara ke mesin X105.

Kenapa pakai Process bukan Thread?
- pyzk bisa hang di level socket (blocking I/O).
- Thread Python TIDAK BISA dipaksa mati - kalau hang, dia akan terus
  memegang koneksi TCP selamanya sampai seluruh service di-restart.
- Process BISA di-terminate oleh OS. Saat di-kill, socket-nya otomatis
  ikut tertutup - mesin langsung bisa diakses lagi tanpa restart systemd.

Dipakai oleh:
- webapp.py    (tombol "Get Records" / "Refresh Statistics" dari UI)
- mainapp.py   (job terjadwal/cron)
sehingga SEMUA jalur komunikasi ke mesin mendapat perlindungan yang sama.
"""

import multiprocessing
import time
import socket
import threading

DEFAULT_TIMEOUT_SECONDS = 90


def is_machine_reachable(ip, port=4370, timeout=5):
    """Cek cepat pakai raw socket sebelum mencoba protokol ZK yang lambat."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        result = s.connect_ex((ip, port))
        s.close()
        return result == 0
    except Exception:
        return False


class SafeJobRunner:
    """Maksimal satu job berjalan per `key` (misal machine_id)."""

    _jobs = {}
    _guard = threading.Lock()

    @classmethod
    def start(cls, key, target, args=(), kwargs=None, timeout=DEFAULT_TIMEOUT_SECONDS):
        kwargs = kwargs or {}
        with cls._guard:
            existing = cls._jobs.get(key)
            if existing and existing["process"].is_alive():
                return False, "Job sudah berjalan untuk key ini."

            result_queue = multiprocessing.Queue()
            process = multiprocessing.Process(
                target=cls._wrapped_target,
                args=(target, args, kwargs, result_queue),
            )
            process.daemon = True
            process.start()

            cls._jobs[key] = {
                "process": process,
                "queue": result_queue,
                "started_at": time.time(),
                "timeout": timeout,
                "result": None,
            }
            return True, "Job dimulai."

    @staticmethod
    def _wrapped_target(target, args, kwargs, result_queue):
        try:
            value = target(*args, **kwargs)
            result_queue.put({"status": "done", "value": value})
        except Exception as e:
            result_queue.put({"status": "error", "message": str(e)})

    @classmethod
    def poll(cls, key):
        """Cek status job. Otomatis force-kill kalau lewat timeout."""
        with cls._guard:
            entry = cls._jobs.get(key)
            if not entry:
                return {"status": "idle"}

            if entry["result"]:
                return entry["result"]

            if not entry["queue"].empty():
                result = entry["queue"].get()
                entry["result"] = result
                entry["process"].join(timeout=2)
                return result

            elapsed = time.time() - entry["started_at"]
            if elapsed > entry["timeout"]:
                process = entry["process"]
                if process.is_alive():
                    process.terminate()
                    process.join(timeout=5)
                    if process.is_alive():
                        process.kill()
                        process.join(timeout=5)
                result = {
                    "status": "error",
                    "message": f"⏱️ Timeout {entry['timeout']}s - proses dihentikan paksa, TANPA perlu restart service.",
                }
                entry["result"] = result
                return result

            return {"status": "running", "elapsed": int(elapsed)}
