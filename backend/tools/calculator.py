import json
import math
import re
from . import register


@register(
    "calculator",
    "计算数学表达式。支持 +, -, *, /, **, sqrt, sin, cos, log, pi, e 等。",
    {"expression": {"type": "string", "description": "要计算的数学表达式。例如：'2 + 3 * 4', 'sqrt(16)', 'sin(pi/2)'"}}
)
def calculator(expression: str) -> str:
    safe_dict = {
        "abs": abs, "round": round, "min": min, "max": max, "sum": sum,
        "pow": pow, "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos,
        "tan": math.tan, "asin": math.asin, "acos": math.acos,
        "atan": math.atan, "atan2": math.atan2, "log": math.log,
        "log10": math.log10, "log2": math.log2, "exp": math.exp,
        "floor": math.floor, "ceil": math.ceil, "factorial": math.factorial,
        "gcd": math.gcd, "degrees": math.degrees, "radians": math.radians,
        "pi": math.pi, "e": math.e, "tau": math.tau,
        "inf": float("inf"), "nan": float("nan"),
        "int": int, "float": float, "complex": complex,
    }
    try:
        # Validate only safe chars
        if not re.match(r'^[\d\s+\-*/().,eEpi\w%^<>!=&|~@]+$', expression):
            return json.dumps({"error": "Expression contains invalid characters"})
        result = eval(expression, {"__builtins__": {}}, safe_dict)
        return json.dumps({"expression": expression, "result": result}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Calculation error: {str(e)}"})
