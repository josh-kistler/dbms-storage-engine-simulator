"""
Project: B461-Database Concepts - Summer 2026
Student implementation: Josh Kistler
Role: Course starter scaffold with student TODO sections completed

Protected sections marked [INSTRUCTOR ONLY] remain part of the course-provided framework.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import OrderedDict

try:
    from .config import BUFFER_POOL_SIZE
except ImportError:
    from config import BUFFER_POOL_SIZE


# ================================
# [STUDENT TODO] IMPLEMENT BELOW
# ================================
class Replacer(ABC):
    """Shared interface for buffer replacement policies.

    Implementation expectation:
    1. Track which frames are known to the policy.
    2. Track whether a frame is currently evictable.
    3. Update policy state on every access.
    4. Return a victim frame id from ``evict`` when possible.
    5. Remove stale state when a frame leaves the buffer pool.
    """

    def __init__(self, pool_size: int = BUFFER_POOL_SIZE) -> None:
        self.pool_size = pool_size

    @abstractmethod
    def record_access(self, frame_id: int) -> None:
        """Record that a frame was accessed."""

    @abstractmethod
    def evict(self) -> int | None:
        """Return a victim frame id, or None if none is available."""

    @abstractmethod
    def remove(self, frame_id: int) -> None:
        """Remove a frame from the replacer state."""


class LRUReplacer(Replacer):
    """Starter skeleton for an LRU policy.

    Suggested steps:
    1. Maintain frames in least-recently-used order.
    2. Move an accessed frame to the most-recent end.
    3. Only consider evictable frames as victims.
    4. Remove all state for a frame when it leaves the buffer pool.
    """

    def __init__(self, pool_size: int = BUFFER_POOL_SIZE) -> None:
        super().__init__(pool_size)
        self._order: OrderedDict[int, None] = OrderedDict()

    def record_access(self, frame_id: int) -> None:
        if frame_id in self._order:
            self._order.move_to_end(frame_id)

    def set_evictable(self, frame_id: int, evictable: bool) -> None:
        if evictable:
            self._order[frame_id] = None
            self._order.move_to_end(frame_id)
        else:
            self._order.pop(frame_id, None)

    def evict(self) -> int | None:
        #Evict the least-recently-used frame that is currently evictable. If no evictable frames are available, return None.
        if not self._order:
            return None
        victim_frame_id, _ = self._order.popitem(last=False)
        return victim_frame_id

    def remove(self, frame_id: int) -> None:
        self._order.pop(frame_id, None)


class ClockReplacer(Replacer):
    """Starter skeleton for a Clock policy.

    Suggested steps:
    1. Track a circular hand over candidate frame ids.
    2. Maintain one reference bit per frame.
    3. Skip frames that are not evictable.
    4. Clear a reference bit on first pass and evict on second chance miss.
    """

    def __init__(self, pool_size: int = BUFFER_POOL_SIZE) -> None:
        super().__init__(pool_size)
        self.clock_hand = 0
        self.reference_bits = [0 for _ in range(pool_size)]
        self.evictable = [False for _ in range(pool_size)]

    def record_access(self, frame_id: int) -> None:
        # Access should set the reference bit for the accessed frame, indicating that it has been recently used and should be given a second chance before eviction.
        self.reference_bits[frame_id] = 1

    def set_evictable(self, frame_id: int, evictable: bool) -> None:
        self.evictable[frame_id] = evictable
        if not evictable:
            self.reference_bits[frame_id] = 1

    def evict(self) -> int | None:
        #Use a clock hand to approximate LRU. Skip non-evictable frames and give a second chance to frames with the reference bit set.
        if not any(self.evictable):
            return None  # No evictable frames available
        while True:
            frame_id = self.clock_hand
            self.clock_hand = (self.clock_hand + 1) % self.pool_size

            if not self.evictable[frame_id]:
                continue  # Skip non-evictable frames

            if self.reference_bits[frame_id] == 1:
                self.reference_bits[frame_id] = 0 
                continue  # Give a second chance
            self.evictable[frame_id] = False  # Evict this frame
            self.reference_bits[frame_id] = 0  # Clear reference bit
            return frame_id

    def remove(self, frame_id: int) -> None:
        self.evictable[frame_id] = False
        self.reference_bits[frame_id] = 0


class LRUReplacementPolicy(LRUReplacer):
    """Compatibility alias for the existing simulator code."""


class ClockReplacementPolicy(ClockReplacer):
    """Compatibility alias for the existing simulator code."""


__all__ = [
    "Replacer",
    "LRUReplacer",
    "ClockReplacer",
    "LRUReplacementPolicy",
    "ClockReplacementPolicy",
]
