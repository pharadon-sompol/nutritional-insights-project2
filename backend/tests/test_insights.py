from pathlib import Path
import sys
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from insights import build_dashboard_payload, clean_data  # noqa: E402


class InsightsTests(unittest.TestCase):
    def setUp(self):
        self.data = pd.DataFrame(
            {
                "Diet_type": ["vegan", "vegan", "keto"],
                "Recipe_name": ["A", "B", "C"],
                "Cuisine_type": ["thai", "thai", "american"],
                "Protein(g)": [10, None, 30],
                "Carbs(g)": [20, 40, 5],
                "Fat(g)": [4, 8, 20],
            }
        )

    def test_clean_data_fills_missing_numeric_values(self):
        cleaned = clean_data(self.data)
        self.assertFalse(cleaned["Protein(g)"].isna().any())

    def test_payload_contains_required_dashboard_sections(self):
        payload = build_dashboard_payload(self.data, source="test")
        for key in [
            "averageMacronutrients",
            "scatterPoints",
            "correlationMatrix",
            "recipeDistribution",
            "metadata",
        ]:
            self.assertIn(key, payload)
        self.assertEqual(payload["summary"]["recipeCount"], 3)

    def test_diet_filter_limits_results(self):
        payload = build_dashboard_payload(self.data, diet_filter="vegan")
        self.assertEqual(payload["selectedDiet"], "vegan")
        self.assertEqual(payload["summary"]["recipeCount"], 2)

    def test_unknown_diet_is_rejected(self):
        with self.assertRaises(ValueError):
            build_dashboard_payload(self.data, diet_filter="not-a-diet")


if __name__ == "__main__":
    unittest.main()
