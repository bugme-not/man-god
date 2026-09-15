import os
import glob
import logging
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Paths to clear or truncate
LOG_PATHS = [
    "/var/log/nginx/*.log",
    "/var/log/supervisor/*.log",
    "/tmp/*.log"
]

# Max log file size in bytes before truncation (10 MB)
MAX_LOG_SIZE_BYTES = 10 * 1024 * 1024
CLEANUP_INTERVAL_SECONDS = 300  # Runs every 5 minutes


def truncate_large_logs():
    """Truncates log files exceeding max size to prevent disk usage issues."""
    for path_pattern in LOG_PATHS:
        for file_path in glob.glob(path_pattern):
            try:
                if os.path.isfile(file_path) and os.path.getsize(file_path) > MAX_LOG_SIZE_BYTES:
                    with open(file_path, 'w') as f:
                        f.truncate(0)
                    logging.info(f"Truncated oversized log file: {file_path}")
            except Exception as e:
                logging.error(f"Failed to truncate {file_path}: {e}")


def main():
    logging.info("Starting log_cleaner daemon...")
    while True:
        try:
            truncate_large_logs()
        except Exception as e:
            logging.error(f"Error during log cleaning cycle: {e}")
        time.sleep(CLEANUP_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
