import heapq
import itertools
from collections.abc import Callable
from dataclasses import dataclass


@dataclass
class Event:
    time: float
    callback: Callable[[], None]


class EventQueue:
    def __init__(self) -> None:
        # the sequence number breaks ties, so events at the same time pop in the order they were scheduled
        self.events: list[tuple[float, int, Event]] = []
        self.sequence = itertools.count()

    def schedule(self, event: Event) -> None:
        heapq.heappush(self.events, (event.time, next(self.sequence), event))

    def pop(self) -> Event:
        return heapq.heappop(self.events)[2]

    def is_empty(self) -> bool:
        return not self.events
