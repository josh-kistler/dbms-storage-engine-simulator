"""
Project: B461-Database Concepts - Summer 2026
Student implementation: Josh Kistler
Role: Course starter scaffold with student TODO sections completed

Protected sections marked [INSTRUCTOR ONLY] remain part of the course-provided framework.
"""

"""Simplified B+ tree for the student starter."""

import json
from bisect import bisect_left, bisect_right
from dataclasses import dataclass, field

try:
    from .buffer_pool_manager import BufferPoolManager
    from .config import BPLUS_ORDER
except ImportError:
    from buffer_pool_manager import BufferPoolManager
    from config import BPLUS_ORDER


@dataclass
class BPlusTreeNode:
    page_id: int
    is_leaf: bool
    keys: list[int] = field(default_factory=list)
    values: list[int] = field(default_factory=list)
    children: list[int] = field(default_factory=list)
    next_leaf: int | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "page_id": self.page_id,
            "is_leaf": self.is_leaf,
            "keys": self.keys,
            "values": self.values,
            "children": self.children,
            "next_leaf": self.next_leaf,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "BPlusTreeNode":
        return cls(
            page_id=int(payload["page_id"]),
            is_leaf=bool(payload["is_leaf"]),
            keys=[int(value) for value in payload.get("keys", [])],
            values=[int(value) for value in payload.get("values", [])],
            children=[int(value) for value in payload.get("children", [])],
            next_leaf=payload.get("next_leaf"),
        )


# ================================
# [STUDENT TODO] IMPLEMENT BELOW
# ================================
class BPlusTree:
    def __init__(
        self,
        buffer_pool_manager: BufferPoolManager,
        order: int = BPLUS_ORDER,
    ) -> None:
        if order < 3:
            raise ValueError("B+ tree order must be at least 3.")

        self.buffer_pool_manager = buffer_pool_manager
        self.order = order
        root = self._allocate_node(is_leaf=True)
        self.root_page_id = root.page_id

    def _serialize(self, node: BPlusTreeNode) -> bytes:
        encoded = json.dumps(node.to_dict(), separators=(",", ":")).encode("utf-8")
        if len(encoded) > self.buffer_pool_manager.disk_manager.page_size:
            raise ValueError("Serialized B+ tree node does not fit in one page.")
        return encoded

    def _allocate_node(self, is_leaf: bool) -> BPlusTreeNode:
        page = self.buffer_pool_manager.new_page()
        node = BPlusTreeNode(page_id=page.page_id, is_leaf=is_leaf)
        self._write_node(node)
        self.buffer_pool_manager.unpin_page(node.page_id)
        return node

    def _read_node(self, page_id: int) -> BPlusTreeNode:
        page = self.buffer_pool_manager.fetch_page(page_id)
        raw = bytes(page.data).rstrip(b"\x00")
        self.buffer_pool_manager.unpin_page(page_id)
        if not raw:
            raise ValueError(f"Page {page_id} does not contain a valid B+ tree node.")
        return BPlusTreeNode.from_dict(json.loads(raw.decode("utf-8")))

    def _write_node(self, node: BPlusTreeNode) -> None:
        page = self.buffer_pool_manager.fetch_page(node.page_id)
        payload = self._serialize(node)
        page.data[:] = b"\x00" * len(page.data)
        page.data[: len(payload)] = payload
        self.buffer_pool_manager.unpin_page(node.page_id, is_dirty=True)

    def _find_leaf_page(self, key: int) -> int:
        # Start at the root and traverse down to the appropriate leaf page for the given key.
        current_page_id = self.root_page_id
        while True:
            node = self._read_node(current_page_id)
            if node.is_leaf:
                return node.page_id
            
            child_index = bisect_right(node.keys, key)
            current_page_id = node.children[child_index]

    def insert(self, key: int, value: int) -> None:
        # Insert ito the root subtree and handle a root split by creating a new root if necessary.
        split_info = self._insert_recursive(self.root_page_id, key, value)
        if split_info is None:
            return
        
        promoted_key, right_page_id = split_info
        old_root_page_id = self.root_page_id
        new_root = self._allocate_node(is_leaf=False)
        new_root.keys = [promoted_key]
        new_root.children = [old_root_page_id, right_page_id]
        self._write_node(new_root)
        self.root_page_id = new_root.page_id

    def _insert_recursive(self, page_id: int, key: int, value: int) -> tuple[int, int] | None:
        # Return None if no split occurred, otherwise return (promoted_key, new_page_id).
        node = self._read_node(page_id)
        if node.is_leaf:
            return self._insert_into_leaf(node, key, value)
        return self._insert_into_internal(node, key, value)

    def _insert_into_leaf(
        self,
        node: BPlusTreeNode,
        key: int,
        value: int,
    ) -> tuple[int, int] | None:
        # Keep leaf keys sorted and update the value if the key already exists. If the leaf overflows, split it and return the promoted separator key and new right page ID.
        position = bisect_left(node.keys, key)
        if position < len(node.keys) and node.keys[position] == key:
            node.values[position] = value
            self._write_node(node)
            return None
        node.keys.insert(position, key)
        node.values.insert(position, value)
        if len(node.keys) < self.order:
            self._write_node(node)
            return None
        return self._split_leaf(node)

    def _insert_into_internal(
        self,
        node: BPlusTreeNode,
        key: int,
        value: int,
    ) -> tuple[int, int] | None:
        # Route the insertion to the correct child and handle a child split by inserting the promoted key and new child pointer into the internal node. If the internal node overflows, split it and return the promoted separator key and new right page ID.
        child_index = bisect_right(node.keys, key)
        child_page_id = node.children[child_index]
        child_split = self._insert_recursive(child_page_id, key, value)
        if child_split is None:
            return None
        promoted_key, right_page_id = child_split
        insert_position = bisect_right(node.keys, promoted_key)
        node.keys.insert(insert_position, promoted_key)
        node.children.insert(insert_position + 1, right_page_id)
        if len(node.keys) < self.order:
            self._write_node(node)
            return None
        return self._split_internal(node)

    def _split_leaf(self, node: BPlusTreeNode) -> tuple[int, int]:
        # Split the leaf into left and right leaves and return the promoted separator key and new right page ID. The promoted key is the first key of the new right leaf.
        split_index = len(node.keys) // 2
        right_node = self._allocate_node(is_leaf=True)
        right_node.keys = node.keys[split_index:]
        right_node.values = node.values[split_index:]
        right_node.next_leaf = node.next_leaf
        node.keys = node.keys[:split_index]
        node.values = node.values[:split_index]
        node.next_leaf = right_node.page_id
        self._write_node(node)
        self._write_node(right_node)
        return (right_node.keys[0], right_node.page_id)

    def _split_internal(self, node: BPlusTreeNode) -> tuple[int, int]:
        # Promote the middle key and split the internal node into left and right nodes. The promoted key is removed from the left node and becomes the separator in the parent. 
        mid_index = len(node.keys) // 2
        promoted_key = node.keys[mid_index]
        right_node = self._allocate_node(is_leaf=False)
        right_node.keys = node.keys[mid_index + 1 :]
        right_node.children = node.children[mid_index + 1 :]
        node.keys = node.keys[:mid_index]
        node.children = node.children[: mid_index + 1]
        self._write_node(node)
        self._write_node(right_node)
        return (promoted_key, right_node.page_id)

    def search(self, key: int) -> int | None:
        # Find the target leaf, then do an exact match search for the key and return the corresponding value if found, otherwise return None.
        leaf_page_id = self._find_leaf_page(key)
        leaf = self._read_node(leaf_page_id)
        position = bisect_left(leaf.keys, key)
        if position < len(leaf.keys) and leaf.keys[position] == key:
            return leaf.values[position]
        return None

    def range_search(self, start_key: int, end_key: int) -> list[tuple[int, int]]:
        # Locate the first relevant leaf page for start_key, then iterate through the leaf pages and collect all key-value pairs where the key is in the range [start_key, end_key]. Stop once we encounter a key greater than end_key or reach the end of the leaf pages. 
        if start_key > end_key:
            return []
        results: list[tuple[int, int]] = []
        current_page_id: int | None = self._find_leaf_page(start_key)
        while current_page_id is not None:
            leaf = self._read_node(current_page_id)
            for key, value in zip(leaf.keys, leaf.values):
                if key > end_key:
                    return results
                if key >= start_key:
                    results.append((key, value))
            current_page_id = leaf.next_leaf
        return results


__all__ = ["BPlusTreeNode", "BPlusTree"]
