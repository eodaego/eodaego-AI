from collections import defaultdict
from dataclasses import dataclass

from app.domains.recommendation.route_optimizer import (
    Coordinate,
    haversine_distance_m,
    optimize_route,
    route_length_m,
)

WALKING_METERS_PER_MINUTE = 4000 / 60
STOP_DWELL_MINUTES = 15
DEFAULT_STAY_MINUTES = 120
MIN_WAYPOINTS = 1
MAX_WAYPOINTS = 10
MIN_DURATION_MINUTES = 1
MAX_DURATION_MINUTES = 600

_BALANCED_TITLE = "관심 분야를 고루 담은 코스"
_BALANCED_TAG_LABELS = ("균형",)
_SHORTEST_TITLE = "이동거리가 짧은 코스"
_SHORTEST_TAG_LABELS = ("최단 이동",)
_FOCUSED_TITLE = "관심도가 높은 시설 중심 코스"
_FOCUSED_TAG_LABELS = ("관심 집중",)


@dataclass(frozen=True)
class FallbackCandidate:
    facility_id: int
    category: str
    latitude: float
    longitude: float
    tags: frozenset[str]

    @property
    def interest(self) -> int:
        return len(self.tags)


@dataclass(frozen=True)
class FallbackCourse:
    title: str
    reason: str
    tag_labels: tuple[str, ...]
    estimated_duration_minutes: int
    ordered_facility_ids: tuple[int, ...]


def _group_keys(candidates: list[FallbackCandidate]) -> dict[int, str]:
    tag_keys = {c.facility_id: min(c.tags) if c.tags else c.category for c in candidates}
    # 태그 기준 그룹이 1개뿐이면 라운드로빈이 의미가 없어 카테고리로 대체한다.
    if len(set(tag_keys.values())) < 2:
        return {c.facility_id: c.category for c in candidates}
    return tag_keys


def _order_balanced(
    candidates: list[FallbackCandidate], entrance: Coordinate
) -> list[FallbackCandidate]:
    group_keys = _group_keys(candidates)
    groups: dict[str, list[FallbackCandidate]] = defaultdict(list)
    for candidate in _order_by_distance(candidates, entrance):
        groups[group_keys[candidate.facility_id]].append(candidate)
    queues = [groups[key] for key in sorted(groups)]
    interleaved: list[FallbackCandidate] = []
    for round_index in range(max(len(queue) for queue in queues)):
        interleaved.extend(queue[round_index] for queue in queues if round_index < len(queue))
    return interleaved


def _order_by_distance(
    candidates: list[FallbackCandidate], entrance: Coordinate
) -> list[FallbackCandidate]:
    return sorted(
        candidates,
        key=lambda c: (
            haversine_distance_m(entrance[0], entrance[1], c.latitude, c.longitude),
            c.facility_id,
        ),
    )


def _order_by_interest(
    candidates: list[FallbackCandidate], entrance: Coordinate
) -> list[FallbackCandidate]:
    return sorted(
        candidates,
        key=lambda c: (
            -c.interest,
            haversine_distance_m(entrance[0], entrance[1], c.latitude, c.longitude),
            c.facility_id,
        ),
    )


def _route_for(
    entrance: Coordinate, exit_point: Coordinate, selected: list[FallbackCandidate]
) -> tuple[list[int], int]:
    ordered_ids = optimize_route(
        start=entrance,
        end=exit_point,
        waypoints=[(c.facility_id, c.latitude, c.longitude) for c in selected],
    )
    coordinates_by_id = {c.facility_id: (c.facility_id, c.latitude, c.longitude) for c in selected}
    ordered = [coordinates_by_id[facility_id] for facility_id in ordered_ids]
    distance_m = route_length_m(entrance, exit_point, ordered)
    minutes = round(distance_m / WALKING_METERS_PER_MINUTE + len(ordered) * STOP_DWELL_MINUTES)
    return ordered_ids, minutes


def _fill_course(
    prioritized: list[FallbackCandidate],
    entrance: Coordinate,
    exit_point: Coordinate,
    stay_minutes: int,
) -> tuple[list[int], int]:
    selected: list[FallbackCandidate] = []
    best_ids: list[int] = []
    best_minutes = 0
    for candidate in prioritized:
        if len(selected) >= MAX_WAYPOINTS:
            break
        trial = [*selected, candidate]
        ordered_ids, minutes = _route_for(entrance, exit_point, trial)
        # 첫 시설은 체류시간을 넘더라도 최소 방문 수(1)를 보장하기 위해 무조건 포함한다.
        if len(selected) >= MIN_WAYPOINTS and minutes > stay_minutes:
            break
        selected = trial
        best_ids, best_minutes = ordered_ids, minutes
    clamped = max(MIN_DURATION_MINUTES, min(MAX_DURATION_MINUTES, best_minutes))
    return best_ids, clamped


def _build_course(
    title: str,
    tag_labels: tuple[str, ...],
    strategy_description: str,
    prioritized: list[FallbackCandidate],
    entrance: Coordinate,
    exit_point: Coordinate,
    stay_minutes: int,
) -> FallbackCourse:
    ordered_ids, minutes = _fill_course(prioritized, entrance, exit_point, stay_minutes)
    reason = (
        f"{strategy_description} 총 {len(ordered_ids)}곳을 방문하며 "
        f"예상 소요시간은 약 {minutes}분입니다."
    )
    return FallbackCourse(
        title=title,
        reason=reason,
        tag_labels=tag_labels,
        estimated_duration_minutes=minutes,
        ordered_facility_ids=tuple(ordered_ids),
    )


def build_fallback_courses(
    entrance: Coordinate,
    exit_point: Coordinate,
    candidates: list[FallbackCandidate],
    stay_duration_minutes: int | None,
) -> list[FallbackCourse]:
    """LLM을 쓸 수 없을 때 A(균형)·B(최단)·C(집중) 3개 코스를 결정적으로 생성한다.
    candidates는 비어 있지 않아야 한다.
    """
    stay_minutes = stay_duration_minutes or DEFAULT_STAY_MINUTES
    return [
        _build_course(
            _BALANCED_TITLE,
            _BALANCED_TAG_LABELS,
            "선택한 관심 분야를 번갈아 방문하도록 구성했습니다.",
            _order_balanced(candidates, entrance),
            entrance,
            exit_point,
            stay_minutes,
        ),
        _build_course(
            _SHORTEST_TITLE,
            _SHORTEST_TAG_LABELS,
            "입구에서 가까운 시설부터 이동거리를 최소화하도록 구성했습니다.",
            _order_by_distance(candidates, entrance),
            entrance,
            exit_point,
            stay_minutes,
        ),
        _build_course(
            _FOCUSED_TITLE,
            _FOCUSED_TAG_LABELS,
            "선택한 관심 분야와 많이 일치하는 시설을 우선 방문하도록 구성했습니다.",
            _order_by_interest(candidates, entrance),
            entrance,
            exit_point,
            stay_minutes,
        ),
    ]
