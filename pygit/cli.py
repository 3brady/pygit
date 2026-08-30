import argparse, os, sys, pyfiglet, textwrap, subprocess
from colorama import Fore

from . import data, base , diff


def main():
    args = parse_args()
    args.func(args)


def parse_args():
    banner = pyfiglet.figlet_format("PYGIT", font="big")

    parser = argparse.ArgumentParser(prog='pygit', description='a version control system written in python',
                                     epilog=banner, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command")
    commands.required = True

    oid = base.get_oid

    init_parser = commands.add_parser("init", help='initialize pygit repository')
    init_parser.set_defaults(func=init)

    hash_object_parser = commands.add_parser("hash-object", help='hash pygit object')
    hash_object_parser.set_defaults(func=hash_object)
    hash_object_parser.add_argument("file")

    cat_file_parser = commands.add_parser("cat-file", help='cat file')
    cat_file_parser.set_defaults(func=cat_file)
    cat_file_parser.add_argument("object", type=oid)

    write_tree_parser = commands.add_parser("write-tree", help='write tree')
    write_tree_parser.set_defaults(func=write_tree)

    read_tree_parser = commands.add_parser('read-tree', help='read tree')
    read_tree_parser.set_defaults(func=read_tree)
    read_tree_parser.add_argument('tree', type=oid)

    commit_parser = commands.add_parser('commit', help='commit changes')
    commit_parser.set_defaults(func=commit)
    commit_parser.add_argument('-m', '--message', required=True)

    log_parser = commands.add_parser('log', help='logs previous commits')
    log_parser.set_defaults(func=log)
    log_parser.add_argument('oid', default='@', type=oid, nargs='?')

    checkout_parser = commands.add_parser('checkout', help='checkout to a diiferent commit')
    checkout_parser.set_defaults(func=checkout)
    checkout_parser.add_argument('commit')

    tag_parser = commands.add_parser('tag', help='tag a commit')
    tag_parser.set_defaults(func=tag)
    tag_parser.add_argument('name')
    tag_parser.add_argument('oid', default='@', type=oid, nargs='?')

    vis_parser = commands.add_parser('vis', help='visualize a history')
    vis_parser.set_defaults(func=vis)

    branch_parser = commands.add_parser('branch', help="branch")
    branch_parser.set_defaults(func=branch)
    branch_parser.add_argument('name' , nargs='?')
    branch_parser.add_argument('start_point', default='@', type=oid , nargs='?')

    status_parser = commands.add_parser('status' , help='displays the status of the files')
    status_parser.set_defaults(func = status)

    reset_parser = commands.add_parser('reset' , help='reset pygit repository')
    reset_parser.set_defaults(func = reset)
    reset_parser.add_argument('commit' , type=oid)

    show_parser = commands.add_parser('show' , help='show a history')
    show_parser.set_defaults(func = show)
    show_parser.add_argument('oid' , default='@' , type = oid , nargs='?')

    diff_parser = commands.add_parser('diff' , help='displays the differnce between two trees , usually the first one of them is the working tree ')
    diff_parser.set_defaults(func = _diff)
    diff_parser.add_argument('commit' , default='@' , type=oid , nargs='?')

    merge_parser = commands.add_parser('merge' , help='merge two commits , or branches')
    merge_parser.set_defaults(func = merge)
    merge_parser.add_argument('commit' , type = oid)

    merge_base_parser = commands.add_parser('merge-base' , help='merge base')
    merge_base_parser.set_defaults(func = merge_base)
    merge_base_parser.add_argument('commit1' , type=oid)
    merge_base_parser.add_argument('commit2', type=oid)

    return parser.parse_args()


def init (args):
    base.init()
    print (f'Initialized empty pygit repository in {os.getcwd()}/{data.GIT_DIR}')


def hash_object (args):
    with open (args.file, 'rb') as f:
        print (data.hash_object (f.read ()))


def cat_file (args):
    sys.stdout.flush ()
    sys.stdout.buffer.write (data.get_object (args.object, expected=None))


def write_tree (args):
    print (base.write_tree ())


def read_tree (args):
    base.read_tree (args.tree)


def commit (args):
    print (base.commit (args.message))


def _print_commit(oid , commit , refs = None):
    refs_str = f' ({", ".join(refs)})' if refs else ''
    print( Fore.YELLOW  , f'commit {oid}{refs_str}\n')
    print( Fore.WHITE , textwrap.indent(commit.message , '    ' ))
    print('')

def log (args):

    refs = {}
    for refname , ref in data.iter_refs():
        refs.setdefault(ref.value, []).append(refname)


    for oid in base.iter_commits_and_parents ({args.oid}):
        commit = base.get_commit (oid)
        _print_commit(oid , commit , refs.get(oid))

def show(args):
    if not args.oid:
        return
    commit = base.get_commit(args.oid)
    parent_tree = None
    if commit.parents:
        parent_tree = base.get_commit(commit.parents[0]).tree

    _print_commit(args.oid , commit)
    result = diff.diff_trees(
        base.get_tree(parent_tree) , base.get_tree(commit.tree))

    sys.stdout.flush ()
    sys.stdout.buffer.write (result)

def checkout (args):
    base.checkout (args.commit)


def tag (args):
    base.create_tag (args.name, args.oid)


def branch (args):
    if not args.name:
        current = base.get_branch_name()
        for branch in base.iter_branch_name():
            if branch == current :
                print( Fore.RED , f'* {branch}')
            else :
                print( Fore.WHITE , branch)
    else :
        base.create_branch(args.name , args.start_point)
        print(f'Branch {args.name} created at {args.start_point[:10]}')


def status(args):
    HEAD = base.get_oid('@')
    branch = base.get_branch_name()
    if branch :
        print(f'On branch {branch}')
    else :
        print(f'HEAD detached at {HEAD[:10]}')

    MERGE_HEAD = data.get_ref('MERGE_HEAD').value
    if MERGE_HEAD :
        print(f'Merging with{MERGE_HEAD[:10]}')

    print('\nChanges to be committed:\n')
    HEAD_tree = HEAD and base.get_commit(HEAD).tree

    for path , action in diff.iter_changed_files(base.get_tree(HEAD_tree) , base.get_working_tree()):
        print(f'{action:>12}: {path}')

def reset(args):
    base.reset(args.commit)


def _diff(args):
    tree = args.commit and base.get_commit(args.commit).tree

    result = diff.diff_trees( base.get_tree(tree) , base.get_working_tree() )
    sys.stdout.flush ()
    sys.stdout.buffer.write (result)

def merge(args):
    base.merge (args.commit)

def merge_base(args):
    print( base.get_merge_base(args.commit1 , args.commit2) )

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
        if commit.parents:
            dot += f'"{oid}" -> "{commit.parents[0]}"\n'

    dot += '}'
    print(dot)
    with subprocess.Popen(
            ['dot', '-Tx11', '/dev/stdin'],
            stdin=subprocess.PIPE) as proc:
        proc.communicate(dot.encode())
# ==========================================================================#
