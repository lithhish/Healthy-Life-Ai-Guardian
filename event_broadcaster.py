"""
AI Driver Health Guardian — Real-Time Event Broadcaster

Provides real-time event broadcasting for Server-Sent Events (SSE)
and high-frequency polling across Driver, Family, Hospital, Ambulance, and Admin dashboards.
"""

import time
import json
import threading
from datetime import datetime
from queue import Queue, Empty

_event_history = []
_subscribers = []
_lock = threading.Lock()

def publish_event(event_type: str, data: dict):
    """
    Publish an event to all active real-time dashboard subscribers.
    """
    event = {
        'id': int(time.time() * 1000),
        'event': event_type,
        'timestamp': datetime.now().isoformat(),
        'data': data
    }
    
    with _lock:
        _event_history.append(event)
        if len(_event_history) > 200:
            _event_history.pop(0)
            
        # Dispatch to all subscriber queues
        dead_subscribers = []
        for q in _subscribers:
            try:
                q.put_nowait(event)
            except Exception:
                dead_subscribers.append(q)
                
        for q in dead_subscribers:
            if q in _subscribers:
                _subscribers.remove(q)

    print(f"[EventBroadcaster] Published '{event_type}' -> {data.get('emergency_id', 'N/A')}")
    return event

def subscribe():
    """Subscribe a new client queue to the SSE stream."""
    q = Queue(maxsize=50)
    with _lock:
        _subscribers.append(q)
    return q

def unsubscribe(q):
    """Unsubscribe a client queue."""
    with _lock:
        if q in _subscribers:
            _subscribers.remove(q)

def get_recent_events(since_id: int = 0):
    """Get all events published after since_id for polling clients."""
    with _lock:
        return [e for e in _event_history if e['id'] > since_id]

def sse_event_stream():
    """Generator function for Flask SSE response."""
    q = subscribe()
    try:
        # Send initial ping event
        yield f"data: {json.dumps({'event': 'CONNECTED', 'timestamp': datetime.now().isoformat()})}\n\n"
        while True:
            try:
                event = q.get(timeout=25)
                yield f"data: {json.dumps(event)}\n\n"
            except Empty:
                # Send heartbeat to keep connection open
                yield f": heartbeat\n\n"
    finally:
        unsubscribe(q)
