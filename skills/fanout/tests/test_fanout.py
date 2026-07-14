import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import fanout as fp


class FanoutPlanTests(unittest.TestCase):
    def test_cluster_items_groups_shared_files(self):
        items = [
            {"name": "A", "files": ["x.py"]},
            {"name": "B", "files": ["x.py", "y.py"]},   # shares x.py with A
            {"name": "C", "files": ["z.py"]},           # disjoint
        ]
        clusters = sorted(sorted(c) for c in fp.cluster_items(items))
        self.assertEqual(clusters, [["A", "B"], ["C"]])

    def test_cluster_items_groups_contract_group(self):
        # File-disjoint but declared as halves of one contract -> serialize together.
        items = [
            {"name": "svc", "files": ["services/billing.py"], "contract_group": "remit-split"},
            {"name": "view", "files": ["views_billing.py"], "contract_group": "remit-split"},
            {"name": "other", "files": ["unrelated.tsx"]},
        ]
        clusters = sorted(sorted(c) for c in fp.cluster_items(items))
        self.assertEqual(clusters, [["other"], ["svc", "view"]])

    def test_paths_match_suffix_boundary(self):
        self.assertTrue(fp._paths_match("backend/app/services/billing.py", "app/services/billing.py"))
        self.assertTrue(fp._paths_match("a/b.py", "b.py"))
        self.assertTrue(fp._paths_match("x.py", "x.py"))
        self.assertFalse(fp._paths_match("xapp/s.py", "app/s.py"))  # not a /-boundary suffix
        self.assertFalse(fp._paths_match("a.py", "b.py"))

    def test_coupling_review_import_adjacent_defaults_parallel(self):
        items = [{"name": "A", "files": ["pkg/a.py"]}, {"name": "B", "files": ["pkg/b.py"]}]
        adj = {"pkg/a.py": {"pkg/b.py"}, "pkg/b.py": {"pkg/a.py"}}
        out = fp.coupling_review(items, adj, [])
        self.assertEqual(out[0]["pair"], ["A", "B"])
        self.assertIn("import-adjacent", out[0]["signals"])
        self.assertEqual(out[0]["default"], "parallel")

    def test_coupling_review_shared_risk_marker_defaults_serialize(self):
        items = [{"name": "A", "files": ["ledger_cents.py"]}, {"name": "B", "files": ["remit_cents.py"]}]
        out = fp.coupling_review(items, {}, ["_cents"])
        self.assertEqual(out[0]["default"], "serialize")
        self.assertIn("shared-risk-marker:_cents", out[0]["signals"])

    def test_coupling_review_omits_signal_free_and_co_clustered(self):
        items = [
            {"name": "A", "files": ["a.tsx"]},
            {"name": "B", "files": ["b.tsx"]},                              # A/B signal-free
            {"name": "C", "files": ["c.py"], "contract_group": "g"},
            {"name": "D", "files": ["d.py"], "contract_group": "g"},        # C/D already serialized
        ]
        out = fp.coupling_review(items, {}, [])
        self.assertEqual(out, [])

    def test_tier_for_uses_supplied_markers(self):
        self.assertEqual(fp.tier_for(["x/billing.py"], ["billing.py"]), "top")
        self.assertEqual(fp.tier_for(["app/api/c/route.ts"], ["/route.ts"]), "top")
        self.assertEqual(fp.tier_for(["features/cell.tsx"], ["billing.py"]), "cheap")
        self.assertEqual(fp.tier_for(["anything.py"], []), "cheap")

    def test_build_file_coupling_ignores_same_file_edges(self):
        nodes = {"n1": {"source_file": "a.py"}, "n2": {"source_file": "a.py"},
                 "n3": {"source_file": "b.py"}}
        links = [{"source": "n1", "target": "n2"}, {"source": "n1", "target": "n3"}]
        adj = fp.build_file_coupling(nodes, links)
        self.assertEqual(adj["a.py"], {"b.py"})
        self.assertEqual(adj["b.py"], {"a.py"})


class WavesTests(unittest.TestCase):
    """Waves: ONE GLOBAL schedule over all items. Items in one wave are
    mutually conflict-free (no shared file, no shared contract_group) AND have
    no `after` dependency between them -> run concurrently; each wave starts
    from the integrated result of the waves before it. Clusters stay the
    merge-safety grouping (MSP boundaries); waves are the execution order."""

    def _waves(self, items):
        adj = fp._conflict_adjacency(items)
        order = {it["name"]: i for i, it in enumerate(items)}
        return fp.global_waves(items, adj, order)

    def test_chain_hub_goes_first_then_leaves_fan_out(self):
        # A-B share f1, B-C share f2: B is the hub -> wave 1 = [B], then A, C.
        items = [
            {"name": "A", "files": ["f1.py"]},
            {"name": "B", "files": ["f1.py", "f2.py"]},
            {"name": "C", "files": ["f2.py"]},
        ]
        self.assertEqual(self._waves(items), [["B"], ["A", "C"]])

    def test_clique_degenerates_to_singleton_waves_in_input_order(self):
        items = [
            {"name": "A", "files": ["models.py"]},
            {"name": "B", "files": ["models.py"]},
            {"name": "C", "files": ["models.py"]},
        ]
        self.assertEqual(self._waves(items), [["A"], ["B"], ["C"]])

    def test_contract_group_conflicts_without_shared_files(self):
        items = [
            {"name": "svc", "files": ["services/x.py"], "contract_group": "g"},
            {"name": "view", "files": ["views/y.py"], "contract_group": "g"},
        ]
        self.assertEqual(self._waves(items), [["svc"], ["view"]])

    def test_after_orders_consumers_behind_producer_but_parallel_together(self):
        # The S4 case: BE produces an API field; FE1 + FE2 consume it. All
        # file-disjoint. contract_group would force BE->FE1->FE2 fully serial;
        # `after` must yield [[BE], [FE1, FE2]] - consumers fan out together.
        items = [
            {"name": "BE", "files": ["api/views.py"]},
            {"name": "FE1", "files": ["app/a.tsx"], "after": ["BE"]},
            {"name": "FE2", "files": ["app/b.tsx"], "after": ["BE"]},
        ]
        self.assertEqual(self._waves(items), [["BE"], ["FE1", "FE2"]])

    def test_after_composes_with_conflicts(self):
        # D after C, and D shares a file with E: D must land after C AND never
        # share a wave with E.
        items = [
            {"name": "C", "files": ["c.py"]},
            {"name": "D", "files": ["shared.py"], "after": ["C"]},
            {"name": "E", "files": ["shared.py"]},
        ]
        waves = self._waves(items)
        wave_of = {n: i for i, w in enumerate(waves) for n in w}
        self.assertGreater(wave_of["D"], wave_of["C"])
        self.assertNotEqual(wave_of["D"], wave_of["E"])

    def test_after_unknown_name_raises(self):
        items = [{"name": "A", "files": ["a.py"], "after": ["nope"]}]
        with self.assertRaises(ValueError):
            self._waves(items)

    def test_after_cycle_raises(self):
        items = [
            {"name": "A", "files": ["a.py"], "after": ["B"]},
            {"name": "B", "files": ["b.py"], "after": ["A"]},
        ]
        with self.assertRaises(ValueError):
            self._waves(items)

    def test_plan_emits_global_waves_and_clusters(self):
        import tempfile
        items = [
            {"name": "A", "files": ["f1.py"]},
            {"name": "B", "files": ["f1.py", "f2.py"]},
            {"name": "C", "files": ["f2.py"]},
            {"name": "solo", "files": ["elsewhere.tsx"]},
        ]
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as g:
            json.dump({"nodes": [], "links": []}, g)
            graph_path = g.name
        try:
            out = fp.plan(items, graph_path, [])
        finally:
            os.unlink(graph_path)
        self.assertIn("waves", out)
        flat = [n for w in out["waves"] for n in w]
        self.assertEqual(sorted(flat), sorted(it["name"] for it in items))
        # solo has no conflicts -> rides the first wave alongside the hub
        self.assertIn("solo", out["waves"][0])
        # no wave contains two items that share a file
        files = {it["name"]: set(it["files"]) for it in items}
        for wave in out["waves"]:
            for i in range(len(wave)):
                for j in range(i + 1, len(wave)):
                    self.assertFalse(files[wave[i]] & files[wave[j]],
                                     f"{wave[i]} and {wave[j]} share a file in one wave")

    def test_plan_works_without_graph_and_drops_decided_pairs(self):
        # --graph is optional: clustering/waves/tiers still compute; and a
        # pair with a declared `after` path is a DECIDED order, so it must
        # not reappear in coupling_review.
        items = [
            {"name": "BE", "files": ["ledger_api.py"]},
            {"name": "FE", "files": ["ledger_ui.tsx"], "after": ["BE"]},
        ]
        out = fp.plan(items, None, ["ledger"])
        self.assertEqual(out["waves"], [["BE"], ["FE"]])
        pairs = [set(p["pair"]) for p in out["coupling_review"]]
        self.assertNotIn({"BE", "FE"}, pairs)


if __name__ == "__main__":
    unittest.main()
