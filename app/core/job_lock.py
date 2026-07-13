import threading
from types import TracebackType


class JobAlreadyRunningError(Exception):
    """같은 job_id가 이미 실행 중일 때 raise된다."""


_registry_lock = threading.Lock()
_job_locks: dict[str, threading.Lock] = {}


def _get_lock(job_id: str) -> threading.Lock:
    with _registry_lock:
        if job_id not in _job_locks:
            _job_locks[job_id] = threading.Lock()
        return _job_locks[job_id]


class JobRunGuard:
    """job_id별 동시 실행을 막는 컨텍스트 매니저.

    스케줄러(주기 실행)와 수동 트리거 API(직접 호출)가 동일한 job 함수를 서로 다른 경로로
    호출하므로, 이 가드를 job 함수 내부(두 경로의 공통 지점)에 둬야 어느 쪽으로 들어와도
    중복 실행이 방지된다. 프로세스 내 인메모리 락이라 uvicorn이 단일 프로세스로 뜬다는
    전제(Dockerfile에 --workers 옵션 없음)에서만 유효하다.
    """

    def __init__(self, job_id: str) -> None:
        self._job_id = job_id
        self._lock = _get_lock(job_id)

    def __enter__(self) -> None:
        if not self._lock.acquire(blocking=False):
            raise JobAlreadyRunningError(f"job already running: {self._job_id}")

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self._lock.release()
