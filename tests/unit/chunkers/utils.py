from griptape.tokenizers import BaseTokenizer


def gen_paragraph(max_tokens: int, tokenizer: BaseTokenizer, sentence_separator: str) -> str:
    all_text = ""
    word = "foo"
    index = 0
    add_word = lambda base, w, i: sentence_separator.join([base, f"{w}-{i}"])

    while max_tokens >= tokenizer.count_tokens(add_word(all_text, word, index)):
        all_text = (
            f"{word}-{index}"
            if not all_text
            else add_word(all_text, word, index)
        )
        index += 1

    return all_text + sentence_separator
