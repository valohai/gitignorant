from typing import List

import pytest

from gitignorant import (
    Rule,
    check_match,
    check_path_match,
    parse_gitignore_file,
    try_parse_rule,
)

GITIGNORE_STRING = (
    r"""
# Hello! this line is ignored.

# comment
#comment
comment_after.file # a comment must be on its own line

*.peasoup
a?.john
zz*
!/[a-f]*.peasoup
# world
!booze/*.peasoup
!/scaffolding/*.peasoup

# Directory testing
recipes/
!/other/recipes/
notes/private
!recipes/include_anyway

# Escape testing
\!important*
"""
    r"spaced_out\ "  # this is separate to avoid trimming whitespace
)


@pytest.fixture(scope="session")
def rules() -> List[Rule]:
    return list(parse_gitignore_file(GITIGNORE_STRING.strip().splitlines()))


TEST_CASES = [
    (False, "hello"),
    (True, "hello.peasoup"),
    (False, "hello.peasoupiness"),
    (True, "ballo/allo.peasoup"),
    (False, "allo.peasoup"),
    (False, "cullo.peasoup"),
    (True, "bazze/allo.peasoup"),
    (False, "booze/allo.peasoup"),
    (True, "booze/scaffolding/allo.peasoup"),
    (False, "scaffolding/allo.peasoup"),
    (True, "asdf/ab.john"),
    (False, "asdf/aba.john"),
    (True, "ab.john"),
    (False, "asdf/cb.john"),
    (True, "!important_1*"),
    (True, "spaced_out "),
    (False, "spaced_out"),
    (True, "zztop"),
    (False, "jazztop"),
    (False, "# comment"),
    (False, "#comment"),
    (False, "comment"),
    (False, "comment_after.file"),
    (True, "comment_after.file # a comment must be on its own line"),
]


@pytest.mark.parametrize(["expected", "path"], TEST_CASES)
@pytest.mark.parametrize("func", ["check_match", "check_path_match"])
def test_gitignorant_files(
    rules: List[Rule],
    path: str,
    expected: bool,
    func: str,
) -> None:
    if func == "check_match":
        assert check_match(rules, path, is_dir=False) == expected
    elif func == "check_path_match":
        assert check_path_match(rules, path) == expected
    else:
        raise NotImplementedError("...")


@pytest.mark.parametrize(
    "expected,path",
    [
        (True, "foo/recipes"),
        (False, "other/recipes"),
        (True, "/recipes"),
    ],
)
def test_gitignorant_dirs(rules: List[Rule], path: str, expected: bool) -> None:
    assert check_match(rules, path, is_dir=True) == expected


@pytest.mark.parametrize(
    "expected, path",
    [
        (True, "a/b"),
        (True, "a/x/b"),
        (True, "a/x/y/b"),
    ],
)
def test_spec_internal_doublestar(path: str, expected: bool) -> None:
    # * A slash followed by two consecutive asterisks then a slash matches
    #     zero or more directories. For example, "a/**/b"
    #     matches "a/b", "a/x/b", "a/x/y/b" and so on.
    r = try_parse_rule("a/**/b")
    assert r
    assert r.matches(path) == expected


@pytest.mark.parametrize(
    "expected, path",
    [
        (True, "abc/a"),
        (True, "abc/x/b"),
        (True, "abc/x/y/b"),
    ],
)
def test_spec_trailing_doublestar(path: str, expected: bool) -> None:
    # * A trailing "/**" matches everything inside. For example, "abc/**"
    #     matches all files inside directory "abc", relative to the location
    #     of the .gitignore file, with infinite depth.
    r = try_parse_rule("abc/**")
    assert r
    assert r.matches(path) == expected


@pytest.mark.parametrize(
    "expected, path",
    [
        (True, "doop/foo"),
        (True, "abc/bloop/buup/foo"),
        (False, "doop/foo/zoop"),
        (False, "abc/bloop/buup/foro"),
    ],
)
def test_spec_leading_doublestar(path: str, expected: bool) -> None:
    # * A leading "**" followed by a slash means match in all directories.
    #     For example, "**/foo" matches file or directory "foo" anywhere, the
    #     same as pattern "foo". "**/foo/bar" matches file or directory "bar"
    #     anywhere that is directly under directory "foo".
    r = try_parse_rule("**/foo")
    assert r
    assert r.matches(path) == expected


def test_spec_trailing_dir_magic() -> None:
    # * For example, a pattern doc/frotz/ matches doc/frotz directory, but not
    #   a/doc/frotz directory; however frotz/ matches frotz and a/frotz that
    #   is a directory (all paths are relative from the .gitignore file).
    r1 = try_parse_rule("doc/frotz/")
    assert r1
    assert r1.matches("doc/frotz", is_dir=True)
    assert not r1.matches("a/doc/frotz", is_dir=True)
    r2 = try_parse_rule("frotz/")
    assert r2
    assert r2.matches("frotz", is_dir=True)
    assert r2.matches("a/frotz", is_dir=True)


def test_unfinished_group_parsing() -> None:
    r1 = try_parse_rule("unfinished/symp[athy")
    assert r1
    assert r1.matches("unfinished/sympa", is_dir=False)
    assert r1.matches("unfinished/sympt", is_dir=False)
    assert r1.matches("unfinished/symph", is_dir=False)
    assert r1.matches("unfinished/sympy", is_dir=False)
    assert not r1.matches("unfinished/sympathy", is_dir=False)


CHECK_PATH_MATCH_CASES = [
    # These should match since `recipes/` is in the list,
    # and it's not anchored to the root
    ("recipes/zep", True),
    ("splop/recipes/zep", True),
    # all subdirectories and files inside subdirectories too
    ("recipes/xoop/", True),
    ("recipes/xoop/zep", True),
    ("recipes/xoop/zep/", True),
    ("recipes/pkex/pox/ioa/hai/kxr/aha", True),
    ("splop/recipes/xoop/xep", True),
    # Subdirectory match (`notes/private`) also catches everything under it,
    # including further subdirectories
    ("notes/private", True),
    ("notes/private/ramblings/trees", True),
    ("notes/private/free_stuff", True),
    # However, subdirectory match is only relative to the .gitignore location and
    # not any subdirectories
    ("splop/notes/private/notes_on_splop", False),
    # Negative rule on a nested file inside a positive rule matching path denies match
    ("recipes/include_anyway/delicious_plum_pie.txt", False),
    ("recipes/include_anyway/more_pie_recipes/rhubarb_pie.txt", False),
    # This should not match, since `/other/recipes/` is explicitly negated
    ("other/recipes/zep", False),
    # This too should match, since it's trying to ignore the whole folder
    ("recipes/", True),
]


@pytest.mark.parametrize(["path", "expected"], CHECK_PATH_MATCH_CASES)
def test_check_path_match(rules: List[Rule], path: str, expected: bool) -> None:
    assert check_path_match(rules, path) == expected
