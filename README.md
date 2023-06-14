# Gitignorant

Gitignorant is (aspires to be)

* a [spec]-compliant .gitignore file parser and matcher
* for Python 3.7 and newer
* with full type hinting and test coverage
* and nothing you don't need

## Features

* Parses .gitignore (and .gitignore style) files
* Matches against list of parsed rules with the same
  semantics as Git ("last rule wins")

## Unfeatures

* Trees of .gitignore files are not directly supported,
  but can be supported by client code.

[spec]: https://git-scm.com/docs/gitignore
