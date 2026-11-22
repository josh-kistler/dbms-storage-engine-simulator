# DBMS Storage Engine Simulator

A simplified database storage-engine simulation implemented in **Python** to explore how indexing, buffer management, page replacement, and workload characteristics affect database performance.

The system integrates a disk-backed page model with a buffer pool and B+ tree index, supporting multiple replacement policies and benchmark workloads.

I completed this project individually as part of a Database Concepts course.

## Features

- Disk-backed fixed-size page storage
- Buffer pool with configurable capacity
- Page pinning and unpinning
- Dirty-page tracking and flushing
- LRU page replacement
- Clock / second-chance page replacement
- B+ tree insertion and lookup
- B+ tree node splitting
- Linked B+ tree leaf nodes
- Range queries
- Point lookups
- Sequential and skewed workloads
- Simulated disk-access costs
- Benchmarking across multiple configurations
- Automated tests

## Architecture

The simulator follows a layered DBMS-style architecture:

```text
Workload Generator
        ↓
    B+ Tree
        ↓
Buffer Pool Manager
        ↓
   Disk Manager
        ↓
 Simulated Disk
```

A query first uses the B+ tree to determine which pages contain the desired data.

The buffer pool then determines whether those pages can be served from memory or must be retrieved through the simulated disk manager.

This allows the benchmark to evaluate not only query behavior, but the interaction between indexing, caching, replacement policy, and storage cost.

## My Implementation

The project used course-provided infrastructure for parts of the simulation and evaluation framework.

My primary implementation work focused on:

### Buffer Pool Manager

The buffer pool maintains a fixed number of in-memory page frames and maps disk page IDs to those frames.

Implemented behavior includes:

- Page fetching
- Cache-hit and cache-miss tracking
- Page allocation
- Pin/unpin management
- Dirty-page handling
- Page eviction
- Page flushing
- Page deletion
- Replacement-policy integration
- Buffer statistics

Only unpinned pages are eligible for eviction.

Dirty pages are written to disk before their frames are reused.

### LRU Replacement

The LRU implementation tracks evictable frames in least-recently-used order.

When an evictable frame is accessed, its recency is updated. When a victim is required, the least recently used eligible frame is selected.

### Clock Replacement

The Clock implementation approximates LRU using:

- A circular clock hand
- Per-frame reference bits
- Evictable-frame state

Recently accessed pages receive a second chance before being selected for eviction.

### B+ Tree

The B+ tree maps integer keys to stored values through disk-backed tree nodes.

The implementation supports:

- Sorted insertion
- Exact-key lookup
- Range search
- Leaf splitting
- Internal-node splitting
- Root splitting
- Separator-key promotion
- Linked leaves

B+ tree nodes are serialized into disk pages, so tree operations interact directly with the buffer manager rather than operating only on in-memory Python objects.

## B+ Tree Insertion

When a leaf exceeds the configured tree order, it is divided into two nodes.

The first key of the new right leaf is promoted to its parent.

Internal-node overflow similarly causes a split, with the middle separator key promoted upward.

If the root splits, a new root is created.

```text
Insert Key
    ↓
Find Target Leaf
    ↓
Insert in Sorted Position
    ↓
Node Overflow?
   /       \
 No        Yes
 |          |
Save      Split Node
             ↓
       Promote Separator
             ↓
       Parent Overflow?
```

Linked leaf nodes allow range queries to continue sequentially after locating the first relevant leaf.

## Buffer Pool

When a page is requested:

```text
Request Page
     ↓
Page in memory?
   /       \
 Yes       No
  |         |
Cache     Find free frame
Hit           ↓
  |       Evict if needed
Pin           ↓
Page       Load from disk
              ↓
             Pin
```

If the buffer is full, the configured replacement algorithm selects an eligible frame.

Pinned pages cannot be evicted.

## Simulated Storage Costs

The course-provided disk simulation models different storage costs for operations such as:

- Random page access
- Sequential page access
- Page transfer
- Memory hits

This makes it possible to compare configurations using simulated execution cost rather than only counting accesses.

## Workloads

The benchmark evaluates multiple access patterns:

- **Point** — individual key lookups
- **Range** — searches across key intervals
- **Scan** — sequential range traversal
- **Skewed** — repeated access to a smaller set of hot keys
- **Mixed** — combination of several query types

These workloads expose different locality and caching characteristics.

## Benchmark Configuration

The included benchmark evaluates combinations of:

| Parameter | Values |
| --- | --- |
| Replacement policy | LRU, Clock |
| Buffer pool size | 4, 8, 16 frames |
| Page capacity | 16, 32 |
| Workload | Point, Range, Scan, Skewed, Mixed |
| Operations | 50 per workload |
| Random seed | 0 |

A complete benchmark run produces **60 configurations**.

## Results

The largest performance difference came from **buffer pool capacity** rather than replacement policy.

Average benchmark results included:

| Policy | Pool Size | Hit Rate | Disk Reads | Evictions | Simulated Time |
| --- | ---: | ---: | ---: | ---: | ---: |
| Clock | 4 | 0.9311 | 22.4 | 24.5 | 1.872 ms |
| LRU | 4 | 0.9416 | 19.0 | 21.1 | 1.578 ms |
| Clock | 8 | 1.0000 | 0 | 0 | 0.690 ms |
| LRU | 8 | 1.0000 | 0 | 0 | 0.690 ms |
| Clock | 16 | 1.0000 | 0 | 0 | 0.690 ms |
| LRU | 16 | 1.0000 | 0 | 0 | 0.690 ms |

With only four frames, LRU generally produced slightly higher cache hit rates and fewer disk reads and evictions than Clock.

Once the working set fit within the larger buffer pools, both policies converged to essentially identical performance.

## Benchmark Visualizations

The project generates plots for:

- Cache hit rate
- Simulated execution time
- Disk reads
- Page evictions

These are stored under:

```text
results/plots/
```

## Tests

The included automated test suite covers:

- Disk management
- Buffer pool behavior
- Replacement policies
- B+ tree operations
- Workload generation
- Integration
- Benchmark execution

Current result:

```text
12 passed
```

## Project Structure

```text
dbms-storage-engine-simulator/
├── src/
│   ├── bplustree.py
│   ├── buffer_pool_manager.py
│   ├── replacement.py
│   ├── disk_manager.py
│   ├── simulator.py
│   ├── workload.py
│   ├── benchmark.py
│   ├── plot_results.py
│   └── ...
│
├── tests/
│   ├── test_bplustree.py
│   ├── test_buffer_pool.py
│   ├── test_replacement.py
│   └── ...
│
├── results/
│   ├── benchmark_results.csv
│   └── plots/
│
├── docs/
├── README.md
└── .gitignore
```

## Running the Tests

```bash
python -m pytest -q
```

Expected result:

```text
12 passed
```

## Running the Simulator

```bash
python src/main.py
```

## Running the Benchmark

```bash
python src/benchmark.py
```

The benchmark writes its results to:

```text
results/benchmark_results.csv
```

## Generating Plots

```bash
python src/plot_results.py results/benchmark_results.csv
```

## Technologies and Concepts

- Python
- Database management systems
- B+ trees
- Buffer management
- LRU replacement
- Clock replacement
- Page-based storage
- Cache management
- Disk I/O simulation
- Benchmarking
- Automated testing
- Performance analysis

## Project Provenance

This project was completed using course-provided starter infrastructure.

The disk manager, base data models, simulator integration, benchmark driver, plotting utilities, and public tests were provided as part of the assignment framework.

My implementation focused on the **buffer pool manager, LRU and Clock replacement policies, and B+ tree functionality**, including insertion, splitting, search, and range queries.

The benchmark results and performance analysis were produced using the completed integrated system.
