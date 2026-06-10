from tfversion.config import BackendConfig


class VerboseFormatter:
    def __init__(self, config: BackendConfig, version: str):
        self._config = config
        self._version = version

    def format(self) -> str:
        c = self._config
        lines = [
            self._line("Backend:", f"s3://{c.bucket}/{c.key}"),
            self._line("Profile:", c.profile or "default"),
            self._line("Region:", c.region),
            self._line("State version (last run):", self._version),
            self._line("Code constraint:", c.required_version or "(not set)"),
        ]
        return "\n".join(lines)

    def _line(self, label: str, value: str) -> str:
        return f"{label:<26}{value}"
