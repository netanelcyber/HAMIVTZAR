"""Tests for the WASM reverse-engineering challenge (build + disassemble).

Pure Python, no external WASM runtime needed: a tiny stack-machine
evaluator here interprets the disassembled opcode list directly, so the
module's *semantics* are checked the same way inspect_wasm.py's output
would be read by hand, not by trusting a black-box engine.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pacs_iso27799_audit.lab.inspect_wasm import format_module, parse_module
from pacs_iso27799_audit.lab.wasm_challenge import build_access_check_module


def _eval_i32_function(opcodes, arg):
    """Tiny stack evaluator for the numeric opcode subset inspect_wasm.py emits."""
    stack = []
    for op in opcodes:
        parts = op.split()
        mnemonic = parts[0]
        if mnemonic == "local.get":
            stack.append(arg)
        elif mnemonic == "i32.const":
            stack.append(int(parts[1]))
        elif mnemonic == "i32.mul":
            b, a = stack.pop(), stack.pop()
            stack.append(a * b)
        elif mnemonic == "i32.add":
            b, a = stack.pop(), stack.pop()
            stack.append(a + b)
        elif mnemonic == "i32.rem_u":
            b, a = stack.pop(), stack.pop()
            stack.append(a % b)
        elif mnemonic == "i32.eq":
            b, a = stack.pop(), stack.pop()
            stack.append(1 if a == b else 0)
        elif mnemonic == "end":
            break
        else:
            raise AssertionError(f"evaluator doesn't handle opcode: {op}")
    return stack[-1]


class BuildModuleTests(unittest.TestCase):
    def test_magic_and_version(self):
        data = build_access_check_module()
        self.assertEqual(data[:4], b"\x00asm")
        self.assertEqual(data[4:8], b"\x01\x00\x00\x00")

    def test_module_is_nonempty_bytes(self):
        data = build_access_check_module()
        self.assertIsInstance(data, bytes)
        self.assertGreater(len(data), 8)


class ParseAndDisassembleTests(unittest.TestCase):
    def setUp(self):
        self.data = build_access_check_module()
        self.mod = parse_module(self.data)

    def test_single_i32_to_i32_type(self):
        self.assertEqual(len(self.mod.types), 1)
        params, results = self.mod.types[0]
        self.assertEqual(params, [0x7F])
        self.assertEqual(results, [0x7F])

    def test_exports_check_code(self):
        self.assertEqual(len(self.mod.exports), 1)
        name, kind, idx = self.mod.exports[0]
        self.assertEqual(name, "check_code")
        self.assertEqual(kind, 0)  # func
        self.assertEqual(idx, 0)

    def test_disassembly_is_readable_and_ends_properly(self):
        self.assertEqual(len(self.mod.code), 1)
        opcodes = self.mod.code[0]
        self.assertEqual(opcodes[0], "local.get 0")
        self.assertEqual(opcodes[-1], "end")
        for op in opcodes:
            self.assertNotIn("unknown opcode", op)

    def test_format_module_mentions_export_name(self):
        text = format_module(self.mod)
        self.assertIn("check_code", text)
        self.assertIn("i32.rem_u", text)


class SemanticsTests(unittest.TestCase):
    """Confirms the disassembled opcodes actually compute what they appear
    to -- i.e. that reading the disassembly (not this source file) is
    sufficient to solve the exercise."""

    def setUp(self):
        mod = parse_module(build_access_check_module())
        self.opcodes = mod.code[0]

    def test_exactly_one_solution_in_the_3_digit_code_space(self):
        solutions = [i for i in range(1000) if _eval_i32_function(self.opcodes, i) == 1]
        self.assertEqual(len(solutions), 1)

    def test_known_solution_passes(self):
        solutions = [i for i in range(1000) if _eval_i32_function(self.opcodes, i) == 1]
        solution = solutions[0]
        self.assertEqual(_eval_i32_function(self.opcodes, solution), 1)
        self.assertEqual(_eval_i32_function(self.opcodes, (solution + 1) % 1000), 0)


if __name__ == "__main__":
    unittest.main()
