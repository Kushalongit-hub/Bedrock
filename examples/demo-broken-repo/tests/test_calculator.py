"""Tests for calculator — deliberately failing."""

from src.calculator import add, multiply, divide


def test_add():
    assert add(2, 3) == 5  # FAILS: returns -1


def test_multiply():
    assert multiply(2, 3) == 6


def test_divide():
    assert divide(6, 3) == 2
