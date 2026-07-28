import os, json, re, math, random
from agents.base_agent import BaseAgent

class MathAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            "math_agent",
            "Solve mathematical problems, equations, calculate results, and explain math concepts",
        )
        self.capabilities = ["math", "calculate", "solve", "equation", "formula", "arithmetic", "algebra", "geometry"]

    def run(self, task):
        self.add_memory(f"Task: {task}")
        t = task.lower()

        if "prime" in t:
            return self._check_prime(t)
        if "factorial" in t or "factor" in t:
            nums = re.findall(r'\d+', t)
            if nums:
                n = int(nums[0])
                if "factorial" in t:
                    return f"MathAgent: {n}! = {math.factorial(n)}"
                return f"MathAgent: Factors of {n}: {self._factors(n)}"
        if "fibonacci" in t:
            nums = re.findall(r'\d+', t)
            n = int(nums[0]) if nums else 10
            return f"MathAgent: Fibonacci ({n}): {self._fibonacci(n)}"
        if "sqrt" in t or "square root" in t:
            nums = re.findall(r'\d+(?:\.\d+)?', t)
            if nums:
                n = float(nums[0])
                return f"MathAgent: sqrt({n}) = {math.sqrt(n):.6f}"
        if "power" in t or "square" in t or "cube" in t:
            nums = re.findall(r'\d+(?:\.\d+)?', t)
            if len(nums) >= 1:
                n = float(nums[0])
                if "cube" in t:
                    return f"MathAgent: {n}^3 = {n**3:.4f}"
                elif len(nums) >= 2:
                    return f"MathAgent: {nums[0]}^{nums[1]} = {float(nums[0])**float(nums[1]):.4f}"
                return f"MathAgent: {n}^2 = {n**2:.4f}"
        if "gcd" in t or "hcf" in t:
            nums = re.findall(r'\d+', t)
            if len(nums) >= 2:
                return f"MathAgent: GCD({nums[0]}, {nums[1]}) = {math.gcd(int(nums[0]), int(nums[1]))}"
        if "lcm" in t:
            nums = re.findall(r'\d+', t)
            if len(nums) >= 2:
                a, b = int(nums[0]), int(nums[1])
                lcm = a * b // math.gcd(a, b)
                return f"MathAgent: LCM({a}, {b}) = {lcm}"
        if "random" in t or "roll" in t:
            nums = re.findall(r'\d+', t)
            if len(nums) >= 2:
                return f"MathAgent: Random number ({nums[0]}-{nums[1]}): {random.randint(int(nums[0]), int(nums[1]))}"
            return f"MathAgent: Random number (1-100): {random.randint(1, 100)}"
        if "percentage" in t or "percent" in t:
            nums = re.findall(r'\d+(?:\.\d+)?', t)
            if len(nums) >= 2:
                pct = float(nums[0]) * float(nums[1]) / 100
                return f"MathAgent: {nums[0]}% of {nums[1]} = {pct:.2f}"
        expr = self._extract_expression(task)
        if expr:
            try:
                result = self._safe_eval(expr)
                return f"MathAgent: {expr} = {result}"
            except Exception as e:
                return f"MathAgent: Could not evaluate '{expr}': {e}"
        return ("MathAgent: Available operations:\n"
                "  prime <n>, factorial <n>, fibonacci <n>\n"
                "  sqrt <n>, square <n>, cube <n>, power <base> <exp>\n"
                "  gcd <a> <b>, lcm <a> <b>, percentage <p> <n>\n"
                "  random <min> <max>, roll\n"
                "  Or type any math expression like: 2 + 2 * (3 + 4)")

    def _extract_expression(self, task):
        cleaned = re.sub(r'[^0-9+\-*/().%\s]', ' ', task)
        cleaned = re.sub(r'\s+', '', cleaned)
        if cleaned and re.search(r'[+\-*/]', cleaned):
            return cleaned
        return None

    def _safe_eval(self, expr):
        allowed = {'abs': abs, 'round': round, 'max': max, 'min': min,
                   'pow': pow, 'sum': sum, 'int': int, 'float': float,
                   'math': math, 'pi': math.pi, 'e': math.e}
        return eval(expr, {"__builtins__": {}}, allowed)

    def _check_prime(self, task):
        nums = re.findall(r'\d+', task)
        if nums:
            n = int(nums[0])
            if n < 2:
                return f"MathAgent: {n} is not prime"
            for i in range(2, int(math.sqrt(n)) + 1):
                if n % i == 0:
                    return f"MathAgent: {n} is not prime (divisible by {i})"
            return f"MathAgent: {n} is prime!"
        return "MathAgent: Provide a number to check"

    def _factors(self, n):
        factors = []
        for i in range(1, int(math.sqrt(n)) + 1):
            if n % i == 0:
                factors.append(i)
                if i != n // i:
                    factors.append(n // i)
        return sorted(factors)

    def _fibonacci(self, n):
        seq = [0, 1]
        for i in range(2, n):
            seq.append(seq[-1] + seq[-2])
        return seq[:n]
