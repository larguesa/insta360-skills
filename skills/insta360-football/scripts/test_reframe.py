"""Synthetic motion regressions; no SDK or model calls."""
import copy
import json
from pathlib import Path
import unittest
import numpy as np
from reframe import camera, vfov


class CameraTests(unittest.TestCase):
    def setUp(self):
        self.plan = json.loads((Path(__file__).resolve().parents[1] / 'assets/example-plan.json').read_text())

    def test_geometry(self):
        self.assertAlmostEqual(vfov(90, 1920, 1080), 58.715507, places=5)

    def test_continuous_pan_and_hold(self):
        t, yaw, _ = camera(self.plan)
        self.assertEqual(len(t), 60)
        speed = np.diff(yaw) * 30
        self.assertGreater(min(speed[14:17]), 5)
        self.assertGreater(min(speed[29:32]), 5)
        self.assertTrue(np.allclose(yaw[t >= 1.5], 5))
        self.assertGreaterEqual(min(yaw), -10)
        self.assertLessEqual(max(yaw), 5)

    def test_duplicate_time(self):
        self.plan['keyframes'][1]['t'] = 0
        with self.assertRaises(ValueError):
            camera(self.plan)

    def test_invalid_angle(self):
        for bad in [float('nan'), 50]:
            p = copy.deepcopy(self.plan)
            p['keyframes'][1]['yaw'] = bad
            with self.assertRaises(ValueError):
                camera(p)

    def test_speed_limit(self):
        self.plan['max_speed'] = 1
        with self.assertRaises(ValueError):
            camera(self.plan)

    def test_frame_alignment(self):
        self.plan['duration'] = 2.001
        with self.assertRaises(ValueError):
            camera(self.plan)


if __name__ == '__main__':
    unittest.main()
