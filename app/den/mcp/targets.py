from collections.abc import Callable
from dataclasses import dataclass

from den.config_files import DocumentFormat, JsonFormat, TomlFormat
from den.machine.paths import home
from den.mcp.files import ConfigFile, KeyedSection, NamedTableArray, Section
from den.mcp.models import McpServer

VIBE_OAUTH = {"auth": {"type": "oauth", "scopes": []}}


class UnknownMcpTarget(Exception):
    pass


@dataclass(frozen=True)
class McpTarget:
    relative_path: str
    document_format: DocumentFormat
    section: Section
    url_entry: Callable[[str], dict]
    command_entry: Callable[[str, list[str]], dict]
    bearer_entry: Callable[[str], dict] = lambda variable: {}
    url_key: str = "url"
    new_url_defaults: dict | None = None

    def config_file(self) -> ConfigFile:
        return ConfigFile(home() / self.relative_path, self.document_format, self.section)

    def render(self, server: McpServer) -> dict:
        if not server.url:
            return self.command_entry(server.command or "", list(server.args))
        if server.bearer_token_env:
            return {**self.url_entry(server.url), **self.bearer_entry(server.bearer_token_env)}
        return self.url_entry(server.url)

    def defaults(self, server: McpServer) -> dict:
        return dict(self.new_url_defaults or {}) if server.url else {}

    def parse(self, name: str, entry: dict) -> McpServer:
        url = entry.get(self.url_key) or entry.get("url")
        if url:
            return McpServer(name, url=url)
        command = entry.get("command", "")
        if isinstance(command, list):
            return McpServer(name, command=command[0], args=tuple(command[1:]))
        return McpServer(name, command=command, args=tuple(entry.get("args", [])))


def _url(url: str) -> dict:
    return {"url": url}


def _command(command: str, args: list[str]) -> dict:
    return {"command": command, "args": args}


def _authorization(value: str) -> dict:
    return {"headers": {"Authorization": value}}


TARGETS: dict[str, McpTarget] = {
    "claude": McpTarget(
        ".claude.json",
        JsonFormat(),
        KeyedSection("mcpServers"),
        lambda url: {"type": "http", "url": url},
        lambda command, args: {"type": "stdio", "command": command, "args": args},
        lambda variable: _authorization(f"Bearer ${{{variable}}}"),
    ),
    "cursor": McpTarget(
        ".cursor/mcp.json",
        JsonFormat(),
        KeyedSection("mcpServers"),
        _url,
        _command,
        lambda variable: _authorization(f"Bearer ${{env:{variable}}}"),
    ),
    "codex": McpTarget(
        ".codex/config.toml",
        TomlFormat(),
        KeyedSection("mcp_servers"),
        _url,
        _command,
        lambda variable: {"bearer_token_env_var": variable},
    ),
    "gemini": McpTarget(
        ".gemini/settings.json",
        JsonFormat(),
        KeyedSection("mcpServers"),
        lambda url: {"httpUrl": url},
        _command,
        lambda variable: _authorization(f"Bearer ${{{variable}}}"),
        url_key="httpUrl",
    ),
    "opencode": McpTarget(
        ".config/opencode/opencode.jsonc",
        JsonFormat(),
        KeyedSection("mcp"),
        lambda url: {"type": "remote", "url": url, "enabled": True},
        lambda command, args: {"type": "local", "command": [command, *args], "enabled": True},
        lambda variable: _authorization(f"Bearer {{env:{variable}}}"),
    ),
    "vibe": McpTarget(
        ".vibe/config.toml",
        TomlFormat(),
        NamedTableArray("mcp_servers"),
        lambda url: {"transport": "streamable-http", "url": url},
        lambda command, args: {"transport": "stdio", "command": command, "args": args},
        lambda variable: {"auth": {"type": "static", "api_key_env": variable}},
        new_url_defaults=VIBE_OAUTH,
    ),
}


def get(agent: str) -> McpTarget:
    if agent not in TARGETS:
        raise UnknownMcpTarget(agent)
    return TARGETS[agent]
