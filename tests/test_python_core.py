from __future__ import annotations

import math
import unittest

import numpy as np

from python_image_studio.core import (
    apply_convolution,
    channel_plane,
    histogram,
    psnr,
    validate_kernel,
)


class PythonImageAlgorithmsTest(unittest.TestCase):
    def setUp(self):
        self.image = np.array(
            [
                [[255, 0, 0], [0, 255, 0]],
                [[0, 0, 255], [255, 255, 255]],
            ],
            dtype=np.uint8,
        )

    def test_bt601_y_channel(self):
        y_channel = channel_plane(self.image, "Y")
        self.assertEqual(int(y_channel[0, 0]), 76)
        self.assertEqual(int(y_channel[0, 1]), 150)

    def test_bt601_uv_channels(self):
        u_channel = channel_plane(self.image, "U")
        v_channel = channel_plane(self.image, "V")
        self.assertEqual(int(u_channel[0, 0]), 85)
        self.assertEqual(int(v_channel[0, 0]), 255)
        self.assertEqual(int(u_channel[0, 1]), 44)
        self.assertEqual(int(v_channel[0, 1]), 21)

    def test_histogram_counts_all_pixels(self):
        bins = histogram(self.image, "R")
        self.assertEqual(int(bins.sum()), 4)
        self.assertEqual(int(bins[0]), 2)
        self.assertEqual(int(bins[255]), 2)

    def test_identity_kernel_and_infinite_psnr(self):
        spec = validate_kernel([[0, 0, 0], [0, 1, 0], [0, 0, 0]], "權重總和")
        result = apply_convolution(self.image, spec)
        score, mse = psnr(self.image, result)
        np.testing.assert_array_equal(result, self.image)
        self.assertEqual(mse, 0)
        self.assertTrue(math.isinf(score))

    def test_five_by_five_identity_kernel(self):
        weights = np.zeros((5, 5), dtype=float)
        weights[2, 2] = 1
        result = apply_convolution(self.image, validate_kernel(weights, "權重總和"))
        np.testing.assert_array_equal(result, self.image)

    def test_custom_divisor(self):
        spec = validate_kernel(np.ones((3, 3)), "自訂除數", custom_divisor=9)
        result = apply_convolution(self.image, spec)
        self.assertEqual(result.shape, self.image.shape)
        self.assertEqual(spec.divisor, 9)

    def test_zero_sum_normalization_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "不可為 0"):
            validate_kernel([[-1, -1, -1], [-1, 8, -1], [-1, -1, -1]], "權重總和")

    def test_clamp_to_edge_convolution(self):
        spec = validate_kernel([[1, 0, 0], [0, 0, 0], [0, 0, 0]], "不正規化")
        result = apply_convolution(self.image, spec)
        np.testing.assert_array_equal(result[0, 0], self.image[0, 0])


if __name__ == "__main__":
    unittest.main()
