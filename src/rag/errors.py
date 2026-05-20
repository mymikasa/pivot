class UnsupportedContentTypeError(ValueError):
    def __init__(self, content_type: str) -> None:
        super().__init__(f"不支持的文件格式: {content_type}")
        self.content_type = content_type


class RerankerUnavailableError(RuntimeError):
    pass
