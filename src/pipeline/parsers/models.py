from dataclasses import dataclass, field


@dataclass
class Section:
    text: str
    metadata: dict = field(default_factory=dict)


@dataclass
class Chunk:
    index: int
    content: str
    token_count: int
    metadata: dict = field(default_factory=dict)
