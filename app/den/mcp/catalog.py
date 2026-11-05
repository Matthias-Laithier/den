import re
from dataclasses import dataclass
from pathlib import Path

import tomlkit

from den.machine.files import read_bytes_if_exists, replace_if_unchanged
from den.machine.paths import manifest_dir
from den.manifest.models import Agent
from den.mcp import targets
from den.mcp.models import McpServer
from den.mcp.targets import McpTarget

ENVIRONMENT_VARIABLE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class InvalidServer(Exception):
    pass


def servers_file() -> Path:
    return manifest_dir() / "mcp.toml"


@dataclass(frozen=True)
class AgentServers:
    agent: str
    states: dict[str, str]
    extras: tuple[McpServer, ...]


def _server(name: str, entry: dict) -> McpServer:
    url, command = entry.get("url"), entry.get("command")
    if bool(url) == bool(command):
        raise InvalidServer(f"{name} needs exactly one of url or command")
    if not isinstance(entry.get("args", []), list):
        raise InvalidServer(f"{name}: args must be a list")
    bearer = entry.get("bearer_token_env")
    if bearer is not None and not (url and ENVIRONMENT_VARIABLE.match(bearer)):
        raise InvalidServer(f"{name}: bearer_token_env must name an environment variable on a url server")
    return McpServer(name, url=url, command=command, args=tuple(entry.get("args", [])), bearer_token_env=bearer)


def load_servers() -> list[McpServer]:
    raw = read_bytes_if_exists(servers_file())
    document = tomlkit.parse(raw.decode()) if raw else {}
    return [_server(name, dict(entry)) for name, entry in document.items()]


def _entry(server: McpServer) -> dict:
    if server.url and server.bearer_token_env:
        return {"url": server.url, "bearer_token_env": server.bearer_token_env}
    if server.url:
        return {"url": server.url}
    return {"command": server.command, "args": list(server.args)}


def save_servers(servers: list[McpServer]) -> None:
    path = servers_file()
    raw = read_bytes_if_exists(path)
    document = tomlkit.document()
    for server in sorted(servers, key=lambda server: server.name):
        document[server.name] = _entry(server)
    replace_if_unchanged(path, tomlkit.dumps(document), raw)


def managed_agents(agents: list[Agent]) -> list[str]:
    return [agent.name for agent in agents if agent.name in targets.TARGETS and agent.home_path.exists()]


def _state(server: McpServer, entries: dict[str, dict], target: McpTarget) -> str:
    if server.name not in entries:
        return "missing"
    entry = entries[server.name]
    return "synced" if all(entry.get(key) == value for key, value in target.render(server).items()) else "different"


def compare(agent: str, servers: list[McpServer]) -> AgentServers:
    target = targets.get(agent)
    entries = target.config_file().read()
    names = {server.name for server in servers}
    states = {server.name: _state(server, entries, target) for server in servers}
    extras = tuple(target.parse(name, entry) for name, entry in entries.items() if name not in names)
    return AgentServers(agent, states, extras)


def _existing_entry(server: McpServer, entries: dict[str, dict], target: McpTarget) -> dict | None:
    parsed = {name: target.parse(name, entry) for name, entry in entries.items()}
    by_name = parsed.get(server.name)
    if by_name is not None and by_name.identity == server.identity:
        return entries[server.name]
    matches = [entries[name] for name, existing in parsed.items() if existing.identity == server.identity]
    if matches:
        return matches[0]
    if by_name is not None and server.command and by_name.command == server.command:
        return entries[server.name]
    return None


def sync(agent: str, servers: list[McpServer]) -> None:
    target = targets.get(agent)
    config = target.config_file()
    entries = config.read()
    synced = {}
    for server in servers:
        existing = _existing_entry(server, entries, target) or target.defaults(server)
        synced[server.name] = {**existing, **target.render(server)}
    config.write(synced)


def import_servers(chosen: list[McpServer]) -> None:
    servers = {server.name: server for server in load_servers()}
    servers.update({server.name: server for server in chosen})
    save_servers(list(servers.values()))


def remove_server(name: str) -> None:
    save_servers([server for server in load_servers() if server.name != name])
