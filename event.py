import heapq
import itertools
from dataclasses import dataclass
from typing import List, Tuple, Callable

@dataclass
class Event:
    time: float
    type: Callable

    def __lt__(self, other):
        return self.time < other.time

class EventQueue:
    def __init__(self):
        self.events: List[Tuple[float, int, Event]] = []
        # tie-breaker so events at the same time pop in the order they were scheduled
        self.sequence = itertools.count()

    def schedule_event(self, event: Event):
        heapq.heappush(self.events, (event.time, next(self.sequence), event))

    def next_event(self) -> Event:
        return heapq.heappop(self.events)[2]

    def is_empty(self):
        return len(self.events) == 0