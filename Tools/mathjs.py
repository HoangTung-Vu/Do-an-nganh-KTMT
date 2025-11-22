import requests
import json
import logging

logging.basicConfig(level=logging.INFO)

class MathjsService:
    BASE_URL = "https://api.mathjs.org/v4/"

    def __init__(self):
        self.session = requests.Session()

    def evaluate_get(self, expression: str, precision: int = None):
        params = {"expr": expression}
        if precision is not None:
            params["precision"] = precision
        try:
            response = self.session.get(self.BASE_URL, params=params)
            response.raise_for_status()
            return {"result": response.text.strip(), "error": None}
        except requests.exceptions.RequestException as e:
            logging.error(f"GET error: {e}")
            return {"result": None, "error": str(e)}

    def evaluate_post(self, expressions, precision: int = None):
        if isinstance(expressions, (str, list)):
            payload = {"expr": expressions}
        else:
            raise ValueError("Expressions must be a string or list of strings.")
        if precision is not None:
            payload["precision"] = precision
        try:
            response = self.session.post(
                self.BASE_URL,
                headers={"Content-Type": "application/json"},
                data=json.dumps(payload),
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"POST error: {e}")
            return {"result": None, "error": str(e)}
