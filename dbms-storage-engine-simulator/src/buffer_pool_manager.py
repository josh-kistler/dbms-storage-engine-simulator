"""
Project: B461-Database Concepts - Summer 2026
Student implementation: Josh Kistler
Role: Course starter scaffold with student TODO sections completed

Protected sections marked [INSTRUCTOR ONLY] remain part of the course-provided framework.
"""

"""Buffer pool manager for the student starter."""

try:
    from .config import BUFFER_POOL_SIZE
    from .disk_manager import DiskManager
    from .models import Page
    from .replacement import ClockReplacementPolicy, LRUReplacementPolicy
except ImportError:
    from config import BUFFER_POOL_SIZE
    from disk_manager import DiskManager
    from models import Page
    from replacement import ClockReplacementPolicy, LRUReplacementPolicy


# ================================
# [STUDENT TODO] IMPLEMENT BELOW
# ================================
class BufferPoolManager:
    def __init__(
        self,
        pool_size: int = BUFFER_POOL_SIZE,
        disk_manager: DiskManager | None = None,
        replacement_policy: str = "lru",
    ) -> None:
        if pool_size <= 0:
            raise ValueError("Buffer pool size must be positive.")

        self.pool_size = pool_size
        self.disk_manager = disk_manager if disk_manager is not None else DiskManager()
        self.page_table: dict[int, int] = {}
        self.frames: list[Page | None] = [None for _ in range(pool_size)]
        self.free_list = list(range(pool_size))
        self.replacer = self._build_replacer(replacement_policy)
        self.replacement_policy_name = replacement_policy.lower()

        self.hit_count = 0
        self.miss_count = 0
        self.eviction_count = 0
        self.flush_count = 0
        self.delete_count = 0

        # ================================
        # [INSTRUCTOR ONLY] DO NOT MODIFY
        # ================================
        # [INSTRUCTOR ONLY] Shared-state orchestration or locking belongs here.

    def _build_replacer(self, replacement_policy: str):
        normalized = replacement_policy.lower()
        if normalized == "lru":
            return LRUReplacementPolicy(self.pool_size)
        if normalized == "clock":
            return ClockReplacementPolicy(self.pool_size)
        raise ValueError(f"Unknown replacement policy: {replacement_policy}")

    def _get_frame_id(self, page_id: int) -> int | None:
        return self.page_table.get(page_id)

    def _mark_frame_evictable(self, frame_id: int, evictable: bool) -> None:
        # [STUDENT TODO] Coordinate pin/unpin state with the replacement policy.
        self.replacer.record_access(frame_id)
        self.replacer.set_evictable(frame_id, evictable)

    def _evict_if_needed(self) -> int:
        if self.free_list:
            return self.free_list.pop(0)

        # Ask the replacement policy for a victim frame to evict. If none are evictable, this will return None.
        victim_frame_id = self.replacer.evict()
        if victim_frame_id is None:
            raise RuntimeError("No evictable frame available.")
        
        victim_page = self.frames[victim_frame_id]
        if victim_page is None:
            return victim_frame_id  # This should not happen, but we can just reuse the frame.
        
        if victim_page.is_dirty:
            self.disk_manager.write_page(victim_page)
            self.flush_count += 1

        self.page_table.pop(victim_page.page_id, None)
        self.frames[victim_frame_id] = None
        self.eviction_count += 1
        return victim_frame_id

    def fetch_page(self, page_id: int) -> Page:
        # First check if the page is already in the buffer pool. If so, pin it and return it.
        frame_id = self._get_frame_id(page_id)
        if frame_id is not None:
            page = self.frames[frame_id]
            if page is None:
                raise RuntimeError("Inconsistent state: page table points to an empty frame.")
            
            self.hit_count += 1
            page.pin_count += 1
            self._mark_frame_evictable(frame_id, False)
            return page
        #On a miss, we need to read the page from disk, potentially evicting an existing page if the buffer pool is full.
        self.miss_count += 1
        frame_id = self._evict_if_needed()
        page = self.disk_manager.read_page(page_id)
        page.pin_count = 1
        self.frames[frame_id] = page
        self.page_table[page_id] = frame_id
        self._mark_frame_evictable(frame_id, False)
        return page

    def new_page(self) -> Page:
        # Allocate a new page on disk, then fetch it into the buffer pool. This is similar to fetch_page but we need to allocate a new page ID first.
        page_id = self.disk_manager.allocate_page()
        frame_id = self._evict_if_needed()
        page = Page(page_id=page_id)
        page.pin_count = 1
        self.frames[frame_id] = page
        self.page_table[page_id] = frame_id
        self._mark_frame_evictable(frame_id, False)
        return page

    def unpin_page(self, page_id: int, is_dirty: bool = False) -> bool:
        #Unpin a page in the buffer pool, potentially marking it as dirty. If the page is not currently pinned, this should return False to indicate an error. If the page becomes unpinned (pin count goes to 0), it should be marked as evictable in the replacement policy.
        frame_id = self._get_frame_id(page_id)
        if frame_id is None:
            return False  
        
        page = self.frames[frame_id]
        if page is None or page.pin_count <= 0:
            return False
        
        if is_dirty:
            page.is_dirty = True
        
        page.pin_count -= 1
        if page.pin_count == 0:
            self._mark_frame_evictable(frame_id, True)

        return True


    def flush_page(self, page_id: int) -> bool:
        #Flush a specific page from the buffer pool to disk if it is dirty. This should write the page back to disk and mark it as clean. If the page is not currently in the buffer pool, this should return False to indicate an error.
        frame_id = self._get_frame_id(page_id)
        if frame_id is None:
            return False
        
        page = self.frames[frame_id]
        if page is None:
            return False
        
        self.disk_manager.write_page(page)
        self.flush_count += 1
        return True

    def flush_all_pages(self) -> None:
        # Flush all dirty pages from the buffer pool to disk. This should iterate through all frames in the buffer pool and write any dirty pages back to disk, marking them as clean.
        for page in self.frames:
            if page is not None and page.is_dirty:
                self.disk_manager.write_page(page)
                self.flush_count += 1

    def delete_page(self, page_id: int) -> bool:
        #Delete a page from the buffer pool and disk. This should remove the page from the buffer pool if it is present (only if it is not currently pinned), and then deallocate the page on disk. If the page is currently pinned, this should return False to indicate an error. If the page is successfully deleted, this should return True.
        frame_id = self._get_frame_id(page_id)
        if frame_id is not None:
            page = self.frames[frame_id]
            if page is not None and page.pin_count > 0:
                return False  
            self.replacer.remove(frame_id)
            self.frames[frame_id] = None
            self.page_table.pop(page_id, None)
            self.free_list.append(frame_id)

        result = self.disk_manager.delete_page(page_id)
        if result:
            self.delete_count += 1
        return result

    def get_stats(self) -> dict[str, float]:
        disk_stats = self.disk_manager.get_stats()
        return {
            "pool_size": self.pool_size,
            "policy": self.replacement_policy_name,
            "hits": self.hit_count,
            "misses": self.miss_count,
            "evictions": self.eviction_count,
            "flushes": self.flush_count,
            "deletes": self.delete_count,
            "disk_reads": disk_stats["reads"],
            "disk_writes": disk_stats["writes"],
            "simulated_time_ms": disk_stats["simulated_time_ms"],
        }
