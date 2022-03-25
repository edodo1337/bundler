import importlib
import inspect
import sys, argparse
from types import ModuleType
import ast
from pathlib import Path
from typing import Iterable

src_path = '.'

body_module_condition = lambda x: (
    not isinstance(x, ast.Import) and not isinstance(x, ast.ImportFrom)
)


class Analyzer(ast.NodeVisitor):
    def __init__(self):
        self.imports: list[ast.Import] = []
        self.froms: list[ast.ImportFrom] = []

    def visit_Import(self, node: ast.Import):
        self.imports.append(node)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        self.froms.append(node)
        self.generic_visit(node)


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def is_local_module(module: ModuleType, src_path: Path) -> bool:
    built_ins = {'sys', 'os'}

    if module.__name__ in built_ins:
        return False

    module_path = Path(inspect.getfile(module)).resolve()

    if src_path in module_path.parents:
        return True

    return False


def dfs(tree: ast.Module, visited_modules: set[str], depth=0):
    analyzer = Analyzer()
    analyzer.visit(tree)

    result_imports: list[ast.Import] = []
    result_froms: list[ast.ImportFrom] = []
    result_body: list[ast.stmt] = []

    import_node: ast.Import | ast.ImportFrom
    for import_node in analyzer.imports + analyzer.froms:
        if isinstance(import_node, ast.ImportFrom):
            inner_module = importlib.import_module(import_node.module)

            if not is_local_module(inner_module, src_path):
                result_imports.append(import_node)
                continue

            inner_module_src = inspect.getsource(inner_module)
            inner_tree = ast.parse(inner_module_src)

            if import_node.module in visited_modules:
                continue

            visited_modules.add(import_node.module)

            merged_imports, merged_froms, merged_body = dfs(inner_tree, visited_modules, depth + 1)
            result_imports.extend(merged_imports)
            result_froms.extend(merged_froms)
            result_body.extend(merged_body)

            module_body = get_all_stmnts(module=inner_module)
            result_body.extend(module_body)

        elif isinstance(import_node, ast.Import):
            for imp in import_node.names:
                inner_module = importlib.import_module(imp.name)

                if not is_local_module(inner_module, src_path):
                    result_imports.append(import_node)
                    continue

                inner_module_src = inspect.getsource(inner_module)
                inner_tree = ast.parse(inner_module_src)

                if imp.name in visited_modules:
                    continue

                visited_modules.add(imp.name)

                merged_imports, merged_froms, merged_body = dfs(
                    inner_tree, visited_modules, depth + 1
                )
                result_imports.extend(merged_imports)
                result_froms.extend(merged_froms)
                result_body.extend(merged_body)

                module_body = get_all_stmnts(inner_module)
                result_body.extend(module_body)

    return result_imports, result_froms, result_body


def get_stmt_by_name(module: ModuleType, part_name: str) -> ast.Module:
    part = ast.parse(inspect.getsource(getattr(module, part_name)))

    return part.body


def get_all_stmnts(module: ModuleType) -> Iterable[ast.stmt]:
    parts = ast.parse(inspect.getsource(module))

    return filter(body_module_condition, parts.body)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--src', help='script source directory')
    parser.add_argument('--main', help='script entry point file')
    argc = parser.parse_args()

    src_path = Path(argc.src).resolve()
    main_path = Path(argc.main).resolve()

    if not src_path.exists():
        sys.exit(bcolors.FAIL + "Source directory doesn't exists")

    if not src_path.is_dir():
        sys.exit(bcolors.FAIL + 'Src is not directory')

    if not main_path.is_file():
        sys.exit(bcolors.FAIL + 'Main is not file')

    with open(main_path) as f:
        text = f.read()
        tree = ast.parse(text)
        analyzer = Analyzer()
        analyzer.visit(tree)

        visited_modules = set()

        result_imports, result_froms, result_body = dfs(tree, visited_modules)

        result_body.extend(list(filter(body_module_condition, tree.body)))

        def distinct_imports(
            imports: list[ast.Import | ast.ImportFrom],
        ) -> set[ast.Import | ast.ImportFrom]:
            result = set((ast.unparse(i) for i in imports))

            return result

        def print_to_output():
            for i in distinct_imports(result_imports + result_froms):
                print(i)

            print()

            for b in result_body:
                print(ast.unparse(b))
                print()

        print_to_output()
