from den import packages
from den.manifest.models import Package


def package(name, method, *targets):
    return Package(name, "cli", method, targets, None, None)


def test_update_steps_upgrade_only_outdated_targets_grouped_per_manager():
    manifest = [
        package("php", "brew", "php", "composer"),
        package("gh", "brew", "gh"),
        package("obsidian", "cask", "obsidian"),
        package("ty", "uv_tool", "ty"),
    ]
    available = {"php": {"composer": "2.10"}, "obsidian": {"obsidian": "1.14"}, "ty": {"ty": "0.0.85"}}
    assert packages.update_steps(manifest, available) == [
        "HOMEBREW_NO_ASK=1 brew upgrade --formula composer",
        "HOMEBREW_NO_ASK=1 brew upgrade --cask obsidian",
        "uv tool upgrade ty",
    ]


def test_install_trusts_third_party_tap_targets_before_installing_them():
    manifest = [
        package("hex", "cask", "anomalyco/tap/hex"),
        package("obsidian", "cask", "obsidian"),
        package("rift", "brew", "acsandmann/tap/rift"),
        package("gh", "brew", "gh"),
    ]
    assert packages.install_steps(manifest) == [
        "HOMEBREW_NO_ASK=1 brew trust --cask anomalyco/tap/hex",
        "HOMEBREW_NO_ASK=1 brew install --cask anomalyco/tap/hex obsidian",
        "HOMEBREW_NO_ASK=1 brew trust --formula acsandmann/tap/rift",
        "HOMEBREW_NO_ASK=1 brew install acsandmann/tap/rift gh",
    ]
