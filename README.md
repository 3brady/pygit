# pygit

A version control system (Git wannabe) written in Python, built to understand how Git actually works under the hood.

`pygit` reimplements Git's core internals — content-addressed objects, trees, commits, branches, merging, and a basic filesystem-based remote — in plain Python. It's a learning project, not a production VCS: don't use it for anything you care about, but do read the source if you want to understand what `.git` is actually doing.

## Features

- Content-addressed object store (blobs, trees, commits), zlib-compressed and hashed the same way Git does
- Staging index, commits, branches, tags
- `diff` and three-way `merge` (via the system `diff`/`diff3` tools)
- Fast-forward and non-fast-forward merges with conflict markers
- Basic filesystem remotes: `fetch` / `push`
- `.pygitignore` support (directory, glob, and exact-name patterns)
- A commit graph visualizer (`pygit vis`) via Graphviz

## Usage

```bash
pygit init
echo "hello" > file.txt
pygit add file.txt
pygit commit -m "first commit"
pygit log
```

Branching and merging:

```bash
pygit branch feature
pygit checkout feature
# ... make changes, commit ...
pygit checkout master
pygit merge feature
```

Visualize the commit graph:

```bash
pygit vis
```

See `pygit --help` or `pygit <command> --help` for the full command list (`status`, `diff`, `tag`, `reset`, `show`, `fetch`, `push`, and more).

## Requirements

- Python 3.8+
- [Graphviz](https://graphviz.org/download/) (`dot` binary) — only needed for `pygit vis`
- `diff` and `diff3` (present by default on most Linux/macOS systems) — needed for `pygit diff` and `pygit merge`

## Installation

### From a release (recommended for users)

Download the wheel from the [Releases page](https://github.com/3brady/pygit/releases) and install it with pip:

```bash
pip install https://github.com/3brady/pygit/releases/download/v1.0.0/pygit-1.0.0-py3-none-any.whl
```

### From source (for contributing / development)

```bash
git clone https://github.com/3brady/pygit.git
cd pygit
python3 -m venv env
source env/bin/activate
pip install -r requirements.txt
pip install -e .
```

After that, run `pygit` to try it out.

## Contributing

Issues and pull requests are welcome. This project exists mainly to explore Git internals, so contributions that improve clarity, correctness, or test coverage are especially appreciated.

## License

Apache License 2.0 — see [LICENSE](LICENSE).
