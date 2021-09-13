#  This file is part of Pynguin.
#
#  SPDX-FileCopyrightText: 2019–2021 Pynguin Contributors
#
#  SPDX-License-Identifier: LGPL-3.0-or-later
#


class CalculatorResult:
    def __init__(self, op: str, result: float):
        self.last_op = op
        self.last_result = result

    def __repr__(self) -> str:
        return f"{self.last_op.upper()}: {self.last_result}"

    def __eq__(self, other) -> bool:
        if isinstance(other, CalculatorResult):
            return (
                self.last_op == other.last_op and self.last_result == other.last_result
            )
        return False


class Calculator:
    amount_calculation = 0
    results = []

    class Decorators:
        @staticmethod
        def calc_decorator(func):
            def inner(self, a, b):
                result = func(self, a, b)
                cr = CalculatorResult(func.__name__, result)
                Calculator.results.append(cr)
                Calculator.amount_calculation += 1
                return result

            return inner

    @Decorators.calc_decorator
    def add(self, a: float, b: float) -> float:
        return a + b

    @Decorators.calc_decorator
    def sub(self, a: float, b: float) -> float:
        return a - b

    @Decorators.calc_decorator
    def mult(self, a: float, b: float) -> float:
        return a * b

    @Decorators.calc_decorator
    def div(self, a: float, b: float) -> float:
        return a / b

    def output_results(self) -> str:
        return "".join([str(x) + "\n" for x in self.results]).rstrip()
