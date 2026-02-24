import os
import json
import hashlib
from dotenv import load_dotenv
import googlemaps

load_dotenv()

class MapsClient:
    def __init__(self, cache_dir="data/cache"):
        api_key = os.getenv("GOOGLE_MAPS_API_KEY")
        if not api_key:
            raise ValueError("Google Maps API key not found in .env (GOOGLE_MAPS_API_KEY)")

        self.client = googlemaps.Client(key=api_key)
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

    def _get_cache_path(self, key_string: str) -> str:
        hashed = hashlib.md5(key_string.encode("utf-8")).hexdigest()
        return os.path.join(self.cache_dir, f"{hashed}.json")

    def get_distance_matrix(self, addresses, optimize_for="distance", mode="driving"):
        """
        Returns a 2D matrix between addresses.

        optimize_for:
          - "distance" -> meters (int)
          - "duration" -> seconds (int)
        mode: "driving" (default), "walking", "bicycling", "transit"
        """
        if not isinstance(addresses, list) or len(addresses) < 2:
            raise ValueError("addresses must be a list with at least two address strings")

        optimize_for = optimize_for.lower().strip()
        if optimize_for not in {"distance", "duration"}:
            raise ValueError("optimize_for must be 'distance' or 'duration'")

        mode = mode.lower().strip()

        # Unambiguous cache key
        cache_key = json.dumps(
            {"addresses": addresses, "optimize_for": optimize_for, "mode": mode},
            sort_keys=True
        )
        cache_path = self._get_cache_path(cache_key)

        # Cache hit
        if os.path.exists(cache_path):
            print("Using cached matrix")
            with open(cache_path, "r") as f:
                matrix = json.load(f)
            # ensure ints (defensive)
            return [[int(x) for x in row] for row in matrix]

        # API call
        response = self.client.distance_matrix(
            origins=addresses,
            destinations=addresses,
            mode=mode,
        )

        if response.get("status") != "OK":
            raise RuntimeError(f"Google Maps API error: {response.get('status')}")

        matrix = []
        for i, row in enumerate(response["rows"]):
            matrix_row = []
            for j, element in enumerate(row["elements"]):
                if element.get("status") != "OK":
                    raise RuntimeError(
                        f"Route error {element.get('status')} from '{addresses[i]}' to '{addresses[j]}'"
                    )

                value = element[optimize_for]["value"]  # meters or seconds
                matrix_row.append(int(value))
            matrix.append(matrix_row)

        with open(cache_path, "w") as f:
            json.dump(matrix, f)

        return matrix