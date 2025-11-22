import pytest
from mathjs import MathjsService  # import class từ file chính

@pytest.fixture(scope="module")
def math_service():
    """Khởi tạo service dùng chung cho các test."""
    return MathjsService()

# -----------------------------
# 🔹 TEST GET REQUESTS
# -----------------------------

def test_evaluate_get_simple(math_service):
    expr = "2+3*sqrt(4)"
    result = math_service.evaluate_get(expr)
    assert result["error"] is None
    assert result["result"] == "8"  # 2 + 3*2 = 8

def test_evaluate_get_with_precision(math_service):
    expr = "2/3"
    result = math_service.evaluate_get(expr, precision=3)
    assert result["error"] is None
    # Kết quả gần đúng vì precision chỉ ảnh hưởng định dạng
    assert result["result"].startswith("0.667")

def test_evaluate_get_invalid_expr(math_service):
    expr = "invalid expression!"
    result = math_service.evaluate_get(expr)
    assert result["error"] is not None
    assert "400" in result["error"] or "Bad Request" in result["error"]


# -----------------------------
# 🔹 TEST POST REQUESTS
# -----------------------------

def test_evaluate_post_single(math_service):
    expr = "2+3"
    result = math_service.evaluate_post(expr)
    assert "result" in result
    assert result["result"] == "5"
    assert result["error"] is None

def test_evaluate_post_multiple(math_service):
    exprs = ["a = 1.2 * (2 + 4.5)", "a / 2", "5.08 cm in inch"]
    result = math_service.evaluate_post(exprs, precision=14)
    assert isinstance(result["result"], list)
    assert result["error"] is None
    assert len(result["result"]) == len(exprs)

def test_evaluate_post_invalid_expr(math_service):
    expr = ["invalid post expression!"]
    result = math_service.evaluate_post(expr)
    # API trả về {"result": None, "error": "..."} hoặc chứa lỗi trong "result"
    assert "result" in result
    assert "error" in result

def test_evaluate_post_wrong_type(math_service):
    with pytest.raises(ValueError):
        math_service.evaluate_post(12345)  # Không phải str hoặc list

# -----------------------------
# 🔹 PERFORMANCE / SANITY TEST
# -----------------------------

def test_multiple_requests(math_service):
    """Kiểm tra nhiều request liên tiếp không lỗi"""
    expressions = [f"{i}+{i}" for i in range(5)]
    for expr in expressions:
        res = math_service.evaluate_get(expr)
        assert res["error"] is None
        assert res["result"] == str(eval(expr))
