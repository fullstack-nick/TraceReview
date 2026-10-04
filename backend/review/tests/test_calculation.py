import math
import unittest
from review.calculation import analyze_trace
from review.csv_input import parse_csv
from review.exceptions import DomainError

TRIANGLE = [[0, 0], [1, 2], [2, 0]]


class CalculationTests(unittest.TestCase):
    def test_hand_worked_examples(self):
        cases = [(TRIANGLE, .5, 1.5, 2, 1.5, 75), (TRIANGLE, 0, 2, 2, 2, 100),
                 (TRIANGLE, .25, .75, 2, .5, 25),
                 ([[0, 0], [1, 2], [3, 2], [4, 0]], .5, 3.5, 6, 5.5, 550 / 6),
                 ([[0, 1], [2, 3]], .5, 1.5, 4, 2, 50),
                 ([[0, 0], [1, 0], [2, 2]], 0, .5, 1, 0, 0)]
        for pts, a, b, total, selected, fraction in cases:
            with self.subTest(a=a, b=b, points=pts):
                result = analyze_trace(pts, a, b)
                for actual, expected in [(result.total_area, total), (result.selected_area, selected), (result.area_fraction_percent, fraction)]:
                    self.assertTrue(math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12))

    def test_invalid_bounds(self):
        for a, b in [(0, 0), (2, 1), (-1, 1), (0, 3), (float("nan"), 1), (0, float("inf")), (True, 2)]:
            with self.subTest(a=a, b=b), self.assertRaises(DomainError):
                analyze_trace(TRIANGLE, a, b)

    def test_numeric_range(self):
        for pts in [[[0, 0], [1, 0]], [[0, 1e308], [1e308, 1e308]], [[-1e308, 1], [1e308, 1]]]:
            with self.subTest(points=pts), self.assertRaises(DomainError):
                analyze_trace(pts, pts[0][0], pts[-1][0])

    def test_tiny_positive_area(self):
        result = analyze_trace([[0, 1e-200], [1, 1e-200]], .25, .75)
        self.assertTrue(math.isclose(result.total_area, 1e-200, rel_tol=1e-12))
        self.assertEqual(result.area_fraction_percent, 50)


class CsvTests(unittest.TestCase):
    def test_utf8_bom_crlf_and_spacing(self):
        source = b'\xef\xbb\xbftime_min,signal_au\r\n-1, 0\r\n0,2e0\r\n1,0\r\n'
        points, result = parse_csv(source)
        self.assertEqual(points, [[-1., 0.], [0., 2.], [1., 0.]])
        self.assertEqual(result.total_area, 2)

    def test_invalid_inputs(self):
        cases = [b'', b'time_min,signal_au\n0,1', b'signal_au,time_min\n0,1\n1,1',
                 b'time_min,signal_au,x\n0,1,0\n1,1,0', b'time_min,signal_au\n0,1\n0,2',
                 b'time_min,signal_au\n1,1\n0,2', b'time_min,signal_au\n0,-1\n1,2',
                 b'time_min,signal_au\n0,NaN\n1,2', b'time_min,signal_au\n0,Infinity\n1,2',
                 b'time_min,signal_au\n0,\n1,2', b'time_min,signal_au\n0,1_0\n1,2',
                 b'time_min,signal_au\n0,1\n\n1,2', b'time_min,signal_au\n0,1\n1,2\n\n',
                 b'time_min,signal_au\n0,1e-9999\n1,2', b'time_min,signal_au\n0,1e9999\n1,2',
                 b'time_min,signal_au\n0,1\n1,\xff', b'time_min,signal_au\n"0\n",1\n1,2',
                 b'time_min,signal_au\n9007199254740992,1\n9007199254740993,1',
                 b'time_min,signal_au\n0,1\n1,' + b'2'*129,
                 b'time_min,signal_au\n0,"1\n1,2']
        for source in cases:
            with self.subTest(source=source[:80]), self.assertRaises(DomainError):
                parse_csv(source)

    def test_error_location(self):
        with self.assertRaises(DomainError) as caught:
            parse_csv(b'time_min,signal_au\n0,0\n1,2\n1,1\n')
        self.assertEqual(caught.exception.location, {"line": 4, "column": "time_min"})

    def test_point_and_byte_limits(self):
        for count in (2, 2000):
            source = ('time_min,signal_au\n' + '\n'.join(f'{i},1' for i in range(count))).encode()
            self.assertEqual(len(parse_csv(source)[0]), count)
        with self.assertRaises(DomainError):
            parse_csv(('time_min,signal_au\n' + '\n'.join(f'{i},1' for i in range(2001))).encode())
        with self.assertRaises(DomainError) as caught:
            parse_csv(b' ' * 262145)
        self.assertEqual(caught.exception.status, 413)

    def test_exact_file_limit_is_accepted_without_rewriting(self):
        rows = [[str(i).ljust(60), '1'.ljust(68)] for i in range(2000)]
        remaining = 262144 - len(('time_min,signal_au\n' + ''.join(','.join(row) + '\n' for row in rows)).encode())
        for row in rows:
            extra = min(60, remaining)
            row[1] += ' ' * extra
            remaining -= extra
        source = ('time_min,signal_au\n' + ''.join(','.join(row) + '\n' for row in rows)).encode()
        self.assertEqual(len(source), 262144)
        self.assertEqual(len(parse_csv(source)[0]), 2000)
        with self.assertRaises(DomainError) as caught:
            parse_csv(source + b' ')
        self.assertEqual(caught.exception.status, 413)
