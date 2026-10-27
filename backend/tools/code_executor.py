import json
import sys
import io
import traceback
import ast
from . import register

SAFE_BUILTINS = {
    "abs": abs, "all": all, "any": any, "bin": bin, "bool": bool,
    "bytes": bytes, "chr": chr, "complex": complex, "dict": dict,
    "divmod": divmod, "enumerate": enumerate, "filter": filter,
    "float": float, "format": format, "frozenset": frozenset,
    "hex": hex, "int": int, "isinstance": isinstance,
    "len": len, "list": list, "map": map, "max": max, "min": min,
    "oct": oct, "ord": ord, "pow": pow, "print": print,
    "range": range, "repr": repr, "reversed": reversed,
    "round": round, "set": set, "slice": slice, "sorted": sorted,
    "str": str, "sum": sum, "tuple": tuple, "type": type,
    "zip": zip, "True": True, "False": False, "None": None,
    "__import__": __import__,
}


class SandboxValidator(ast.NodeVisitor):
    """AST 遍历器 — 阻断沙箱逃逸，但允许所有模块导入"""

    FORBIDDEN_DUNDER = frozenset({
        "__class__", "__bases__", "__mro__", "__subclasses__",
        "__globals__", "__builtins__", "__import__", "__code__",
        "__func__", "__self__", "__dict__", "__module__",
        "__getattribute__", "__getattr__", "__setattr__", "__delattr__",
        "__reduce__", "__reduce_ex__", "__getstate__", "__setstate__",
    })

    FORBIDDEN_NAMES = frozenset({
        "open", "exec", "eval", "compile", "getattr",
        "setattr", "delattr", "globals", "locals", "vars",
        "dir", "breakpoint", "input", "memoryview",
        "staticmethod", "classmethod", "property",
        "__import__", "copyright", "credits", "license",
    })

    def visit_Import(self, node):
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module is None:
            raise SyntaxError("禁止相对导入")
        self.generic_visit(node)

    def visit_Attribute(self, node):
        if isinstance(node.attr, str) and node.attr in self.FORBIDDEN_DUNDER:
            raise SyntaxError(f"禁止访问: .{node.attr}")
        self.generic_visit(node)

    def visit_Name(self, node):
        if node.id in self.FORBIDDEN_NAMES:
            raise SyntaxError(f"禁止使用: {node.id}")
        self.generic_visit(node)


@register(
    "code_execute",
    "在沙箱中执行 Python 代码。可导入任意模块进行安全研究和渗透测试。返回标准输出和最后一个表达式的结果。",
    {"code": {"type": "string", "description": "要执行的 Python 代码，最后一个表达式的结果会被返回"}}
)
def code_execute(code: str) -> str:
    try:
        tree = ast.parse(code)
        SandboxValidator().visit(tree)

        stdout = io.StringIO()
        stderr = io.StringIO()

        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = stdout
        sys.stderr = stderr

        result = None
        namespace = {"__builtins__": SAFE_BUILTINS}

        try:
            if tree.body:
                for node in tree.body[:-1]:
                    compiled = compile(ast.Module(body=[node], type_ignores=[]),
                                       "<sandbox>", "exec")
                    exec(compiled, namespace)

                last_node = tree.body[-1]
                if isinstance(last_node, ast.Expr):
                    compiled = compile(ast.Expression(body=last_node.value),
                                       "<sandbox>", "eval")
                    result = eval(compiled, namespace)
                else:
                    compiled = compile(ast.Module(body=[last_node], type_ignores=[]),
                                       "<sandbox>", "exec")
                    exec(compiled, namespace)
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

        output = stdout.getvalue()
        errors = stderr.getvalue()

        return json.dumps({
            "output": output.rstrip() if output else None,
            "errors": errors.rstrip() if errors else None,
            "result": repr(result) if result is not None else None,
        }, ensure_ascii=False)
    except SyntaxError as e:
        return json.dumps({"error": f"Security blocked: {e}"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Execution failed: {traceback.format_exc()}"}, ensure_ascii=False)
