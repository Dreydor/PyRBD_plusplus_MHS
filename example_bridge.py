"""Example: generate symbolic availability function for directed bridge topology."""

from availability_evaluation import (
    availability_function_for_directed_system,
    read_graph,
)


if __name__ == '__main__':
    # Load directed bridge topology from topologies/Pickle_bridge.pickle
    graph, _, _ = read_graph('topologies', 'bridge')

    # Build symbolic system availability expression using node metadata:
    # is_input=True nodes are parallel starts, is_output=True nodes are parallel ends
    availability_expression = availability_function_for_directed_system(graph)

    print('System availability function:')
    print(availability_expression)
