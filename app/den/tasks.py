from den.manifest.models import Task
from den.services.shell import succeeds


def state(task: Task) -> str:
    if task.manual:
        return "manual"
    if not task.check:
        return "on demand"
    return "done" if succeeds(task.check) else "pending"
