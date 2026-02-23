from availability_evaluation import *

if __name__ == '__main__':
    # Load Germany_17 topology
    G,_,_ = read_graph('topologies', 'Germany_17')
    # Create node availability list
    A_dic = {node: 0.99 for node in G.nodes}
    # Evaluate the availability of a source-destination pair
    result = calculate_availability_cpp(G, 4, 15, A_dic)
    # Result is a tuple contains the souce destination and the availability
    # The source and destination are added by 1
    print(result)
    
    
    # Multithreading
    # Load Germany_17 topology
    G,_,_ = read_graph('topologies', 'Germany_17')
    # Create node availability list
    A_dic = {node: 0.99 for node in G.nodes}
    # Evaluate the availability of all source-destination pair
    results = calculate_availability_multithreading_cpp(G, A_dic)
    # Results is a list of tuples contains the souce destination and the availability
    # The source and destination are added by 1
    print(results)

    # Directed system with uni-/bi-directional edges and virtual source/sink
    directed_topology = {
        "nodes": [
            {"id": "source", "weight": 1, "virtual": True},
            {"id": "A", "weight": 1},
            {"id": "B", "weight": 2},
            {"id": "C", "weight": 1},
            {"id": "sink", "weight": 1, "virtual": True},
        ],
        "edges": [
            {"source": "source", "target": "A", "direction": "uni"},
            {"source": "A", "target": "B", "direction": "bi"},
            {"source": "B", "target": "C", "direction": "uni"},
            {"source": "C", "target": "A", "direction": "uni"},
            {"source": "C", "target": "sink", "direction": "uni"},
        ],
    }
    directed_base_availability = {
        "source": 1.0,
        "A": 0.99,
        "B": 0.98,
        "C": 0.99,
        "sink": 1.0,
    }
    directed_result = calculate_directed_system_availability(
        directed_topology,
        source="source",
        sink="sink",
        node_availability=directed_base_availability,
    )
    print(directed_result)

    # Build symbolic availability function for BI tools (PowerBI, etc.)
    directed_function = build_directed_system_availability_function(
        directed_topology,
        source="source",
        sink="sink",
    )
    print(directed_function["expression"])
    print(directed_function["symbols"])
    
    # Multiprocessing
    # Load Germany_17 topology
    G,_,_ = read_graph('topologies', 'Germany_17')
    # Create node availability list
    A_dic = {node: 0.99 for node in G.nodes}
    # Evaluate the availability of all source-destination pair
    results = calculate_availability_multiprocessing_cpp(G, A_dic)
    # Results is a list of tuples contains the souce destination and the availability
    # The source and destination are added by 1
    print(results)
