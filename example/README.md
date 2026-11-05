# Example files repository

A small den files repository with one example of everything den manages. Copy it to start your own:

```sh
cp -r ~/repos/den/example ~/repos/den-files
cd ~/repos/den-files && git init && git add -A && git commit -m "feat: start my den files"
```

Then create a private GitHub repository for it, push, run `den`, and select `~/repos/den-files`.

| Path | What it holds |
|---|---|
| `manifest/packages.toml` | Packages per OS: `brew`, `cask`, `pacman`, `aur`, `apt`, `uv_tool`, `npm`, `script` |
| `manifest/tasks.toml` | Setup tasks with a `check` and a `run`, or `manual` steps |
| `manifest/links.toml` | Restricts `home/` packages to an OS, a profile, or a `when` command |
| `manifest/agents.toml` | Agent CLIs whose skills folder and instructions file den links |
| `manifest/agent-settings.toml` | Keys den merges into each agent's config files |
| `manifest/mcp.toml` | MCP servers written into every agent |
| `home/` | Stow-style packages mirroring `$HOME`, linked by den |
| `skills/` | Skills shared by every agent |
| `instructions/AGENTS.md` | The global instructions file of every agent |
| `secrets/names.txt` | Names of the secrets den encrypts into `secrets/secrets.age` |
| `scripts/` | Scripts that tasks call through `$DEN_ROOT` |

Any entry takes `os = ["macos", "arch", "debian"]`, `profiles = ["work"]` (toggled with `w` on the Overview tab), or `when = "<command>"` to apply only where it fits.
