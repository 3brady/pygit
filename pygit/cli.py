import argparse, os, sys, pyfiglet, textwrap, subprocess
from colorama import Fore

from . import data, base


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
    checkout_parser.add_argument('oid', type=oid)

    tag_parser = commands.add_parser('tag', help='tag a commit')
    tag_parser.set_defaults(func=tag)
    tag_parser.add_argument('name')
    tag_parser.add_argument('oid', default='@', type=oid, nargs='?')

    vis_parser = commands.add_parser('vis', help='visualize a history')
    vis_parser.set_defaults(func=vis)

    branch_parser = commands.add_parser('branch', help="branch")
    branch_parser.set_defaults(func=branch)
    branch_parser.add_argument('name')
    branch_parser.add_argument('starting_point', default='@', nargs='?')

    return parser.parse_args()


def init(args):
    data.init()
    print(f"Initialized empty pygit repository at {os.getcwd()}/{data.GIT_DIR}")


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


def log(args):
    for oid in base.iter_commits_and_parents({args.oid}):
        commit = base.get_commit(oid)

        print(Fore.YELLOW, f'commit {oid}\n')
        print(Fore.WHITE, textwrap.indent(commit.message, '    '))
        print('')


def checkout(args):
    base.checkout(args.oid)


def branch(args):
    base.create_branch(args.name, args.starting_point)
    print(f'Branch {args.name} created at {args.starting_point}')


def tag(args):
    base.create_tag(args.name, args.oid)


# for visualization / mostly vibe-coded :)
# ==========================================================================#
def vis(args):
    head = data.get_ref('HEAD')
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
        if commit.parent:
            dot += f'"{oid}" -> "{commit.parent}"\n'

    dot += '}'
    print(dot)
    with subprocess.Popen(
            ['dot', '-Tx11', '/dev/stdin'],
            stdin=subprocess.PIPE) as proc:
        proc.communicate(dot.encode())
# ==========================================================================#
