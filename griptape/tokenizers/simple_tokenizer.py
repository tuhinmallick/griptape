from attr import define, field
from griptape.tokenizers import BaseTokenizer


@define(frozen=True)
class SimpleTokenizer(BaseTokenizer):
    characters_per_token: int = field(kw_only=True)
    max_tokens: int = field(kw_only=True)

    def count_tokens(self, text: str) -> int:
        return (len(text) + self.characters_per_token - 1) // self.characters_per_token
