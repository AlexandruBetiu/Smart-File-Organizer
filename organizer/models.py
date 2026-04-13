from dataclasses import asdict, dataclass, field


@dataclass
class FilePlan:
    source: str
    file_name: str
    criterion: str
    group_name: str
    destination_folder: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class MoveRecord:
    source: str
    destination: str
    moved_at: str
    criterion: str
    group_name: str
    status: str = "moved"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class OrganizationResult:
    folder: str
    criterion: str
    moved_files: list[MoveRecord] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    stopped: bool = False

    @property
    def moved_count(self) -> int:
        return len(self.moved_files)
