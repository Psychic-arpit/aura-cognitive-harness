"""
tests/test_fastpath.py - Unit Tests for Semantic Router & Fast-Path Engine
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
from aura.agent.router import ROUTER

def test_instant_math():
    tests = [
        ("what is 15% of 850", "127.5"),
        ("2 + 2", "4"),
        ("100 * 4.5", "450"),
        ("calc 2^8", "256")
    ]
    for expr, expected in tests:
        t0 = time.perf_counter()
        intent = ROUTER.route(expr)
        elapsed_us = (time.perf_counter() - t0) * 1_000_000
        assert intent.type == "math_eval", f"Expected math_eval for {expr}, got {intent.type}"
        assert intent.target == expected, f"Expected {expected} for {expr}, got {intent.target}"
        print(f"  [PASS] Math: '{expr}' -> {intent.target} in {elapsed_us:.1f}us")

def test_turbo_nav():
    tests = [
        ("open instagram and search ISWF video", "https://www.instagram.com/explore/search/keyword/?q=ISWF%20video"),
        ("search leetcode two sum", "https://leetcode.com/problemset/?search=two%20sum"),
        ("github aura agent", "https://github.com/search?q=aura%20agent"),
        ("reddit local llm", "https://www.reddit.com/search/?q=local%20llm")
    ]
    for query, expected_url in tests:
        t0 = time.perf_counter()
        intent = ROUTER.route(query)
        elapsed_us = (time.perf_counter() - t0) * 1_000_000
        assert intent.type == "turbo_nav", f"Expected turbo_nav for {query}, got {intent.type}"
        assert intent.target == expected_url, f"Expected {expected_url}, got {intent.target}"
        print(f"  [PASS] Turbo: '{query}' -> {intent.target[:40]}... in {elapsed_us:.1f}us")

def test_compound_goal_detection():
    query = "click the submit button and then type hello world"
    intent = ROUTER.route(query)
    assert intent.type == "autonomous_goal", f"Expected autonomous_goal, got {intent.type}"
    print(f"  [PASS] Compound Goal: '{query}' -> {intent.type}")

def test_new_execution_routes():
    # Shell execution
    i_shell = ROUTER.route("> git status")
    assert i_shell.type == "shell_exec" and i_shell.target == "git status"
    print("  [PASS] Shell Route: '> git status' -> shell_exec")

    # TagRush QA
    i_tr = ROUTER.route("test tagrush")
    assert i_tr.type == "tagrush_qa"
    print("  [PASS] TagRush Route: 'test tagrush' -> tagrush_qa")

    # Paint Draw
    i_paint = ROUTER.route("draw rectangle in paint")
    assert i_paint.type == "paint_draw"
    print("  [PASS] Paint Route: 'draw rectangle in paint' -> paint_draw")

    # Clean Temp
    i_clean = ROUTER.route("clean temp")
    assert i_clean.type == "clean_temp"
    print("  [PASS] Clean Route: 'clean temp' -> clean_temp")

    # App Aliases
    i_calc = ROUTER.route("calc")
    assert i_calc.type == "app_launch" and i_calc.target == "calc"
    print("  [PASS] Alias Route: 'calc' -> app_launch")

if __name__ == "__main__":
    print("Running Fast-Path & Semantic Router Tests...")
    test_instant_math()
    test_turbo_nav()
    test_compound_goal_detection()
    test_new_execution_routes()
    print("ALL FAST-PATH TESTS PASSED [100%]\n")
