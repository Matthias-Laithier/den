import json
import tomllib

from den.mcp import catalog
from den.mcp.models import McpServer

NOTION = McpServer("notion", url="https://mcp.notion.com/mcp")
PLAYWRIGHT = McpServer("playwright", command="npx", args=("@playwright/mcp@latest",))


def write_claude_config(home, servers):
    (home / ".claude.json").write_text(json.dumps({"numStartups": 3, "mcpServers": servers}))


def test_sync_folds_duplicates_and_keeps_agent_only_fields(fake_home):
    write_claude_config(
        fake_home,
        {
            "notion-oauth": {"type": "http", "url": "https://mcp.notion.com/mcp/", "headers": {"X-Agent": "kept"}},
            "old": {"type": "http", "url": "https://old.example.com"},
        },
    )
    catalog.sync("claude", [NOTION, PLAYWRIGHT])
    document = json.loads((fake_home / ".claude.json").read_text())
    assert document["numStartups"] == 3
    assert document["mcpServers"] == {
        "notion": {"type": "http", "url": "https://mcp.notion.com/mcp", "headers": {"X-Agent": "kept"}},
        "playwright": {"type": "stdio", "command": "npx", "args": ["@playwright/mcp@latest"]},
    }


def test_sync_keeps_agent_only_fields_when_a_command_server_changes_its_arguments(fake_home):
    write_claude_config(
        fake_home,
        {"playwright": {"type": "stdio", "command": "npx", "args": ["@playwright/mcp@0.1"], "env": {"TOKEN": "kept"}}},
    )
    catalog.sync("claude", [PLAYWRIGHT])
    document = json.loads((fake_home / ".claude.json").read_text())
    assert document["mcpServers"]["playwright"] == {
        "type": "stdio",
        "command": "npx",
        "args": ["@playwright/mcp@latest"],
        "env": {"TOKEN": "kept"},
    }


def test_sync_drops_agent_only_fields_when_a_url_server_moves(fake_home):
    write_claude_config(
        fake_home,
        {"notion": {"type": "http", "url": "https://old.example.com", "headers": {"Authorization": "Bearer secret"}}},
    )
    catalog.sync("claude", [NOTION])
    document = json.loads((fake_home / ".claude.json").read_text())
    assert document["mcpServers"]["notion"] == {"type": "http", "url": "https://mcp.notion.com/mcp"}


def test_compare_reports_missing_different_and_agent_only_servers(fake_home):
    write_claude_config(
        fake_home,
        {
            "notion": {"type": "http", "url": "https://other.example.com"},
            "extra": {"type": "http", "url": "https://x.example.com"},
        },
    )
    comparison = catalog.compare("claude", [NOTION, PLAYWRIGHT])
    assert comparison.states == {"notion": "different", "playwright": "missing"}
    assert [server.name for server in comparison.extras] == ["extra"]


def test_toml_agents_keep_their_other_settings(fake_home):
    (fake_home / ".codex").mkdir()
    (fake_home / ".codex" / "config.toml").write_text(
        'model = "gpt"\n\n[mcp_servers.stale]\nurl = "https://stale.example.com"\n'
    )
    (fake_home / ".vibe").mkdir()
    (fake_home / ".vibe" / "config.toml").write_text('theme = "dark"\n')
    catalog.sync("codex", [NOTION])
    catalog.sync("vibe", [NOTION])
    codex = tomllib.loads((fake_home / ".codex" / "config.toml").read_text())
    vibe = tomllib.loads((fake_home / ".vibe" / "config.toml").read_text())
    assert codex == {"model": "gpt", "mcp_servers": {"notion": {"url": "https://mcp.notion.com/mcp"}}}
    assert vibe == {
        "theme": "dark",
        "mcp_servers": [
            {
                "name": "notion",
                "transport": "streamable-http",
                "url": "https://mcp.notion.com/mcp",
                "auth": {"type": "oauth", "scopes": []},
            }
        ],
    }


def test_bearer_servers_reference_the_variable_in_each_agent_format(fake_home):
    slack = McpServer("slack", url="https://gateway.example.com/slack", bearer_token_env="GATEWAY_KEY")
    write_claude_config(
        fake_home, {"slack": {"type": "http", "url": slack.url, "headers": {"Authorization": "Bearer old"}}}
    )
    (fake_home / ".vibe").mkdir()
    catalog.sync("claude", [slack])
    catalog.sync("vibe", [slack])
    claude = json.loads((fake_home / ".claude.json").read_text())["mcpServers"]["slack"]
    vibe = tomllib.loads((fake_home / ".vibe" / "config.toml").read_text())["mcp_servers"][0]
    assert claude["headers"] == {"Authorization": "Bearer ${GATEWAY_KEY}"}
    assert vibe["auth"] == {"type": "static", "api_key_env": "GATEWAY_KEY"}
    assert catalog.compare("claude", [slack]).states == {"slack": "synced"}
