from src.maps import MapsClient
from src.sheets import SheetsClient
from src.optimizer import solve_cvrp, extract_routes
from src.agent import RouteAgent

def main():
    # 1) Read from Google Sheets
    sheets = SheetsClient()
    stops, vans = sheets.read_stops_and_vans()

    # 2) Extract addresses + students (demands)
    addresses = []
    students = []
    stop_ids = []

    for row in stops:
        addr = row.get("Address")
        if not addr:
            continue  # skip empty rows

        addresses.append(addr)
        students.append(int(row.get("Students") or 0))
        stop_ids.append(row.get("ID"))

    # 3) Extract van capacities + start indices
    van_ids = []
    start_indices = []
    capacities = []

    for row in vans:
        van_ids.append(row.get("ID"))
        start_indices.append(int(row.get("Start Index")))
        capacities.append(int(row.get("Capacity")))

    print(f"Loaded {len(addresses)} stops and {len(capacities)} vans.")
    print("Van start indices:", start_indices)
    print("Van capacities:", capacities)

    # 4) Get distance matrix from Google Maps
    maps = MapsClient(cache_dir="data/cache")

    # Agent chooses optimization metric (toggle supported)
    agent = RouteAgent()

    # Toggle options:
    #   - set prefer="distance" or prefer="duration" to force it
    #   - set prefer=None to let agent decide
    prefer = None  # change to "duration" if you want to force minutes-based routing

    decision = agent.choose_metric(
        students=students,
        capacities=capacities,
        prefer=prefer,
        traffic_sensitive=False,
        time_windows=False,
    )

    optimize_for = decision.optimize_for
    print(f"Agent decision: optimize_for={optimize_for} | reason: {decision.reason}")
    matrix = maps.get_distance_matrix(addresses, optimize_for=optimize_for, mode="driving")

    # 5) Quick sanity checks + sample output
    #check 1 : Matrix Shape
    n = len(addresses)
    if len(matrix) != n or any(len(r) != n for r in matrix):
        raise RuntimeError("Distance matrix shape mismatch")
    #check 2 : Diagonal must be zero
    for i in range(n):
        if matrix[i][i] != 0:
            raise RuntimeError(f"Matrix diagonal not zero at index {i}: {matrix[i][i]}")
    # check 3 : Start indices valid
    for idx in start_indices:
        if idx < 0 or idx >= n:
            raise ValueError(f"Invalid Start Index {idx}. Must be between 0 and {n - 1}.")

    print(f"Matrix size: {n}x{n} (optimize_for={optimize_for})")
    print("First row:", matrix[0])

    # 6) Solve with OR-Tools (closed routes: ends == starts)
    num_vans = len(capacities)

    manager, routing, solution = solve_cvrp(
        distance_matrix=matrix,
        demands=students,
        capacities=capacities,
        starts=start_indices
    )

    # If no solution, try the other metric once (agent-style fallback)
    if solution is None:
        fallback = "duration" if optimize_for == "distance" else "distance"
        print(f"No solution with {optimize_for}. Retrying with {fallback}...")

        optimize_for = fallback
        matrix = maps.get_distance_matrix(addresses, optimize_for=optimize_for, mode="driving")

        manager, routing, solution = solve_cvrp(
            distance_matrix=matrix,
            demands=students,
            capacities=capacities,
            starts=start_indices
        )

    if solution is None:
        raise RuntimeError("No solution found by OR-Tools. Check demands/capacities/starts.")

    routes = extract_routes(manager, routing, solution, num_vans)

    # 7) Print routes (indices + addresses + load)
    per_van_cost = {}
    total_raw_cost = 0
    for v, route in routes.items():
        van_label = van_ids[v] if v < len(van_ids) else f"Van {v}"

        # Create closed-loop version for display only
        loop_route = route + [route[0]]
        raw_cost = 0
        for a, b in zip(loop_route, loop_route[1:]):
            raw_cost += matrix[a][b]
        total_raw_cost += raw_cost

        # Convert to miles/minutes units
        if optimize_for == "distance":
            route_cost = raw_cost / 1609.34  # meters → miles
            unit = "miles"
        else:
            route_cost = raw_cost / 60  # seconds → minutes
            unit = "minutes"

        per_van_cost[v] = route_cost

        print(f"{van_label} route cost: {route_cost:.2f} {unit}")

        print(f"\n{van_label} route (indices): {loop_route}")

        print(f"{van_label} route (addresses):")
        for idx in loop_route:
            print(f"  - [{idx}] {addresses[idx]}")

        # Correct load calculation (no double counting)
        load = sum(students[idx] for idx in route)
        print(f"{van_label} total students picked up: {load} / capacity {capacities[v]}")

    if optimize_for == "distance":
        total_cost = total_raw_cost / 1609.34
        cost_unit = "miles"
    else:
        total_cost = total_raw_cost / 60
        cost_unit = "minutes"

    print(f"\nTOTAL cost: {total_cost:.2f} {unit}")
    print(f"Average route time: {total_cost / len(capacities):.2f} minutes")

    sheets.write_routes(
        routes_ws_name="Routes",
        routes=routes,  # keep routes WITHOUT duplicated loop end
        van_ids=van_ids,
        stop_ids=stop_ids,
        addresses=addresses,
        students=students,
        per_van_cost=per_van_cost,
        total_cost=total_cost,
        cost_unit=cost_unit,
    )
    print("Wrote routes to Google Sheet tab: Routes")

    # Return data for next step (optimizer / output / formatting)
    return {
        "addresses": addresses,
        "students": students,
        "stop_ids": stop_ids,
        "van_ids": van_ids,
        "start_indices": start_indices,
        "capacities": capacities,
        "matrix": matrix,
        "optimize_for": optimize_for,
        "routes": routes,
    }

if __name__ == "__main__":
    main()