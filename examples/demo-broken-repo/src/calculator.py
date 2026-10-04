"""Demo broken repo — a simple calculator with a bug."""


def add(a, b):
    return a - b  # BUG: should be a + b


def multiply(a, b):
    return a * b


def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
