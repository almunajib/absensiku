# core_files/safe_logger.py
"""
Safe logger module untuk menghindari broken pipe error
"""
import logging
import signal

# Ignore SIGPIPE signal globally
try:
    signal.signal(signal.SIGPIPE, signal.SIG_IGN)
except AttributeError:
    # Windows tidak punya SIGPIPE
    pass


class SafeStreamHandler(logging.StreamHandler):
    """StreamHandler yang ignore broken pipe errors"""
    
    def emit(self, record):
        try:
            super().emit(record)
            # Flush juga perlu di-protect
            self.flush()
        except (BrokenPipeError, IOError, OSError):
            # Ignore broken pipe, connection reset, dll
            pass
        except Exception:
            # Untuk error lain, tetap handle seperti biasa
            self.handleError(record)


def setup_logger(name, log_file, level=logging.INFO):
    """
    Setup logger dengan file handler dan safe stream handler
    
    Args:
        name: Nama logger
        log_file: Path ke file log
        level: Log level (default: INFO)
    
    Returns:
        Logger object
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Cegah duplicate handlers
    if logger.handlers:
        return logger
    
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    
    # File handler (selalu aman)
    fh = logging.FileHandler(log_file)
    fh.setLevel(level)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    
    # Safe stream handler (untuk stdout/journalctl)
    sh = SafeStreamHandler()
    sh.setLevel(level)
    sh.setFormatter(formatter)
    logger.addHandler(sh)
    
    return logger
