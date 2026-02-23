"""
    Consist of all availability evaluation methods
"""
from itertools import combinations
import os
import pickle as pkl
import networkx as nx

from cutsets import optimized_minimalcuts

# Load data from a pickle file
def read_graph(directory, top):
    with open(os.path.join(directory, 'Pickle_' + top + '.pickle'), 'rb') as handle:
        f = pkl.load(handle)
    G = f[0]
    pos = f[1]
    lable = f[2]

    return G, pos, lable

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
    import build.rbd_bindings
    
    # Relabel the nodes of G and A_dic
    G, A_dic, relabel_mapping = relabel_graph_A_dict(G, A_dic)
    
    # Find the new source and target
    source = relabel_mapping[source]
    target = relabel_mapping[target]
    
    # Calculate the availability
    result = build.rbd_bindings.evaluateAvailability(optimized_minimalcuts(G, source, target), A_dic, source, target)
    return (source, target, result)
    

def calculate_availability_multiprocessing_cpp(G, A_dic):
    import build.rbd_bindings
    # Relabel the nodes of G and A_dic
    G, A_dic, _ = relabel_graph_A_dict(G, A_dic)
    node_pairs = list(combinations(G.nodes(), 2))
    mincutsets = [optimized_minimalcuts(G, pair[0], pair[1]) for pair in node_pairs]
    results = build.rbd_bindings.evaluateAvailabilityTopologyMultiProcessing(mincutsets, A_dic, node_pairs)
    
    return results

def calculate_availability_multithreading_cpp(G, A_dic):
    import build.rbd_bindings
    # Relabel the nodes of G and A_dic
    G, A_dic, _ = relabel_graph_A_dict(G, A_dic)
    node_pairs = list(combinations(G.nodes(), 2))
    mincutsets = [optimized_minimalcuts(G, pair[0], pair[1]) for pair in node_pairs]
    results = build.rbd_bindings.evaluateAvailabilityTopologyMultiThreading(mincutsets, A_dic, node_pairs)
    
    return results


def _normalize_edge_direction(direction):
    """Normalize user-provided direction strings to uni-/bi-directional tokens."""
    if direction is None:
        return 'uni'
    value = str(direction).strip().lower()
    if value in {'bi', 'bidirectional', 'both', 'undirected', 'two-way', 'two_way'}:
        return 'bi'
    return 'uni'


def build_directed_graph_from_topology(topology):
    """
    Build a directed graph from a topology definition.

    Expected keys in ``topology``:
      - nodes: [{"id": <node_id>, "weight": <k-factor>}]
      - edges: [{"source": <src>, "target": <dst>, "direction": "uni"|"bi"}]

    Notes:
      - Nodes with ``virtual=True`` are considered 100% reliable endpoints.
      - Edges marked as bidirectional add both directed arcs.
    """
    graph = nx.DiGraph()
    weights = {}
    virtual_nodes = set()

    for node in topology.get('nodes', []):
        node_id = node['id']
        k_factor = float(node.get('weight', 1.0))
        graph.add_node(node_id)
        weights[node_id] = k_factor
        if node.get('virtual', False):
            virtual_nodes.add(node_id)

    for edge in topology.get('edges', []):
        src = edge['source']
        dst = edge['target']
        direction = _normalize_edge_direction(edge.get('direction', 'uni'))

        graph.add_edge(src, dst)
        if direction == 'bi':
            graph.add_edge(dst, src)

    return graph, weights, virtual_nodes


def apply_weight_k_factor(node_availability, node_weights, virtual_nodes=None):
    """
    Apply node weight as the k-factor in the availability transformation.

    For each non-virtual node with base availability ``A`` and weight ``k``:
        A_eff = 1 - (1 - A)^k

    Virtual nodes are always treated as perfectly reliable (A_eff = 1.0).
    """
    virtual_nodes = virtual_nodes or set()
    weighted_availability = {}

    for node, availability in node_availability.items():
        if node in virtual_nodes:
            weighted_availability[node] = 1.0
            continue

        k_factor = float(node_weights.get(node, 1.0))
        if k_factor < 0:
            raise ValueError(f"Node '{node}' has invalid negative weight: {k_factor}")
        weighted_availability[node] = 1.0 - ((1.0 - availability) ** k_factor)

    return weighted_availability


def calculate_directed_system_availability(topology, source, sink, node_availability):
    """
    Evaluate availability in directed systems with optional cyclic loops.

    The function expects one virtual source and one virtual sink used only for flow
    orientation. Their availability is forced to 1.0.
    """
    graph, node_weights, virtual_nodes = build_directed_graph_from_topology(topology)

    if source not in graph:
        raise ValueError(f"Source node '{source}' does not exist in topology")
    if sink not in graph:
        raise ValueError(f"Sink node '{sink}' does not exist in topology")

    if source not in virtual_nodes:
        virtual_nodes.add(source)
    if sink not in virtual_nodes:
        virtual_nodes.add(sink)

    weighted_availability = apply_weight_k_factor(node_availability, node_weights, virtual_nodes)
    return calculate_availability_cpp(graph, source, sink, weighted_availability)


def _make_disjoint_set(base_set, target_set):
    """Python version of C++ makeDisjointSet used for symbolic expression generation."""
    rc = []
    for elem in base_set:
        if -elem in target_set:
            return [target_set]
        if elem not in target_set:
            rc.append(elem)

    if not rc:
        return []

    result = []
    work = list(target_set)
    for elem in rc:
        work.append(-elem)
        result.append(list(work))
        work[-1] = -work[-1]

    return result


def _mincut_to_probaset(src, dst, mincutset):
    """Python version of C++ minCutSetToProbaset used for symbolic expression generation."""
    work = [list(s) for s in mincutset if s not in ([src], [dst])]
    if not work:
        return []

    for i, subset in enumerate(work):
        work[i] = [-elem for elem in subset]

    prob_set = []
    while work:
        if len(work) == 1:
            prob_set.append(work[0])
            break

        selected = work[0]
        prob_set.append(selected)
        remaining = work[1:]
        work = []

        for subset in remaining:
            work.extend(_make_disjoint_set(selected, subset))

    return prob_set


def _availability_symbol(node_id):
    """Convert a node id to a PowerBI-safe availability symbol."""
    safe = ''.join(ch if ch.isalnum() else '_' for ch in str(node_id))
    return f"A_{safe}"


def _weighted_symbol(node_id, node_weights, virtual_nodes):
    """Return weighted availability term for a node in symbolic form."""
    if node_id in virtual_nodes:
        return "1"

    base_symbol = _availability_symbol(node_id)
    k_factor = float(node_weights.get(node_id, 1.0))
    if k_factor < 0:
        raise ValueError(f"Node '{node_id}' has invalid negative weight: {k_factor}")
    if k_factor == 1:
        return base_symbol
    return f"(1 - POWER(1 - {base_symbol}, {k_factor:g}))"


def build_directed_system_availability_function(topology, source, sink):
    """
    Build symbolic availability function for a directed system.

    Returns a dictionary with:
      - expression: string formula using A_<node_id> base symbols
      - symbols: mapping of node_id to base symbol name
      - weighted_symbols: mapping of node_id to weighted symbolic term
      - relabel_mapping: mapping of original node IDs to internal integer IDs
    """
    graph, node_weights, virtual_nodes = build_directed_graph_from_topology(topology)

    if source not in graph:
        raise ValueError(f"Source node '{source}' does not exist in topology")
    if sink not in graph:
        raise ValueError(f"Sink node '{sink}' does not exist in topology")

    virtual_nodes = set(virtual_nodes)
    virtual_nodes.add(source)
    virtual_nodes.add(sink)

    relabeled_graph, _, relabel_mapping = relabel_graph_A_dict(graph, {n: 1.0 for n in graph.nodes})
    inv_mapping = {v: k for k, v in relabel_mapping.items()}
    src_relabeled = relabel_mapping[source]
    sink_relabeled = relabel_mapping[sink]
    mincutset = optimized_minimalcuts(relabeled_graph, src_relabeled, sink_relabeled)
    prob_set = _mincut_to_probaset(src_relabeled, sink_relabeled, mincutset)

    weighted_symbols = {
        node: _weighted_symbol(node, node_weights, virtual_nodes)
        for node in graph.nodes
    }
    base_symbols = {node: _availability_symbol(node) for node in graph.nodes if node not in virtual_nodes}

    if not prob_set:
        expression = "1"
    else:
        terms = []
        for subset in prob_set:
            factors = []
            for literal in subset:
                node_id = inv_mapping[abs(literal)]
                symbol = weighted_symbols[node_id]
                if literal < 0:
                    factors.append(f"(1 - {symbol})")
                else:
                    factors.append(f"({symbol})")
            terms.append(' * '.join(factors) if factors else '1')

        unavailability = ' + '.join(f"({term})" for term in terms)
        expression = f"1 - ({unavailability})"

    return {
        'expression': expression,
        'symbols': base_symbols,
        'weighted_symbols': weighted_symbols,
        'relabel_mapping': relabel_mapping,
    }
