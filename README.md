# PyRBD++
An open-source Python tool for RBD evaluation based on the [PyRBD](https://github.com/shakthij98/PyRBD), which is suitable for complex systems and networks with bidirectional links between components and cyclic loops. PyRBD++ addresses the efficiency limitations of PyRBD by combining boolean techniques with Minimal Cut Set (MCS) methods. The boolean algorithms are implemented in C++ and integrated with Python, significantly improving computational performance.

If you use this tool, please cite us as follows.
S. Janardhanan, Y. Chen, C. Mas-Machuca, "PyRBD++: An Open-Source Fast Reliability Block Diagram Evaluation Tool", International Workshop on Resilient Networks Design and Modeling (RNDM) 2025.

## Installation
Clone the source code

```bash
git clone
```

Install the python libraries:

```bash
pip install -r requirements.txt
```

Build the programm

```bash
mkdir build # if not exist
cd build
cmake ..
make
cd ..
```

## Usage
We provide a example using single-core, multithreading, multiprocessing implementation to evaluate the availability of the topology Germany_17. See the [example.py](example.py).

### Directed topology support
PyRBD++ also supports directed systems (including cyclic loops) with mixed uni-/bi-directional links.

Each node in the topology may contain:
- `id`: node identifier
- `weight`: k-factor used in node availability transformation
- `virtual` (optional): if `true`, node is considered 100% reliable (useful for source/sink)

Each edge contains:
- `source`, `target`
- `direction`: `uni` or `bi`

Use `calculate_directed_system_availability(topology, source, sink, node_availability)`.

To obtain the **availability/reliability function** (instead of a single calculated value), use:

`build_directed_system_availability_function(topology, source, sink)`

This returns a dictionary containing:
- `expression`: a symbolic formula that can be implemented in BI tooling (e.g., PowerBI)
- `symbols`: mapping of each non-virtual node id to its base availability symbol (`A_<id>`)
- `weighted_symbols`: each node's effective availability term after applying the node `weight`

For non-virtual nodes, weighted availability is computed as:

`A_eff = 1 - (1 - A)^k`

where `A` is the base node availability and `k` is the node `weight`.
