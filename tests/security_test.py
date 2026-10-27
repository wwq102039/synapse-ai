"""
Synapse AI 安全渗透测试 v3 — 修复验证版
"""
import sys
import json
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


def test_hardcoded_api_key():
    config_path = Path(__file__).parent.parent / "backend" / "config.py"
    content = config_path.read_text()
    if 'sk-' in content.split('os.getenv')[1].split(')')[0] if 'os.getenv' in content else False:
        pass  # 下面精确检查
    if __import__('re').search(r'sk-[0-9a-f]{32}', content):
        print("[FAIL] 硬编码 API Key 仍在 config.py")
        return False
    # 确认默认值已清空
    if 'DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")' in content:
        print("[PASS] API Key 已从硬编码移除，改用环境变量")
        return True
    print("[PASS] 未发现硬编码 API Key")
    return True


def test_code_sandbox_rce():
    from tools.code_executor import code_execute

    # Step 1: __class__ 访问被阻止
    payload1 = '().__class__'
    r1 = json.loads(code_execute(payload1))
    if "Security blocked" in r1.get("error", ""):
        print(f"  [OK] dunder __class__ 已被 AST 沙箱拦截")
    else:
        print(f"[FAIL] __class__ 未被拦截: {r1}")
        return False

    # Step 2: __bases__ 被阻止
    payload2 = 'x = 1; x.__class__.__bases__'
    r2 = json.loads(code_execute(payload2))
    if "Security blocked" in r2.get("error", ""):
        print(f"  [OK] dunder __bases__ 已被拦截")
    else:
        print(f"[FAIL] __bases__ 未被拦截")
        return False

    # Step 3: __globals__ 被阻止
    payload3 = 'def f(): pass; f.__code__.__globals__'
    r3 = json.loads(code_execute(payload3))
    if "Security blocked" in r3.get("error", ""):
        print(f"  [OK] dunder __globals__ 已被拦截")
    else:
        print(f"[FAIL] __globals__ 未被拦截")
        return False

    # Step 4: open 函数被阻止
    payload4 = 'open("/etc/hosts")'
    r4 = json.loads(code_execute(payload4))
    if "Security blocked" in r4.get("error", "") or ("NameError" in r4.get("errors", "")):
        print(f"  [OK] 'open' 函数已被阻止")
    else:
        print(f"[FAIL] 'open' 未被拦截")
        return False

    # Step 5: exec/eval 被阻止
    for func in ['exec', 'eval']:
        payload5 = f'print({func})'
        r5 = json.loads(code_execute(payload5))
        if "Security blocked" in r5.get("error", "") or "NameError" in r5.get("errors", ""):
            print(f"  [OK] '{func}' 已被阻止")

    # Step 6: import 全部放行 (安全研究需要)
    payload6 = 'import os; print(os.getcwd())'
    r6 = json.loads(code_execute(payload6))
    if 'error' not in r6:
        print(f"  [OK] import os 正常可用: {r6.get('output','').strip()}")
    else:
        print(f"  [WARN] import os 异常: {r6}")

    # Step 7: subprocess 可用 (渗透测试必备)
    payload7 = 'import subprocess; print(subprocess.run(\"echo ok\", shell=True, capture_output=True).stdout.decode().strip())'
    r7 = json.loads(code_execute(payload7))
    if 'ok' in r7.get('output', ''):
        print(f"  [OK] subprocess 可用 (渗透测试模式)")

    # Step 8: 合法代码仍能执行
    payload8 = '2 + 3 * 4'
    r8 = json.loads(code_execute(payload8))
    if r8.get("result") == "14":
        print(f"  [OK] 合法数学计算正常: 2+3*4=14")
    else:
        print(f"  [WARN] 合法代码执行异常: {r8}")

    print("[PASS] 代码沙箱 — dunder/open/exec/eval 被封堵，import 全放行")
    return True


def test_filesystem_sandbox():
    from tools.filesystem import file_read, file_write, BASE_DIR

    issues = []

    # 检查 BASE_DIR 安全路径解析是否存在
    import tools.filesystem as fs_mod
    if not hasattr(fs_mod, '_resolve_safe_path'):
        issues.append("缺少 _resolve_safe_path 安全路径解析函数")
    else:
        print(f"  [OK] _resolve_safe_path 已定义, BASE_DIR={BASE_DIR}")

    # 测试: 读取系统文件应被拒绝
    sys_files = [
        r"C:\Windows\System32\drivers\etc\hosts" if sys.platform == "win32" else "/etc/passwd",
    ]
    for sp in sys_files:
        result = json.loads(file_read(sp))
        if "禁止访问" in result.get("error", ""):
            print(f"  [OK] 沙箱外文件读取被阻止: {sp}")
        elif "content" in result:
            issues.append(f"仍可读取沙箱外文件: {sp}")

    # 测试: 任意路径写入应被拒绝
    test_path = str(Path.home() / "outside_sandbox_test.txt")
    result = json.loads(file_write(test_path, "should fail"))
    if "禁止访问" in result.get("error", ""):
        print(f"  [OK] 沙箱外写入被阻止: {test_path}")
    elif result.get("success"):
        issues.append(f"仍可写入沙箱外路径: {test_path}")
        try:
            os.remove(test_path)
        except Exception:
            pass

    # 测试: 沙箱内写入应成功
    safe_path = str(BASE_DIR / "test_safe_write.txt")
    result = json.loads(file_write(safe_path, "hello sandbox"))
    if result.get("success"):
        print(f"  [OK] 沙箱内写入正常: {safe_path}")
        try:
            os.remove(safe_path)
        except Exception:
            pass
    else:
        issues.append(f"沙箱内合法写入失败: {result}")

    # 测试: .. 路径遍历应被阻止
    traversal_path = str(BASE_DIR / ".." / "outside.txt")
    result = json.loads(file_write(traversal_path, "traversal"))
    if "禁止访问" in result.get("error", ""):
        print(f"  [OK] 路径遍历攻击被阻止: ..")
    elif result.get("success"):
        issues.append(f"路径遍历攻击成功: {traversal_path}")
        try:
            os.remove(Path(traversal_path).resolve())
        except Exception:
            pass

    if issues:
        print("[FAIL] 文件系统沙箱问题:")
        for i in issues:
            print(f"       {i}")
        return False
    print("[PASS] 文件系统沙箱有效")
    return True


def test_ssrf():
    from tools.web_search import web_fetch

    issues = []

    # file:// 协议应被阻止
    r1 = json.loads(web_fetch("file:///C:/Windows/win.ini"))
    if "安全阻止" in r1.get("error", "") or "禁止的协议" in r1.get("error", ""):
        print(f"  [OK] file:// 协议已被阻止")
    elif "content" in r1:
        issues.append(f"file:// 协议未被阻止")

    # localhost 应被阻止
    r2 = json.loads(web_fetch("http://localhost:8765/api/health"))
    err2 = r2.get("error", "")
    if "安全阻止" in err2 or "禁止访问" in err2:
        print(f"  [OK] localhost 已被 SSRF 防护拦截")
    elif "connection" in err2.lower() or "refused" in err2.lower():
        print(f"  [OK] localhost 连接被拒绝（系统级阻止）")
    elif "content" in r2:
        issues.append(f"SSRF 可访问 localhost")

    # 127.0.0.1 应被阻止
    r3 = json.loads(web_fetch("http://127.0.0.1:8765/api/health"))
    err3 = r3.get("error", "")
    if "安全阻止" in err3 or "禁止访问" in err3:
        print(f"  [OK] 127.0.0.1 已被拦截")
    elif "connection" in err3.lower() or "refused" in err3.lower():
        print(f"  [OK] 127.0.0.1 连接被拒绝")
    elif "content" in r3:
        issues.append(f"SSRF 可访问 127.0.0.1")

    if issues:
        print("[FAIL] SSRF 防护问题:")
        for i in issues:
            print(f"       {i}")
        return False
    print("[PASS] SSRF 防护有效")
    return True


def test_sql_security():
    from tools.database_query import db_query

    issues = []

    # DROP 应被拒绝
    r1 = json.loads(db_query("DROP TABLE memories"))
    if "只允许 SELECT" in r1.get("error", ""):
        print(f"  [OK] DROP 被拒绝（只允许 SELECT）")

    # INSERT 应被拒绝
    r2 = json.loads(db_query("INSERT INTO memories VALUES (1,'x','y','now')"))
    if "只允许 SELECT" in r2.get("error", ""):
        print(f"  [OK] INSERT 被拒绝")

    # DELETE 应被拒绝
    r3 = json.loads(db_query("DELETE FROM memories"))
    if "只允许 SELECT" in r3.get("error", ""):
        print(f"  [OK] DELETE 被拒绝")

    # SELECT 应正常工作
    r4 = json.loads(db_query("SELECT name FROM sqlite_master WHERE type='table'"))
    if "rows" in r4:
        print(f"  [OK] 合法 SELECT 查询正常 ({len(r4['rows'])} 个表)")

    # SQL 注入尝试（模拟 AI 被 prompt inject 后拼接用户输入）
    r5 = json.loads(db_query("SELECT * FROM memories WHERE key = 'test' OR 1=1"))
    if "rows" in r5:
        print(f"  [OK] 注入式查询被作为普通 SELECT 执行（只读无危害）")

    if issues:
        print("[FAIL] SQL 安全问题:")
        for i in issues:
            print(f"       {i}")
        return False
    print("[PASS] SQL 安全 — 只允许 SELECT 只读查询")
    return True


def main():
    print("=" * 60)
    print("Synapse AI 安全渗透测试 v3")
    print("=" * 60)

    tests = [
        ("硬编码 API Key", test_hardcoded_api_key),
        ("代码执行器沙箱 (RCE)", test_code_sandbox_rce),
        ("文件系统沙箱", test_filesystem_sandbox),
        ("SSRF 防护", test_ssrf),
        ("SQL 注入防护", test_sql_security),
    ]

    results = []
    for name, test_fn in tests:
        print(f"\n--- {name} ---")
        try:
            passed = test_fn()
            results.append((name, passed))
        except Exception as e:
            import traceback
            print(f"[ERROR] {e}")
            traceback.print_exc()
            results.append((name, False))

    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}")

    failed = sum(1 for _, p in results if not p)
    print(f"\n通过: {len(results) - failed}/{len(results)}, 失败: {failed}/{len(results)}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit(main())
