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

    # Directed topology symbolic availability function
    topology = {
        "nodes": [
            {"id": "source", "weight": 1},
            {"id": "n1", "weight": 2},
            {"id": "n2", "weight": 1},
            {"id": "sink", "weight": 1},
        ],
        "edges": [
            {"source": "source", "target": "n1", "bidirectional": False},
            {"source": "source", "target": "n2", "bidirectional": False},
            {"source": "n1", "target": "sink", "bidirectional": False},
            {"source": "n2", "target": "sink", "bidirectional": False},
        ],
    }
    directed_graph = build_directed_graph_from_topology(topology)
    expression = availability_function_for_directed_system(directed_graph, "source", "sink")
    print(expression)
