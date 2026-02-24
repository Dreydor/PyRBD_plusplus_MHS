"""
    Consist of all availability evaluation methods
"""
import os
import pickle as pkl
import networkx as nx
from itertools import combinations
from typing import Dict, List
try:
    import build.rbd_bindings
except ModuleNotFoundError:
    build = None

from cutsets import optimized_minimalcuts


def build_directed_graph_from_topology(topology: dict) -> nx.DiGraph:
    """Build a directed graph from a topology payload.

    Expected format:
    {
        "nodes": [{"id": "A", "weight": 2}, ...],
        "edges": [
            {"source": "source", "target": "A", "bidirectional": false},
            {"source": "A", "target": "B", "bidirectional": true}
        ]
    }

    The ``weight`` node attribute is preserved and later used as a k-factor
    exponent in symbolic availability functions.
    """
    graph = nx.DiGraph()

    for node in topology.get("nodes", []):
        node_id = node["id"]
        node_weight = node.get("weight", 1)
        graph.add_node(node_id, weight=node_weight)

    for edge in topology.get("edges", []):
        source = edge["source"]
        target = edge["target"]
        graph.add_edge(source, target)
        if edge.get("bidirectional", False):
            graph.add_edge(target, source)

    return graph


def _component_unavailability_symbol(node: str, weight: float) -> str:
    """Return unavailability symbol with weighted k-factor.

    Node availability variable is represented as ``A_<id>``.
    With k-factor weighting, effective availability is ``A_<id>^weight``.
    So unavailability is ``(1 - A_<id>^weight)``.
    """
    symbol = f"A_{node}"
    if float(weight) == 1.0:
        return f"(1 - {symbol})"
    return f"(1 - ({symbol}^{weight}))"


def _inclusion_exclusion_terms(minimal_cutsets: List[List[str]], node_weights: Dict[str, float]) -> List[str]:
    """Build inclusion-exclusion polynomial terms for union of minimal cut-set failures."""
    terms = []
    cutset_count = len(minimal_cutsets)

    for r in range(1, cutset_count + 1):
        sign = " + " if r % 2 == 1 else " - "
        for selected in combinations(minimal_cutsets, r):
            merged_nodes = sorted({node for cutset in selected for node in cutset})
            node_terms = [_component_unavailability_symbol(node, node_weights.get(node, 1)) for node in merged_nodes]
            terms.append(f"{sign}({' * '.join(node_terms)})")

    return terms


def availability_function_for_directed_system(
    graph: nx.DiGraph,
    source: str,
    sink: str,
    node_weights: Dict[str, float] = None,
) -> str:
    """Return a symbolic availability function for a directed system.

    The returned expression uses inclusion-exclusion over minimal cut sets.
    Source and sink are treated as virtual (100% reliable), therefore excluded
    from cut sets and the final function.
    """
    if node_weights is None:
        node_weights = {node: graph.nodes[node].get("weight", 1) for node in graph.nodes}

    minimal_cutsets = optimized_minimalcuts(graph, source, sink)
    filtered_cutsets = [
        [node for node in cutset if node not in {source, sink}]
        for cutset in minimal_cutsets
        if set(cutset) != {source} and set(cutset) != {sink}
    ]
    filtered_cutsets = [cutset for cutset in filtered_cutsets if cutset]

    if not filtered_cutsets:
        return "1"

    union_failure_terms = _inclusion_exclusion_terms(filtered_cutsets, node_weights)
    union_failure = "".join(union_failure_terms).lstrip(" + ")
    return f"1 - ({union_failure})"

# Load data from a pickle file
def read_graph(directory, top):
    """Load graph payload from pickle.

    Supported pickle formats:
    1) Legacy tuple/list: (graph, pos, label)
    2) Direct graph object
    3) Directed-topology dict: {"nodes": ..., "edges": ...}
    """
    with open(os.path.join(directory, 'Pickle_' + top + '.pickle'), 'rb') as handle:
        payload = pkl.load(handle)

    # Legacy format: [G, pos, label]
    if isinstance(payload, (list, tuple)) and len(payload) >= 3:
        return payload[0], payload[1], payload[2]

    # Newer format: topology dictionary
    if isinstance(payload, dict) and 'nodes' in payload and 'edges' in payload:
        graph = build_directed_graph_from_topology(payload)
        return graph, None, None

    # Fallback: graph-only payload
    if hasattr(payload, 'nodes') and hasattr(payload, 'edges'):
        return payload, None, None

    raise ValueError(
        f"Unsupported topology pickle format for '{top}'. "
        "Expected (graph, pos, label), graph object, or topology dict with 'nodes'/'edges'."
    )

# Relabel the nodes of G and A_dic
def relabel_graph_A_dict(G, A_dic):
    # Get the nodes of G
    nodes = list(G.nodes())
    # Create a mapping of the nodes to new labels
    relabel_mapping = {nodes[i]: i + 1 for i in range(len(nodes))}
    # Relabel the nodes of G
    G_relabel = nx.relabel_nodes(G, relabel_mapping)
    # Relabel the nodes in A_dict
    A_dic = {relabel_mapping[node]: value for node, value in A_dic.items()}
    return G_relabel, A_dic, relabel_mapping

def calculate_availability_cpp(G, source, target, A_dic):
    
    # Relabel the nodes of G and A_dic
    G, A_dic, relabel_mapping = relabel_graph_A_dict(G, A_dic)
    
    # Find the new source and target
    source = relabel_mapping[source]
    target = relabel_mapping[target]
    
    # Calculate the availability
    if build is None:
        raise ModuleNotFoundError("build.rbd_bindings is not available. Build the C++ extension first.")
    result = build.rbd_bindings.evaluateAvailability(optimized_minimalcuts(G, source, target), A_dic, source, target)
    return (source, target, result)
    

def calculate_availability_multiprocessing_cpp(G, A_dic):
    # Relabel the nodes of G and A_dic
    G, A_dic, _ = relabel_graph_A_dict(G, A_dic)
    node_pairs = list(combinations(G.nodes(), 2))
    mincutsets = [optimized_minimalcuts(G, pair[0], pair[1]) for pair in node_pairs]
    if build is None:
        raise ModuleNotFoundError("build.rbd_bindings is not available. Build the C++ extension first.")
    results = build.rbd_bindings.evaluateAvailabilityTopologyMultiProcessing(mincutsets, A_dic, node_pairs)
    
    return results

def calculate_availability_multithreading_cpp(G, A_dic):
    # Relabel the nodes of G and A_dic
    G, A_dic, _ = relabel_graph_A_dict(G, A_dic)
    node_pairs = list(combinations(G.nodes(), 2))
    mincutsets = [optimized_minimalcuts(G, pair[0], pair[1]) for pair in node_pairs]
    if build is None:
        raise ModuleNotFoundError("build.rbd_bindings is not available. Build the C++ extension first.")
    results = build.rbd_bindings.evaluateAvailabilityTopologyMultiThreading(mincutsets, A_dic, node_pairs)
    
    return results
