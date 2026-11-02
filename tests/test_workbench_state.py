from __future__ import annotations

import unittest

from python_image_studio.workbench import _apply_queued_stage_view


class WorkbenchStateTest(unittest.TestCase):
    def test_queued_stage_view_is_applied_before_widget_creation(self):
        state = {
            "stage_view": "原始影像",
            "_next_stage_view": "人臉結果",
        }

        _apply_queued_stage_view(state)

        self.assertEqual(state["stage_view"], "人臉結果")
        self.assertNotIn("_next_stage_view", state)

    def test_missing_queued_view_keeps_current_selection(self):
        state = {"stage_view": "色彩通道"}

        _apply_queued_stage_view(state)

        self.assertEqual(state["stage_view"], "色彩通道")


if __name__ == "__main__":
    unittest.main()
