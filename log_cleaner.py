import asyncio
import os
import time
import glob

try:
    import uvloop
    uvloop.install()
except ImportError:
    pass

LOG_PATHS = [
    "/var/log/nginx/*.log",
    "/var/log/sshd.log",
    "/var/log/syslog",
    "/var/log/messages",
    "/var/log/auth.log",
    "/tmp/*.log"
]

# Targeted directories (avoiding sweeping root /tmp wipes)
DIRS_TO_PURGE = ["/var/tmp", "/var/cache/nginx"]
CLEAN_INTERVAL = 120
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024
TEMP_MAX_AGE_SEC = 300

def log(msg: str) -> None:
    print(f"[Log-Cleaner] {time.strftime('%Y-%m-%d %H:%M:%S')} - {msg}", flush=True)

def truncate_file(filepath: str) -> None:
    """Uses non-blocking POSIX system calls directly."""
    try:
        fd = os.open(filepath, os.O_RDWR | os.O_NONBLOCK)
        try:
            os.ftruncate(fd, 0)
            log(f"Truncated oversized log: {filepath}")
        finally:
            os.close(fd)
    except Exception:
        pass

def scan_and_filter_logs(pattern: str) -> list[str]:
    targets = []
    for filepath in glob.glob(pattern):
        try:
            if os.path.isfile(filepath) and os.path.getsize(filepath) > MAX_FILE_SIZE_BYTES:
                targets.append(filepath)
        except Exception:
            pass
    return targets

async def purge_logs():
    loop = asyncio.get_running_loop()
    scan_tasks = [loop.run_in_executor(None, scan_and_filter_logs, pattern) for pattern in LOG_PATHS]
    results = await asyncio.gather(*scan_tasks)
    
    truncation_tasks = []
    for oversized_files in results:
        for filepath in oversized_files:
            truncation_tasks.append(loop.run_in_executor(None, truncate_file, filepath))
            
    if truncation_tasks:
        await asyncio.gather(*truncation_tasks)

def _scan_directory_fast(path_str: str) -> list[str]:
    now = time.time()
    files_to_remove = []
    if not os.path.exists(path_str):
        return files_to_remove
    try:
        with os.scandir(path_str) as entries:
            for entry in entries:
                try:
                    if entry.is_file(follow_symlinks=False) and not entry.name.endswith('.py'):
                        stat = entry.stat(follow_symlinks=False)
                        if now - stat.st_mtime > TEMP_MAX_AGE_SEC:
                            files_to_remove.append(entry.path)
                except Exception:
                    pass
    except Exception:
        pass
    return files_to_remove

def unlink_file(filepath: str) -> None:
    try:
        os.unlink(filepath)
    except Exception:
        pass

async def wipe_temp_cache():
    loop = asyncio.get_running_loop()
    scan_tasks = [loop.run_in_executor(None, _scan_directory_fast, d) for d in DIRS_TO_PURGE]
    results = await asyncio.gather(*scan_tasks)
    
    removal_tasks = []
    for file_list in results:
        for filepath in file_list:
            removal_tasks.append(loop.run_in_executor(None, unlink_file, filepath))
            
    if removal_tasks:
        await asyncio.gather(*removal_tasks)

async def main():
    log("Engine active. Fast async log sanitization enabled...")
    while True:
        try:
            await asyncio.gather(purge_logs(), wipe_temp_cache())
        except Exception as e:
            log(f"Cycle execution error: {e}")
        await asyncio.sleep(CLEAN_INTERVAL)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log("Shutting down engine...")
