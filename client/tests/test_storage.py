import json
import os
import tempfile
import unittest

from core.storage import default_settings, load_settings


class StorageTests(unittest.TestCase):
    def test_uses_environment_override_for_settings_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = os.path.join(tmpdir, "custom-settings.json")
            original = os.environ.get("GAME_HUB_SETTINGS_FILE")
            os.environ["GAME_HUB_SETTINGS_FILE"] = settings_path
            try:
                loaded = load_settings()
                self.assertEqual(loaded["player_name"], default_settings()["player_name"])
                self.assertTrue(os.path.exists(settings_path))

                with open(settings_path, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
                self.assertIn("saved_servers", data)
            finally:
                if original is None:
                    os.environ.pop("GAME_HUB_SETTINGS_FILE", None)
                else:
                    os.environ["GAME_HUB_SETTINGS_FILE"] = original


if __name__ == "__main__":
    unittest.main()
