"""Red-test drill (bootstrap round 17): a planted failing test. Never merged:
its pull request must be blocked by the required "Full gate (Ubuntu)" check."""
import unittest


class Drill(unittest.TestCase):
    def test_planted_failure(self):
        self.assertEqual(1, 2, "planted by the red-test drill")
