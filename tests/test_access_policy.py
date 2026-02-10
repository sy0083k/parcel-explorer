import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read_module_ast(relative_path: str) -> ast.Module:
    source = (ROOT / relative_path).read_text(encoding="utf-8")
    return ast.parse(source)


def _find_route_decorator_call(func_def: ast.AsyncFunctionDef, route_path: str) -> ast.Call | None:
    for decorator in func_def.decorator_list:
        if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
            if decorator.func.attr in {"get", "post"}:
                if decorator.args and isinstance(decorator.args[0], ast.Constant):
                    if decorator.args[0].value == route_path:
                        return decorator
    return None


def _dependencies_kwarg(call: ast.Call):
    for kw in call.keywords:
        if kw.arg == "dependencies" and isinstance(kw.value, ast.List):
            return kw.value
    return None


def _dependency_names(dep_list: ast.List) -> set[str]:
    names: set[str] = set()
    for elt in dep_list.elts:
        if isinstance(elt, ast.Call) and isinstance(elt.func, ast.Name) and elt.func.id == "Depends":
            if elt.args and isinstance(elt.args[0], ast.Name):
                names.add(elt.args[0].id)
    return names


def test_login_post_internal_network_guard():
    module = _read_module_ast("app/routers/auth.py")
    funcs = [node for node in module.body if isinstance(node, ast.AsyncFunctionDef)]
    login_func = next(func for func in funcs if func.name == "login")
    decorator = _find_route_decorator_call(login_func, "/login")
    assert decorator is not None

    deps = _dependencies_kwarg(decorator)
    assert deps is not None
    assert "check_internal_network" in _dependency_names(deps)


def test_admin_upload_requires_internal_and_authentication():
    module = _read_module_ast("app/routers/admin.py")
    funcs = [node for node in module.body if isinstance(node, ast.AsyncFunctionDef)]
    upload_func = next(func for func in funcs if func.name == "upload_excel")
    decorator = _find_route_decorator_call(upload_func, "/upload")
    assert decorator is not None

    deps = _dependencies_kwarg(decorator)
    assert deps is not None
    dependency_names = _dependency_names(deps)
    assert "check_internal_network" in dependency_names
    assert "require_authenticated" in dependency_names


def test_admin_root_redirects_when_unauthenticated_and_keeps_internal_guard():
    module = _read_module_ast("app/routers/admin.py")
    funcs = [node for node in module.body if isinstance(node, ast.AsyncFunctionDef)]
    admin_root = next(func for func in funcs if func.name == "admin_root")

    decorator = _find_route_decorator_call(admin_root, "/")
    assert decorator is not None

    deps = _dependencies_kwarg(decorator)
    assert deps is not None
    dependency_names = _dependency_names(deps)
    assert "check_internal_network" in dependency_names
    assert "require_authenticated" not in dependency_names

    has_redirect_response = False
    for node in ast.walk(admin_root):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "RedirectResponse":
            has_redirect_response = True
            break

    assert has_redirect_response
