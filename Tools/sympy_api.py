# sympy_api.py
from fastapi import FastAPI
from pydantic import BaseModel
import sympy as sp

app = FastAPI()

class Expression(BaseModel):
    expr: str

@app.post("/evaluate")
def evaluate_expression(data: Expression):
    x, y, z = sp.symbols('x y z')
    try:
        result = sp.simplify(sp.sympify(data.expr))
        return {"result": str(result)}
    except Exception as e:
        return {"error": str(e)}
