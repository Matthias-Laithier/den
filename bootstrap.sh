#!/bin/sh

set -eu

REPOSITORY="Matthias-Laithier/den"
TARGET="${DEN_HOME:-$HOME/repos/den}"
HOMEBREW_INSTALLER="https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh"
UV_INSTALLER="https://astral.sh/uv/install.sh"

detect_os() {
    if [ "$(uname -s)" = "Darwin" ]; then
        echo macos
        return
    fi
    family="$(. /etc/os-release && echo "$ID ${ID_LIKE:-}")"
    case " $family " in
        *" arch "*) echo arch ;;
        *" debian "*) echo debian ;;
        *) echo "Unsupported system: $family" >&2; exit 1 ;;
    esac
}

install_macos_prerequisites() {
    if ! xcode-select -p >/dev/null 2>&1; then
        xcode-select --install
        echo "Run this script again once the command line tools are installed"
        exit 0
    fi
    if ! command -v brew >/dev/null 2>&1; then
        /bin/bash -c "$(curl -fsSL "$HOMEBREW_INSTALLER")" </dev/tty
    fi
    eval "$(/opt/homebrew/bin/brew shellenv 2>/dev/null || /usr/local/bin/brew shellenv)"
    brew install gh
}

install_prerequisites() {
    case "$(detect_os)" in
        macos) install_macos_prerequisites ;;
        arch) sudo pacman -S --needed --noconfirm git github-cli curl ;;
        debian) sudo apt-get update && sudo apt-get install -y git gh curl ;;
    esac
    if ! command -v uv >/dev/null 2>&1; then
        curl -LsSf "$UV_INSTALLER" | sh
    fi
    export PATH="$HOME/.local/bin:$PATH"
}

clone_tool() {
    if [ ! -d "$TARGET/.git" ]; then
        mkdir -p "$(dirname "$TARGET")"
        git clone "https://github.com/$REPOSITORY.git" "$TARGET"
    fi
}

clone_files() (
    printf 'GitHub repo holding your den files (owner/name, empty to skip): ' >/dev/tty
    IFS= read -r files_repository </dev/tty
    [ -n "$files_repository" ] || return 0
    case "$files_repository" in
        */*/*|/*|*/|*\\*)
            printf 'Expected owner/name.\n' >&2
            exit 1
            ;;
        */*) ;;
        *)
            printf 'Expected owner/name.\n' >&2
            exit 1
            ;;
    esac
    files_target="$HOME/repos/${files_repository#*/}"
    if [ "$files_target" = "$TARGET" ]; then
        printf 'Your files repo cannot be cloned to %s: that is where den lives. Clone it elsewhere and pick it on first launch.\n' "$files_target" >&2
        exit 1
    fi
    if [ -d "$files_target/.git" ]; then
        return 0
    fi
    if ! gh auth status >/dev/null 2>&1; then
        gh auth login --hostname github.com --git-protocol https --web </dev/tty
        gh auth setup-git
    fi
    mkdir -p "$(dirname "$files_target")"
    gh repo clone "$files_repository" "$files_target"
)

install_prerequisites
clone_tool
clone_files
exec "$TARGET/den" </dev/tty
