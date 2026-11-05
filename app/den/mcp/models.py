from dataclasses import dataclass


@dataclass(frozen=True)
class McpServer:
    name: str
    url: str | None = None
    command: str | None = None
    args: tuple[str, ...] = ()
    bearer_token_env: str | None = None

    @property
    def identity(self) -> tuple:
        if self.url:
            return ("url", self.url.rstrip("/"))
        return ("command", self.command, self.args)

    @property
    def target(self) -> str:
        return self.url or " ".join([self.command or "", *self.args])
