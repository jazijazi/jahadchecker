# gunicorn_config.py

import multiprocessing

# Bind to a Unix socket file
bind = "0.0.0.0:8000"

# Recommended: number of workers = 2 * CPUs + 1
workers = multiprocessing.cpu_count() * 2 + 1

# Optional: threads per worker (can improve concurrency for IO-bound apps)
threads = 2

# Logging
accesslog = "-"  # stdout
errorlog = "-"   # stderr
loglevel = "info"

# Timeouts
timeout = 120            # Worker timeout (seconds)
graceful_timeout = 20    # Graceful timeout for worker restart

# Daemonize (commented out: don't use with systemd!)
# daemon = True # Never daemonize in Docker.

# PID file (optional)
# Not needed in Docker because process management is handled by Docker itself.
# pidfile = "/run/gunicorn/gunicorn.pid"

# Worker class (default: sync, others include gevent, uvicorn.workers.UvicornWorker)
worker_class = "sync"

# Max requests before a worker is restarted (helps with memory leaks)
max_requests = 1000
max_requests_jitter = 50

# Preload app (can be useful to reduce memory footprint with copy-on-write)
preload_app = True
