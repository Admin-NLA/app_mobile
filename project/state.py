from threading import Lock
pending_scans = {}
scan_results = {}

lock = Lock()