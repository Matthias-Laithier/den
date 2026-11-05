from den import tasks
from den.manifest.models import Task


def test_states_checks_every_task_and_keys_them_by_name():
    checked = [
        Task("done", "", check="true", run="x", manual=None),
        Task("pending", "", check="false", run="x", manual=None),
        Task("manual", "", check=None, run=None, manual="do it by hand"),
    ]

    assert tasks.states(checked) == {"done": "done", "pending": "pending", "manual": "manual"}
