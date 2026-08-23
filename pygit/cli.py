import argparse , os , sys , pyfiglet
from . import data , base

def main ():
    args = parse_args ()
    args.func (args)

def parse_args ():
    banner = pyfiglet.figlet_format("PYGIT", font="big")

    parser = argparse.ArgumentParser(prog = 'pygit' , description='a version control system written in python' , epilog=banner , formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest = "command")
    commands.required = True

    init_parser = commands.add_parser("init" , help='initialize pygit repository')
    init_parser.set_defaults(func = init)
    init_parser.set_defaults(func = init)

    hash_object_parser = commands.add_parser("hash-object" , help='hash pygit object')
    hash_object_parser.set_defaults(func = hash_object)
    hash_object_parser.add_argument("file")

    cat_file_parser = commands.add_parser("cat-file" , help='cat file')
    cat_file_parser.set_defaults(func = cat_file)
    cat_file_parser.add_argument("object")

    write_tree_parser = commands.add_parser("write-tree" , help='write tree')
    write_tree_parser.set_defaults(func = write_tree)

    read_tree_parser = commands.add_parser('read-tree' , help='read tree')
    read_tree_parser.set_defaults(func=read_tree)
    read_tree_parser.add_argument('tree')

    commit_parser = commands.add_parser('commit' , help= 'commit changes')
    commit_parser.set_defaults(func = commit)
    commit_parser.add_argument('-m','--message' , required=True)

    return parser.parse_args()

def init(args):
    data.init()
    print(f"Initialized empty pygit repository at {os.getcwd()}/{data.GIT_DIR}")

def hash_object(args):
    with open(args.file, 'rb') as f :
        print(data.hash_object(f.read()))

def cat_file(args) :
    sys.stdout.flush()
    sys.stdout.buffer.write(data.get_object(args.object, expected=None))

def write_tree(args):
    print(base.write_tree())

def read_tree(args):
    base.read_tree(args.tree)

def commit(args):
    print(base.commit(args.message))