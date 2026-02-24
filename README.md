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


## Directed system symbolic availability function
You can now generate a symbolic availability function (instead of a numeric value) for directed systems with uni-directional and bi-directional edges.

```python
from availability_evaluation import (
    build_directed_graph_from_topology,
    availability_function_for_directed_system,
)

topology = {
    "nodes": [
        {"id": "n1", "weight": 2, "is_input": True, "is_output": False},
        {"id": "n2", "weight": 1, "is_input": True, "is_output": False},
        {"id": "n3", "weight": 1, "is_input": False, "is_output": True},
        {"id": "n4", "weight": 1, "is_input": False, "is_output": True},
    ],
    "edges": [
        {"source": "n1", "target": "n3", "bidirectional": False},
        {"source": "n2", "target": "n4", "bidirectional": False},
    ],
}

G = build_directed_graph_from_topology(topology)
expr = availability_function_for_directed_system(G)
print(expr)
```

Output example (depends on topology structure):

```text
1 - ((...))
```

Where each node availability variable is `A_<id>`. Node `weight` is used as a k-factor exponent (`A_<id>^weight`).

Inputs and outputs are defined per-node using `is_input`/`is_output`. All input nodes are treated in parallel as system starts, and all output nodes are treated in parallel as system ends.
