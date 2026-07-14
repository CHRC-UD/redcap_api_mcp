from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class Profile:
    name: str
    api_url: str
    project_title: str = ""
    ca_bundle: str | None = None
    report_aliases: dict[str, str] = field(default_factory=dict)
    protected_fields: list[str] = field(default_factory=list)
    identifiers_enabled: bool = False

    def public(self, default: bool) -> dict[str, object]:
        return {
            "name": self.name,
            "project_title": self.project_title,
            "default": default,
            "report_aliases": sorted(self.report_aliases),
            "identifiers_enabled": self.identifiers_enabled,
        }

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "Profile":
        return cls(**data)  # type: ignore[arg-type]
