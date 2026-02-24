"""
    Consist of all availability evaluation methods
"""
import os
import pickle as pkl
import networkx as nx
from itertools import combinations
from typing import Dict, List, Optional, Tuple
try:
    import build.rbd_bindings
except ModuleNotFoundError:
    build = None

from cutsets import optimized_minimalcuts


def build_directed_graph_from_topology(topology: dict) -> nx.DiGraph:
    """Build a directed graph from a topology payload.

    Expected node format:
      {"id": "A", "weight": 2, "is_input": False, "is_output": False}

    Expected edge format:
      {"source": "A", "target": "B", "bidirectional": False}

    ``weight`` is preserved for k-factor usage in symbolic availability,
    ``is_input`` and ``is_output`` define start/end node sets.
    """
    graph = nx.DiGraph()

    for node in topology.get("nodes", []):
        node_id = node["id"]
        graph.add_node(
            node_id,
            weight=node.get("weight", 1),
            is_input=bool(node.get("is_input", False)),
            is_output=bool(node.get("is_output", False)),
        )

    for edge in topology.get("edges", []):
        source = edge["source"]
        target = edge["target"]
        graph.add_edge(source, target)
        if edge.get("bidirectional", False):
            graph.add_edge(target, source)

    return graph




def _derive_terminal_nodes(graph: nx.DiGraph) -> Tuple[List[str], List[str]]:
    input_nodes = [n for n, data in graph.nodes(data=True) if data.get("is_input", False)]
    output_nodes = [n for n, data in graph.nodes(data=True) if data.get("is_output", False)]

    if not input_nodes:
        raise ValueError("No input nodes found. Mark at least one node with is_input=True.")
    if not output_nodes:
        raise ValueError("No output nodes found. Mark at least one node with is_output=True.")

    return input_nodes, output_nodes


def _augment_graph_with_parallel_terminals(graph: nx.DiGraph) -> Tuple[nx.DiGraph, str, str]:
    input_nodes, output_nodes = _derive_terminal_nodes(graph)

    augmented = graph.copy()
    super_source = "__virtual_input__"
    super_sink = "__virtual_output__"

    while super_source in augmented or super_sink in augmented:
        super_source = f"_{super_source}"
        super_sink = f"_{super_sink}"

    augmented.add_node(super_source, weight=1, is_input=False, is_output=False)
    augmented.add_node(super_sink, weight=1, is_input=False, is_output=False)

    for node in input_nodes:
        augmented.add_edge(super_source, node)
    for node in output_nodes:
        augmented.add_edge(node, super_sink)

    return augmented, super_source, super_sink

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
    """Build inclusion-exclusion polynomial terms for union of minimal cut-set failures.

    Terms that collapse to the same node product are coefficient-combined.
    """
    coefficients: Dict[Tuple[str, ...], int] = {}
    cutset_count = len(minimal_cutsets)

    for r in range(1, cutset_count + 1):
        sign = 1 if r % 2 == 1 else -1
        for selected in combinations(minimal_cutsets, r):
            merged_nodes = tuple(sorted({node for cutset in selected for node in cutset}))
            coefficients[merged_nodes] = coefficients.get(merged_nodes, 0) + sign

    terms = []
    for merged_nodes, coeff in sorted(coefficients.items(), key=lambda x: (len(x[0]), x[0])):
        if coeff == 0:
            continue
        node_terms = [_component_unavailability_symbol(node, node_weights.get(node, 1)) for node in merged_nodes]
        product = f"({' * '.join(node_terms)})"
        abs_coeff = abs(coeff)
        coeff_prefix = "" if abs_coeff == 1 else f"{abs_coeff} * "
        sign_prefix = " + " if coeff > 0 else " - "
        terms.append(f"{sign_prefix}{coeff_prefix}{product}")

    return terms


def availability_function_for_directed_system(
    graph: nx.DiGraph,
    source: Optional[str] = None,
    sink: Optional[str] = None,
    node_weights: Dict[str, float] = None,
) -> str:
    """Return a symbolic availability function for a directed system.

    Preferred mode uses node attributes ``is_input`` and ``is_output``.
    All inputs are treated in parallel as system starts, all outputs in
    parallel as system ends. ``source``/``sink`` are still accepted for
    backward compatibility.
    """
    if node_weights is None:
        node_weights = {node: graph.nodes[node].get("weight", 1) for node in graph.nodes}

    if source is None or sink is None:
        eval_graph, source, sink = _augment_graph_with_parallel_terminals(graph)
        excluded_nodes = {source, sink}
    else:
        eval_graph = graph
        excluded_nodes = {source, sink}

    minimal_cutsets = optimized_minimalcuts(eval_graph, source, sink)
    filtered_cutsets = [
        [node for node in cutset if node not in excluded_nodes]
        for cutset in minimal_cutsets
        if set(cutset) != {source} and set(cutset) != {sink}
    ]
    filtered_cutsets = [cutset for cutset in filtered_cutsets if cutset]

    # Remove duplicate cut sets that can appear after terminal augmentation
    seen = set()
    unique_cutsets = []
    for cutset in filtered_cutsets:
        key = tuple(sorted(cutset))
        if key not in seen:
            seen.add(key)
            unique_cutsets.append(list(key))

    if not unique_cutsets:
        return "1"

    union_failure_terms = _inclusion_exclusion_terms(unique_cutsets, node_weights)
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
