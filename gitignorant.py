import re
from functools import lru_cache
from typing import Iterable, TextIO, Optional, Union, List

__all__ = [
    "Rule",
    "check_match",
    "parse_gitignore_file",
]

# TODO: this may not correctly support \] within ]
specials_re = re.compile(r"(\*+|\[|]|\?)")


@lru_cache(maxsize=512)
def compile_pattern(pat: str, is_dir: bool) -> "re.Pattern":  # type: ignore[type-arg]
    anchor = False
    if pat.startswith("/"):
        anchor = True
        pat = pat[1:]
    elif is_dir and "/" in pat:
        anchor = True

    re_bits = []
    if anchor:
        re_bits.append("^")

    bits = specials_re.split(pat)
    while bits:
        bit = bits.pop(0)
        if not bit:
            continue

        if bit == "?":
            re_bits.append(r"[^/]")
            continue

        if bit.startswith("*"):
            if len(bit) > 1:
                re_bits.append(".*")
            else:
                re_bits.append(r"[^/]*")
            continue

        if bit.startswith("["):
            alternation_contents = []
            while True:
                try:
                    bit = bits.pop(0)
                except IndexError:
                    # Instead of failing to parse,
                    # we just assume an unterminated [] seq is to the end of string
                    break
                if bit == "]":
                    break
                # Unescape everything but the dash – this may not be 100% correct.
                esc_bit = re.escape(bit).replace("\\-", "-")
                alternation_contents.append(esc_bit)
            re_bits.append("[%s]" % "".join(alternation_contents))
            continue

        if re_bits and re_bits[-1] == ".*":
            # If the last bit was a double star, we'll need to fix up any
            # leading slashes from this bit (since the double star would consume them).
            bit = bit.lstrip("/")

        re_bits.append(re.escape(bit))

    re_bits.append("$")
    re_content = "".join(re_bits)
    return re.compile(re_content)


class Rule:
    def __init__(self, *, negative: bool, content: str) -> None:
        self.negative = bool(negative)
        self.content = str(content)

    def __repr__(self) -> str:
        return f'<Rule {self.content!r}{ "(negative)" if self.negative else ""}>'

    def matches(self, path: str, is_dir: bool = False) -> bool:
        pat = self.content
        if pat.endswith("/"):
            if not is_dir:
                #   * If there is a separator at the end of the pattern then the pattern
                #     will only match directories, otherwise the pattern can match both
                #     files and directories.
                return False
            pat = pat.rstrip("/")
        re_pat = compile_pattern(pat, is_dir=is_dir)
        # `search` is correct since the regex is possibly anchored from the start
        res = re_pat.search(path)
        # This commented-out print() is useful for debugging.
        # print(self.content, "->", re_pat, "?", path, is_dir, ":", res)
        return bool(res)


def try_parse_rule(line: str) -> Optional["Rule"]:
    line = line.rstrip()  # Remove all trailing spaces
    if line.endswith("\\"):
        # "Trailing spaces are ignored unless they are quoted with backslash ("\")."

        # That is, now that we only have a slash left at the end of the path,
        # it must have been escaping a space.
        line = line[:-1] + " "
    if not line:
        # "A blank line matches no files, so it can serve as a separator
        #  for readability."
        return None
    if line.startswith("#"):
        # "A line starting with # serves as a comment."
        return None
    negative = False
    if line.startswith("!"):
        # "An optional prefix "!" which negates the pattern; any matching file
        #  excluded by a previous pattern will become included again. It is not
        #  possible to re-include a file if a parent directory of that file is
        #  excluded. Git doesn’t list excluded directories for performance
        #  reasons, so any patterns on contained files have no effect, no matter
        #  where they are defined."
        negative = True
        line = line[1:]
    elif line.startswith("\\!"):
        # "Put a backslash ("\") in front of the
        #  first "!" for patterns that begin with a literal "!", for
        #  example, "\!important!.txt"."
        line = line[1:]
    return Rule(negative=negative, content=line)


def check_match(rules: List[Rule], path: str, is_dir: bool = False) -> bool:
    # Algorithm: Find the last matching rule in the list and
    #            figure out whether it was not negative.
    for rule in reversed(rules):
        if rule.matches(path, is_dir):
            return not rule.negative
    return False


def parse_gitignore_file(f: Union[TextIO, Iterable[str]]) -> Iterable[Rule]:
    for line in f:
        rule = try_parse_rule(line)
        if rule is not None:
            yield rule
