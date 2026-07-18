import math

Coordinate = tuple[float, float]

_EARTH_RADIUS_M = 6371000.0


def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """두 좌표 간 직선거리(미터)."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return _EARTH_RADIUS_M * c


def _route_length(
    start: Coordinate, end: Coordinate, order: list[tuple[int, float, float]]
) -> float:
    points: list[Coordinate] = [start, *[(lat, lon) for _, lat, lon in order], end]
    return sum(haversine_distance_m(*points[i], *points[i + 1]) for i in range(len(points) - 1))


def _two_opt(
    start: Coordinate, end: Coordinate, order: list[tuple[int, float, float]]
) -> list[tuple[int, float, float]]:
    if len(order) < 2:
        return order
    best = order
    best_length = _route_length(start, end, best)
    improved = True
    while improved:
        improved = False
        for i in range(len(best) - 1):
            for j in range(i + 1, len(best)):
                candidate = best[:i] + list(reversed(best[i : j + 1])) + best[j + 1 :]
                candidate_length = _route_length(start, end, candidate)
                if candidate_length < best_length:
                    best, best_length = candidate, candidate_length
                    improved = True
    return best


def optimize_route(
    start: Coordinate, end: Coordinate, waypoints: list[tuple[int, float, float]]
) -> list[int]:
    """start에서 출발해 end로 도착하는 구간이 고정된 상태에서, waypoints를 모두 방문하는
    최단 순서의 facility_id 목록을 반환한다(최근접 이웃 초기해 + 2-opt 개선).
    """
    if not waypoints:
        return []

    remaining = list(waypoints)
    order: list[tuple[int, float, float]] = []
    current = start
    while remaining:
        nearest = min(
            remaining, key=lambda w: haversine_distance_m(current[0], current[1], w[1], w[2])
        )
        order.append(nearest)
        remaining.remove(nearest)
        current = (nearest[1], nearest[2])

    order = _two_opt(start, end, order)
    return [facility_id for facility_id, _, _ in order]
