import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location("distribution", Path(__file__).resolve().parents[1] / "scripts/verify_distribution.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class DistributionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.a, self.b = self.root / "a", self.root / "b"
        for root in (self.a, self.b):
            (root / "reports").mkdir(parents=True)
            (root / "shared.txt").write_text("shared", encoding="utf-8")
            (root / "README.md").write_text(root.name, encoding="utf-8")
            self.write_contract(root)

    def write_contract(self, root, **changes):
        data = {"schema_version": 1, "shared_paths": ["shared.txt"], "variant_paths": ["README.md"]}
        data.update(changes)
        (root / MODULE.CONTRACT).write_text(json.dumps(data), encoding="utf-8")

    def test_self_check_is_not_peer_check(self):
        result = MODULE.verify(self.a)
        self.assertTrue(result["pass"])
        self.assertFalse(result["peer_checked"])
        self.assertEqual(result["peer_files_compared"], 0)

    def test_equal_shared_different_readmes(self):
        self.assertTrue(MODULE.verify(self.a, self.b)["pass"])

    def test_changed_shared_fails(self):
        (self.b / "shared.txt").write_text("changed")
        self.assertFalse(MODULE.verify(self.a, self.b)["pass"])

    def test_missing_shared_fails(self):
        (self.a / "shared.txt").unlink()
        self.assertFalse(MODULE.verify(self.a)["pass"])

    def test_unrelated_private_extra_not_read(self):
        (self.b / "extra-private.txt").write_text("not part of contract")
        self.assertTrue(MODULE.verify(self.a, self.b)["pass"])

    def test_same_directory_is_not_peer(self):
        self.assertFalse(MODULE.verify(self.a, self.a)["pass"])

    def test_different_contract_fails(self):
        self.write_contract(self.b, schema_version=2)
        self.assertFalse(MODULE.verify(self.a, self.b)["pass"])

    def test_parent_traversal_fails(self):
        self.write_contract(self.a, shared_paths=["../secret"])
        self.assertFalse(MODULE.verify(self.a)["pass"])

    def test_absolute_path_fails(self):
        self.write_contract(self.a, shared_paths=[str(self.b / "shared.txt")])
        self.assertFalse(MODULE.verify(self.a)["pass"])

    def test_symlink_fails(self):
        (self.a / "shared.txt").unlink()
        (self.a / "shared.txt").symlink_to(self.b / "shared.txt")
        self.assertFalse(MODULE.verify(self.a)["pass"])

    def test_duplicate_paths_fail(self):
        self.write_contract(self.a, shared_paths=["shared.txt", "shared.txt"])
        self.assertFalse(MODULE.verify(self.a)["pass"])

    def test_overlapping_paths_fail(self):
        self.write_contract(self.a, variant_paths=["shared.txt"])
        self.assertFalse(MODULE.verify(self.a)["pass"])

    def test_invalid_json_fails(self):
        (self.a / MODULE.CONTRACT).write_text("not json")
        self.assertFalse(MODULE.verify(self.a)["pass"])

    def test_invalid_path_type_fails(self):
        self.write_contract(self.a, shared_paths=[5])
        self.assertFalse(MODULE.verify(self.a)["pass"])


if __name__ == "__main__":
    unittest.main()
