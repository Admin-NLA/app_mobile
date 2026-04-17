from threading import Lock
from queue import Queue
from typing import Optional
pending_scans = {}
scan_results = {}
records_clients = {}

lock = Lock()

def build_records_channel(company: str, event_id: Optional[int]):
    if not company or not event_id:
        return None
    return f"{company}|{event_id}"

def connect_records_client(channel: str):
    client_queue = Queue()
    with lock:
        clients = records_clients.setdefault(channel, [])
        clients.append(client_queue)
    return client_queue

def disconnect_records_client(channel: str, client_queue: Queue):
    with lock:
        clients = records_clients.get(channel, [])
        if client_queue in clients:
            clients.remove(client_queue)
        if not clients and channel in records_clients:
            records_clients.pop(channel, None)

def publish_records_event(channel: str, event_payload: dict):
    with lock:
        clients = list(records_clients.get(channel, []))
    for client_queue in clients:
        client_queue.put(event_payload)