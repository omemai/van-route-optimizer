from ortools.constraint_solver import pywrapcp, routing_enums_pb2

def solve_cvrp(distance_matrix, demands, capacities, starts):
    num_vehicles = len(capacities)
    ends = starts  # each vehicle ends at its start

    manager = pywrapcp.RoutingIndexManager(
        len(distance_matrix),
        num_vehicles,
        starts,
        ends
    )

    routing = pywrapcp.RoutingModel(manager)

    # Distance callback
    def distance_cb(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return distance_matrix[from_node][to_node]

    transit_cb = routing.RegisterTransitCallback(distance_cb)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_cb)

    # Demand callback
    def demand_cb(from_index):
        from_node = manager.IndexToNode(from_index)
        return demands[from_node]

    demand_cb_idx = routing.RegisterUnaryTransitCallback(demand_cb)

    routing.AddDimensionWithVehicleCapacity(
        demand_cb_idx,
        0,          # slack
        capacities,
        True,       # start cumul at zero
        "Capacity"
    )

    search_params = pywrapcp.DefaultRoutingSearchParameters()
    search_params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC

    solution = routing.SolveWithParameters(search_params)
    return manager, routing, solution


def extract_routes(manager, routing, solution, num_vans):
    routes = {}

    for v in range(num_vans):
        index = routing.Start(v)
        route = []

        while not routing.IsEnd(index):
            node = manager.IndexToNode(index)
            route.append(node)
            index = solution.Value(routing.NextVar(index))

        routes[v] = route

    return routes