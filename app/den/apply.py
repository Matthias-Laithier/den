from den import agents, links, packages, tasks
from den.agents import AgentStatus
from den.links import Link
from den.manifest.models import Manifest, Package, Task
from den.services.shell import run_steps


def pending_links(manifest: Manifest) -> list[Link]:
    return [link for link in links.plan_all(manifest.link_packages) if link.state != "linked"]


def linkable_agents(manifest: Manifest) -> list[AgentStatus]:
    statuses = [agents.status(agent) for agent in manifest.agents]
    return [status for status in statuses if status.needs_setup and not status.own_skills]


def missing_packages(manifest: Manifest) -> list[Package]:
    installed = packages.statuses(manifest.packages)
    return [package for package in manifest.packages if not installed[package.name]]


def pending_tasks(manifest: Manifest) -> list[Task]:
    return [task for task in manifest.tasks if task.run and tasks.state(task) == "pending"]


def apply_everything(manifest: Manifest) -> list[str]:
    to_link = pending_links(manifest)
    backup = links.apply_all(to_link)
    print(f"Linked {len(to_link)} configs" + (f", replaced files saved in {backup}" if backup else ""))
    for status in linkable_agents(manifest):
        agents.set_up(status.agent)
        print(f"Set up the skills, instructions and settings of {status.agent.name}")
    steps = packages.install_steps(missing_packages(manifest))
    return run_steps(steps + [task.run for task in pending_tasks(manifest) if task.run])
