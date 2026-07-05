from pathlib import Path

from pipeline.io_utils import read_json, write_json


def parse_route_for_app(route_id: str) -> tuple[str, str] | None:
    # Convert direction-coded model route IDs into the route grouping used by the app UI.
    if len(route_id) < 6:
        return None

    direction = route_id[-1]
    route_key = route_id[:5]
    if route_key.endswith("0"):
        route_key = route_key[:4]

    if direction == "1":
        return route_key, "去程"
    if direction == "2":
        return route_key, "返程"
    return None


def create_target_routes_app(
    target_routes_path: Path,
    output_path: Path,
    unparsed_report_path: Path,
) -> dict[str, dict[str, str]]:
    # Group directional routes so Streamlit can show one route with separate directions.
    target_routes: list[str] = read_json(target_routes_path)

    route_groups: dict[str, dict[str, str]] = {}
    unparsed: list[str] = []
    for route_id in target_routes:
        parsed = parse_route_for_app(route_id)
        if parsed is None:
            unparsed.append(route_id)
            continue
        route_key, direction = parsed
        route_groups.setdefault(route_key, {})[direction] = route_id

    sorted_groups = {key: route_groups[key] for key in sorted(route_groups)}
    write_json(output_path, sorted_groups)
    write_json(unparsed_report_path, unparsed)
    return sorted_groups
