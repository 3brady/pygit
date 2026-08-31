import argparse, os, sys, pyfiglet, textwrap, subprocess
from colorama import Fore, init as colorama_init
from . import data, base, diff, remote

colorama_init(strip=not sys.stdout.isatty())


def main():
    with data.change_git_dir('.'):
        args = parse_args()
        args.func(args)


def parse_args():
    banner = pyfiglet.figlet_format("PYGIT", font="big")

    parser = argparse.ArgumentParser(prog='pygit', description='a version control system written in python',
                                     epilog=banner, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command")
    commands.required = True

    oid = base.get_oid

    init_parser = commands.add_parser(
        "init", help='create an empty pygit repository in the current directory')
    init_parser.set_defaults(func=init)

    hash_object_parser = commands.add_parser(
        "hash-object", help='compute the object id (hash) of a file and store it as a blob')
    hash_object_parser.set_defaults(func=hash_object)
    hash_object_parser.add_argument("file", help='path to the file to hash and store')

    cat_file_parser = commands.add_parser(
        "cat-file", help='print the raw content of a stored object')
    cat_file_parser.set_defaults(func=cat_file)
    cat_file_parser.add_argument(
        "object", type=oid, help='object id, or a name pygit can resolve (branch, tag, @)')

    write_tree_parser = commands.add_parser(
        "write-tree", help='write the current index (staging area) out as a tree object')
    write_tree_parser.set_defaults(func=write_tree)

    read_tree_parser = commands.add_parser(
        'read-tree', help='replace the index with the contents of a tree object')
    read_tree_parser.set_defaults(func=read_tree)
    read_tree_parser.add_argument('tree', type=oid, help='oid of the tree to load into the index')

    commit_parser = commands.add_parser(
        'commit', help='record the staged changes as a new commit')
    commit_parser.set_defaults(func=commit)
    commit_parser.add_argument(
        '-m', '--message', required=True, help='commit message describing the change')

    log_parser = commands.add_parser(
        'log', help='show commit history starting from a given commit')
    log_parser.set_defaults(func=log)
    log_parser.add_argument(
        'oid', default='@', type=oid, nargs='?',
        help="commit to start from (default: @, the current HEAD)")

    checkout_parser = commands.add_parser(
        'checkout', help='switch the working directory and HEAD to a branch or commit')
    checkout_parser.set_defaults(func=checkout)
    checkout_parser.add_argument(
        'commit', help='branch name or commit id to check out')

    tag_parser = commands.add_parser(
        'tag', help='create a named tag pointing at a commit')
    tag_parser.set_defaults(func=tag)
    tag_parser.add_argument('name', help='name for the new tag')
    tag_parser.add_argument(
        'oid', default='@', type=oid, nargs='?',
        help='commit to tag (default: @, the current HEAD)')

    vis_parser = commands.add_parser(
        'vis', help='render the commit graph with Graphviz (requires the "dot" binary)')
    vis_parser.set_defaults(func=vis)

    branch_parser = commands.add_parser(
        'branch', help='list branches, or create a new one')
    branch_parser.set_defaults(func=branch)
    branch_parser.add_argument(
        'name', nargs='?',
        help='name of the branch to create; omit to list existing branches')
    branch_parser.add_argument(
        'start_point', default='@', type=oid, nargs='?',
        help='commit the new branch should start at (default: @, the current HEAD)')

    status_parser = commands.add_parser(
        'status', help='show the current branch and pending changes')
    status_parser.set_defaults(func=status)

    reset_parser = commands.add_parser(
        'reset', help='move HEAD to a given commit without changing tracked files')
    reset_parser.set_defaults(func=reset)
    reset_parser.add_argument('commit', type=oid, help='commit to reset HEAD to')

    show_parser = commands.add_parser(
        'show', help='show a commit and the changes it introduced')
    show_parser.set_defaults(func=show)
    show_parser.add_argument(
        'oid', default='@', type=oid, nargs='?',
        help='commit to show (default: @, the current HEAD)')

    diff_parser = commands.add_parser(
        'diff', help='show changes between the working tree, the index, or a commit')
    diff_parser.set_defaults(func=_diff)
    diff_parser.add_argument(
        '--cached', action='store_true',
        help='compare the index against HEAD instead of the working tree')
    diff_parser.add_argument(
        'commit', nargs='?',
        help='commit to diff against (default: the index, or HEAD with --cached)')

    merge_parser = commands.add_parser(
        'merge', help='merge a branch or commit into the current branch')
    merge_parser.set_defaults(func=merge)
    merge_parser.add_argument(
        'commit', type=oid, help='branch name or commit id to merge in')

    merge_base_parser = commands.add_parser(
        'merge-base', help='find the common ancestor commit of two commits')
    merge_base_parser.set_defaults(func=merge_base)
    merge_base_parser.add_argument('commit1', type=oid, help='first commit')
    merge_base_parser.add_argument('commit2', type=oid, help='second commit')

    fetch_parser = commands.add_parser(
        'fetch', help='download commits and objects from a remote pygit repository')
    fetch_parser.set_defaults(func=fetch)
    fetch_parser.add_argument(
        'remote', help='filesystem path to the remote repository')

    push_parser = commands.add_parser(
        'push', help='upload commits and update a branch on a remote repository')
    push_parser.set_defaults(func=push)
    push_parser.add_argument('remote', help='filesystem path to the remote repository')
    push_parser.add_argument('branch', help='name of the branch to push')

    add_parser = commands.add_parser(
        'add', help='stage files or directories to be tracked')
    add_parser.set_defaults(func=add)
    add_parser.add_argument(
        'files', nargs='+', help='one or more file or directory paths to stage')

    return parser.parse_args()


def init(args):
    base.init()
    print(f'Initialized empty pygit repository in {os.getcwd()}/{data.GIT_DIR}')


def hash_object(args):
    with open(args.file, 'rb') as f:
        print(data.hash_object(f.read()))


def cat_file(args):
    sys.stdout.flush()
    sys.stdout.buffer.write(data.get_object(args.object, expected=None))


def write_tree(args):
    print(base.write_tree())


def read_tree(args):
    base.read_tree(args.tree)


def commit(args):
    print(base.commit(args.message))


def _print_commit(oid, commit, refs=None):
    refs_str = f' ({", ".join(refs)})' if refs else ''
    print(Fore.YELLOW, f'commit {oid}{refs_str}\n')
    print(Fore.WHITE, textwrap.indent(commit.message, '    '))
    print('')


def log(args):
    refs = {}
    for refname, ref in data.iter_refs():
        refs.setdefault(ref.value, []).append(refname)

    for oid in base.iter_commits_and_parents({args.oid}):
        commit = base.get_commit(oid)
        _print_commit(oid, commit, refs.get(oid))


def show(args):
    if not args.oid:
        return
    commit = base.get_commit(args.oid)
    parent_tree = None
    if commit.parents:
        parent_tree = base.get_commit(commit.parents[0]).tree

    _print_commit(args.oid, commit)
    result = diff.diff_trees(
        base.get_tree(parent_tree), base.get_tree(commit.tree))

    sys.stdout.flush()
    sys.stdout.buffer.write(result)


def checkout(args):
    base.checkout(args.commit)


def tag(args):
    base.create_tag(args.name, args.oid)


def branch(args):
    if not args.name:
        current = base.get_branch_name()
        for branch in base.iter_branch_name():
            if branch == current:
                print(Fore.RED, f'* {branch}')
            else:
                print(Fore.WHITE, branch)
    else:
        base.create_branch(args.name, args.start_point)
        print(f'Branch {args.name} created at {args.start_point[:10]}')


def status(args):
    HEAD = base.get_oid('@')
    branch = base.get_branch_name()
    if branch:
        print(f'On branch {branch}')
    else:
        print(f'HEAD detached at {HEAD[:10]}')

    MERGE_HEAD = data.get_ref('MERGE_HEAD').value
    if MERGE_HEAD:
        print(f'Merging with {MERGE_HEAD[:10]}')

    print('\nChanges to be committed:\n')
    HEAD_tree = HEAD and base.get_commit(HEAD).tree

    for path, action in diff.iter_changed_files(base.get_tree(HEAD_tree), base.get_index_tree()):
        print(f'{action:>12}: {path}')

    print('\nChanges not staged for commit:\n')
    for path, action in diff.iter_changed_files(base.get_index_tree(), base.get_working_tree()):
        print(f'{action:>12}: {path}')


def reset(args):
    base.reset(args.commit)


def _diff(args):
    oid = args.commit and base.get_oid(args.commit)

    if args.commit:
        tree_from = base.get_tree(oid and base.get_commit(oid).tree)

    if args.cached:
        tree_to = base.get_index_tree()
        if not args.commit:
            oid = base.get_oid('@')
            tree_from = base.get_tree(oid and base.get_commit(oid).tree)
    else:
        tree_to = base.get_working_tree()
        if not args.commit:
            tree_from = base.get_index_tree()

    result = diff.diff_trees(tree_from, tree_to)
    sys.stdout.flush()
    sys.stdout.buffer.write(result)


def merge(args):
    base.merge(args.commit)


def merge_base(args):
    print(base.get_merge_base(args.commit1, args.commit2))


def fetch(args):
    remote.fetch(args.remote)


def push(args):
    remote.push(args.remote, f'refs/heads/{args.branch}')


def add(args):
    base.add(args.files)


# for visualization / mostly vibe-coded :)
# ==========================================================================#
def vis(args):
    head = base.get_oid('@')
    dot = 'digraph commit {\n'
    dot += 'bgcolor="transparent"\n'
    dot += 'node [fontname="Helvetica" fontsize=11]\n'
    dot += 'edge [color="#888888" penwidth=1.5 arrowsize=0.8]\n'

    oids = set()
    for refname, ref in data.iter_refs(deref=False):
        dot += (f'"{refname}" [shape=note style=filled '
                f'fillcolor="#a8d8ff" color="#5599cc" '
                f'fontname="Helvetica-Bold" penwidth=1.5]\n')
        dot += f'"{refname}" -> "{ref.value}" [color="#5599cc" style=dashed]\n'
        if not ref.symbolic:
            oids.add(ref.value)

    for oid in base.iter_commits_and_parents(oids):
        commit = base.get_commit(oid)
        if oid == head:
            fillcolor, bordercolor = '#ffd966', '#cc9900'
        else:
            fillcolor, bordercolor = '#f0f0f0', '#999999'
        label = f'{oid[:10]}\\n{commit.message}' if commit.message else oid[:10]
        dot += (f'"{oid}" [shape=box style="filled,rounded" '
                f'fillcolor="{fillcolor}" color="{bordercolor}" '
                f'penwidth=1.5 label="{label}" margin=0.15]\n')
        for parent in commit.parents:
            dot += f'"{oid}" -> "{parent}"\n'

    dot += '}'
    print(dot)
    with subprocess.Popen(
            ['dot', '-Tx11', '/dev/stdin'],
            stdin=subprocess.PIPE) as proc:
        proc.communicate(dot.encode())
# ==========================================================================#
