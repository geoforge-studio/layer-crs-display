import unittest

from layer_crs_display.audit_logic import (
    STATUS_DIFFERENT,
    STATUS_MISSING,
    STATUS_OK,
    audit_summary,
    classify_crs,
    matches_filter,
    reprojectable_layer_ids,
)


class AuditLogicTests(unittest.TestCase):
    def test_classification_has_only_three_expected_states(self):
        self.assertEqual(classify_crs(False, False), STATUS_MISSING)
        self.assertEqual(classify_crs(True, True), STATUS_OK)
        self.assertEqual(classify_crs(True, False), STATUS_DIFFERENT)

    def test_summary_counts_layers_crs_and_statuses(self):
        rows = [
            dict(status=STATUS_OK, crs_key="EPSG:32639"),
            dict(status=STATUS_OK, crs_key="EPSG:32639"),
            dict(status=STATUS_DIFFERENT, crs_key="EPSG:4326"),
            dict(status=STATUS_MISSING, crs_key=""),
        ]
        self.assertEqual(
            audit_summary(rows),
            dict(layers=4, crs=2, ok=2, different=1, missing=1),
        )

    def test_filter_does_not_change_rows(self):
        row = dict(status=STATUS_DIFFERENT)
        self.assertTrue(matches_filter(row, "All"))
        self.assertTrue(matches_filter(row, STATUS_DIFFERENT))
        self.assertFalse(matches_filter(row, STATUS_OK))

    def test_only_selected_different_layers_are_sent_to_reproject(self):
        rows = [
            dict(layer_id="ok", status=STATUS_OK),
            dict(layer_id="different-1", status=STATUS_DIFFERENT),
            dict(layer_id="missing", status=STATUS_MISSING),
            dict(layer_id="different-2", status=STATUS_DIFFERENT),
        ]
        self.assertEqual(
            reprojectable_layer_ids(
                rows, {"ok", "different-2", "missing"}
            ),
            ["different-2"],
        )


if __name__ == "__main__":
    unittest.main()
