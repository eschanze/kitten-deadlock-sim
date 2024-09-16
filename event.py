import heapq
from dataclasses import dataclass
from typing import List, Callable

@dataclass
class Event:
    time: float
    type: Callable

    def __lt__(self, other):
        return self.time < other.time

class EventQueue:
    def __init__(self):
        self.events: List[Event] = []

    def schedule_event(self, event: Event):
        heapq.heappush(self.events, event)

    def next_event(self) -> Event:
        return heapq.heappop(self.events)

    def is_empty(self):
        return len(self.events) == 0