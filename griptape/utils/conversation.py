from __future__ import annotations
from typing import TYPE_CHECKING
from attr import define, field

if TYPE_CHECKING:
    from griptape.memory.structure import ConversationMemory


@define(frozen=True)
class Conversation:
    memory: ConversationMemory = field()

    def lines(self) -> list[str]:
        lines = []

        for run in self.memory.runs:
            lines.extend((f"Q: {run.input}", f"A: {run.output}"))
        return lines

    def prompt_stack(self) -> list[str]:
        return [
            f"{stack.role}: {stack.content}"
            for stack in self.memory.to_prompt_stack().inputs
        ]

    def __str__(self) -> str:
        return str.join("\n", self.lines())
