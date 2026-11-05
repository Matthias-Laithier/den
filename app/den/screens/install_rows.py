from rich.text import Text

from den.manifest.models import Package

TASK_STYLES = {"done": "green", "pending": "bold yellow", "manual": "cyan", "on demand": "dim"}
TASK_ORDER = ("pending", "manual", "on demand", "done")


def package_rank(package: Package, installed: dict[str, bool], updates: dict[str, dict[str, str]]) -> tuple:
    if not installed.get(package.name):
        return (0, package.group, package.name)
    return (1 if package.name in updates else 2, package.group, package.name)


def package_state(name: str, installed: dict[str, bool], updates: dict[str, dict[str, str]]) -> Text:
    if not installed.get(name):
        return Text("✗ missing", style="bold red")
    if name in updates:
        return Text("↑ update", style="bold yellow")
    return Text("✓ installed", style="green")


def update_label(name: str, updates: dict[str, dict[str, str]]) -> str:
    return ", ".join(f"{target} → {version}" for target, version in updates.get(name, {}).items())


def task_rank(state: str) -> int:
    return TASK_ORDER.index(state) if state in TASK_ORDER else len(TASK_ORDER)


def task_state(state: str) -> Text:
    return Text(state, style=TASK_STYLES.get(state, ""))


def summary(missing: int, outdated: int | None, pending_tasks: int) -> Text:
    parts = [
        (f"✗ {missing} to install", "bold red") if missing else ("✓ every package installed", "bold green"),
        "   ",
    ]
    if outdated is None:
        parts.append(("updates not checked, press u", "dim"))
    else:
        parts.append(
            (f"↑ {outdated} to update", "bold yellow") if outdated else ("✓ everything up to date", "bold green")
        )
    parts += [
        "   ",
        (f"● {pending_tasks} setup tasks pending", "bold yellow") if pending_tasks else ("✓ setup done", "green"),
    ]
    return Text.assemble(*parts)
