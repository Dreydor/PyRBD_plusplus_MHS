"""Example: generate symbolic availability function for directed bridge topology."""

import inspect
import networkx as nx

from availability_evaluation import (
    availability_function_for_directed_system,
    read_graph,
)


def _availability_call_compat(graph: nx.DiGraph) -> str:
    """Call compatibility wrapper for old/new availability API signatures."""
    sig = inspect.signature(availability_function_for_directed_system)
    params = list(sig.parameters.values())

    # New API: source/sink are optional and defaults should exist
    if len(params) >= 3 and params[1].default is not inspect._empty and params[2].default is not inspect._empty:
        return availability_function_for_directed_system(graph)

    # Old API fallback: derive single terminals from metadata when possible
    input_nodes = [n for n, d in graph.nodes(data=True) if d.get("is_input", False)]
    output_nodes = [n for n, d in graph.nodes(data=True) if d.get("is_output", False)]

    if len(input_nodes) == 1 and len(output_nodes) == 1:
        return availability_function_for_directed_system(graph, input_nodes[0], output_nodes[0])

    raise TypeError(
        "Installed availability_function_for_directed_system requires source/sink, "
        "but bridge topology has parallel input/output nodes. "
        "Please update availability_evaluation.py to the new API."
    )


if __name__ == '__main__':
    # Load directed bridge topology from topologies/Pickle_bridge.pickle
    graph, _, _ = read_graph('topologies', 'bridge')

    # Build symbolic system availability expression using node metadata:
    # is_input=True nodes are parallel starts, is_output=True nodes are parallel ends
    availability_expression = _availability_call_compat(graph)

    print('System availability function:')
    print(availability_expression)
