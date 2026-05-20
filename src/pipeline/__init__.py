import warnings

warnings.warn(
    "src.pipeline 已废弃，请使用 src.rag 代替",
    DeprecationWarning,
    stacklevel=2,
)

from src.rag.parsers import registry as PARSERS
from src.rag.parsers import clean_nodes, chunk_nodes

__all__ = ["PARSERS", "clean_nodes", "chunk_nodes"]
