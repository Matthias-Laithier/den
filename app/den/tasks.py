from concurrent.futures import ThreadPoolExecutor

from den.manifest.models import Task
from den.services.shell import succeeds


def state(task: Task) -> str:
    if task.manual:
        return "manual"
    if not task.check:
        return "on demand"
    return "done" if succeeds(task.check) else "pending"


def states(tasks: list[Task]) -> dict[str, str]:
    with ThreadPoolExecutor() as pool:
        return dict(zip((task.name for task in tasks), pool.map(state, tasks), strict=True))
