# den

den is a terminal UI that applies your machine setup from a files repository. It manages packages, setup tasks, config links, agent skills and instructions, MCP servers, and encrypted secrets on macOS, Arch Linux, and Debian.

The tool and your files live in separate repositories. This repository holds the TUI, launcher, and bootstrap. Your files repository holds the configuration den applies.

## Fresh machine

```sh
curl -fsSL https://raw.githubusercontent.com/Matthias-Laithier/den/master/bootstrap.sh | sh
```

`bootstrap.sh` installs git, `gh`, and `uv`. It clones the den tool repository to `~/repos/den` (or `$DEN_HOME`) over HTTPS, with no GitHub login. It then asks for the GitHub repository holding your den files. If you give one, it logs in to GitHub when needed and clones the repository to `~/repos/<name>`. It opens den at the end.

On first launch, den asks for the folder holding your files repository and stores it as `files = "<path>"` in `~/.config/den/config.toml`. You can skip the bootstrap clone and pick an existing folder.

## Daily use

```sh
den
```

The launcher links itself to `~/.local/bin/den`, installs `uv` when needed, and runs the TUI from `app/`. It pulls the tool repository and the files repository on launch.

The Changes tab commits and pushes the files repository. Use it for every change den makes.

| Tab | What it does |
|---|---|
| Overview | State of the machine. `ctrl+a` applies everything |
| Install | Packages and setup tasks from `manifest/`, installed with the OS package manager |
| Configs | Symlinks from `$HOME` into `home/`, with backup or adoption of files already on disk |
| Skills | Skills shared by every agent. Import from a folder, a `SKILL.md`, or a GitHub repository |
| Instructions | Preview and edit `instructions/AGENTS.md`, and see which agents link it |
| Agents | Links each agent CLI's skills folder to `skills/` and its instructions file to `instructions/AGENTS.md`. Merges settings from `manifest/agent-settings.toml` into its config files. Agents that manage their own skills keep their folder |
| MCP | MCP servers from `manifest/mcp.toml`, written into each agent's config. Logins and tokens stay with each agent |
| Secrets | Secrets encrypted in `secrets/secrets.age`, decrypted to `~/.config/den/secrets.zsh` |
| Changes | Diff, commit, pull, and push the files repository |

## Files repository

The files folder is a git repository with this layout:

```text
home/
manifest/
  packages.toml
  tasks.toml
  links.toml
  agents.toml
  agent-settings.toml
  mcp.toml
skills/
instructions/
  AGENTS.md
secrets/
scripts/
```

`home/` holds stow-style packages that mirror `$HOME`. `manifest/` holds packages, setup tasks, config links, agent CLIs, agent settings, and MCP servers. `skills/` holds the skills shared by agents. `instructions/AGENTS.md` is the global instructions file. `secrets/` holds the encrypted secrets and their names. `scripts/` holds setup task scripts reached through `$DEN_ROOT`.

## Moving from the single-repo den

Move the old checkout, clone the new tool repository, and start den:

```sh
mv ~/repos/den ~/repos/den-files
git clone https://github.com/Matthias-Laithier/den.git ~/repos/den
~/repos/den/den
```

Pick `~/repos/den-files` when den asks for the files folder. Press `ctrl+a` on Overview to relink stale links.

## Tool layout

- `app/`: the TUI (Python, Textual), its tests and styles
- `bootstrap.sh`: installs prerequisites, clones the repositories, and opens den
- `den`: the launcher
- `.githooks/`: the pre-commit hook that scans commits with gitleaks

## Development

- `make dev` runs den
- `make check` checks formatting, lint, types (ty), and runs the tests
- `make check-all` also scans the git history for leaked secrets

## Decisions

- **The tool and files live in separate repositories.** The tool repository holds the code that applies a setup and the bootstrap. The files repository holds the setup itself. den stores the files folder in `~/.config/den/config.toml`.
- **Links are not made with GNU Stow.** Stow refuses to replace links it does not own, so it cannot move links from another dotfiles checkout, and it reports conflicts by aborting instead of per file. den keeps Stow's folder layout and folding, and adds per-link states, backups and adoption.
- **Secrets are encrypted with age through `pyrage`**, so no `age` binary is needed to unlock them. The decrypted file lives outside the files repository with `600` permissions.

## License

License: MIT. See [LICENSE](LICENSE).
