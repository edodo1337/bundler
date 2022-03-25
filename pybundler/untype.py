import argparse
import ast
from pathlib import Path
import sys


class TypeHintRemover(ast.NodeTransformer):
    def visit_FunctionDef(self, node):
        node.returns = None

        if node.args.args:
            for arg in node.args.args:
                arg.annotation = None
        return node

    def visit_Import(self, node):
        node.names = [n for n in node.names if n.name != 'typing']
        return node if node.names else None

    def visit_ImportFrom(self, node):
        return node if node.module != 'typing' else None


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--src', help='script path')
    argc = parser.parse_args()

    src_path = Path(argc.src).resolve()

    if not src_path.exists():
        sys.exit("Source directory doesn't exists")

    with open(src_path) as f:
        src = f.read()
        parsed_source = ast.parse(src)
        transformed = TypeHintRemover().visit(parsed_source)
        print(ast.unparse(transformed))
