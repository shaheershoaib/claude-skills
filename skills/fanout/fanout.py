"""Plan a parallel subagent fan-out from a graphify graph. Project-agnostic.

cluster_items: items sharing an edited file OR a declared contract_group MUST
serialize (one owner); distinct clusters are file- and contract-disjoint -> safe
to run in parallel (merge-safety unit is the EDITED file, not symbols, not
transitive import-coupling).
coupling_review: for each file-disjoint, NOT-co-clustered PAIR, the soft coupling
signals (import-adjacency, shared risk-marker, and - from trajectory memory - a
recorded regression between the two surfaces) that warrant an explicit
parallelize-vs-serialize verdict from the ORCHESTRATOR before dispatch.
tier_for: RISK tier ('top'/'cheap') from caller-supplied path markers; a surface
with a bad track record in trajectory memory (a revert, a speculative ship, a
caused-regression, or repeated wrong-surface traps) is ALSO forced to 'top',
even with no path-marker match.

Trajectory memory is OPTIONAL and strictly ADDITIVE: with no store, an empty
store, or --no-trajectories, the output is identical to the marker-only plan.
History only ever ADDS caution - it bumps a tier UP and adds serialize hints; it
never relaxes a tier or removes a coupling signal.

The graph is a HINT, not a merge-safety oracle: file-level granularity; may be
stale; blind to the cross-repo API contract. The orchestrator still reviews
diffs AND renders the coupling_review verdicts.
"""
import argparse
import json
import os
from collections import defaultdict

DEFAULT_TRAJECTORY_STORE = os.path.expanduser(
    "~/.claude/mcp-servers/trajectory-kb/data/trajectories.jsonl"
)


def load_graph(path):
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    return {n["id"]: n for n in d["nodes"]}, d["links"]


def build_file_coupling(nodes_by_id, links):
    adj = defaultdict(set)
    for ln in links:
        s = nodes_by_id.get(ln.get("source"))
        t = nodes_by_id.get(ln.get("target"))
        if not s or not t:
            continue
        sf, tf = s.get("source_file"), t.get("source_file")
        if sf and tf and sf != tf:
            adj[sf].add(tf)
            adj[tf].add(sf)
    return dict(adj)


def _paths_match(a, b):
    """Same file across repo-relative vs prefixed roots: equal, or one is a
    /-boundary suffix of the other (so item 'backend/app/services/x.py' matches
    graph node 'app/services/x.py' but 'xapp/s.py' does NOT match 'app/s.py').
    Without this, item paths that carry a repo prefix never resolve to graph
    nodes and the coupling advisory silently never fires."""
    return a == b or a.endswith("/" + b) or b.endswith("/" + a)


def _item_graph_files(file_paths, adj_keys):
    """Graph node source_files that path-match an item's edited files."""
    return {k for f in file_paths for k in adj_keys if _paths_match(f, k)}


def cluster_items(items):
    """Union items that MUST serialize: they share an edited file OR a declared
    contract_group (two halves of one contract -> one owner, even when their
    edited files are disjoint). Distinct clusters are file- and contract-disjoint
    -> safe to run in parallel."""
    parent = {it["name"]: it["name"] for it in items}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        parent[find(a)] = find(b)

    owner, group_owner = {}, {}
    for it in items:
        for f in it["files"]:
            if f in owner:
                union(it["name"], owner[f])
            else:
                owner[f] = it["name"]
        g = it.get("contract_group")
        if g:
            if g in group_owner:
                union(it["name"], group_owner[g])
            else:
                group_owner[g] = it["name"]
    groups = defaultdict(list)
    for it in items:
        groups[find(it["name"])].append(it["name"])
    return list(groups.values())


def _conflict_adjacency(items):
    """name -> set of names it MUST serialize with: shared edited file OR shared
    contract_group (the same keys cluster_items unions on, kept pairwise here so
    waves can see WHICH items inside a cluster actually conflict)."""
    names = [it["name"] for it in items]
    files = {it["name"]: set(it["files"]) for it in items}
    group = {it["name"]: it.get("contract_group") for it in items}
    adj = {n: set() for n in names}
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            if files[a] & files[b] or (group[a] and group[a] == group[b]):
                adj[a].add(b)
                adj[b].add(a)
    return adj


def _after_edges(items):
    """Validated producer->consumer edges from the optional per-item `after`
    list ("this item starts only after the named items INTEGRATE"). Directional
    on purpose: unlike contract_group it does NOT merge items into one owner -
    two consumers of one producer stay parallel with each other."""
    names = {it["name"] for it in items}
    after = {it["name"]: list(it.get("after") or []) for it in items}
    unknown = {d for deps in after.values() for d in deps if d not in names}
    if unknown:
        raise ValueError("unknown `after` reference(s): %s" % sorted(unknown))
    return after


def global_waves(items, adj, order_index):
    """ONE global execution schedule over all items. Items in one wave are
    mutually conflict-free (no shared file, no shared contract_group) and have
    no `after` path between them -> run concurrently; each wave starts from the
    INTEGRATED result of the waves before it (merge/rebase between waves, or
    one owner stepping through). `after` gives a topological floor (consumers
    never before producers); above the floor, greedy coloring hub-first: the
    most-conflicted item (the shared spine, e.g. the models.py contract) lands
    early so producers integrate before consumers fan out. Deterministic:
    dependency floor asc, conflict degree desc, then input order. Raises
    ValueError on an unknown `after` name or a dependency cycle."""
    after = _after_edges(items)
    names = [it["name"] for it in items]
    consumers = defaultdict(list)
    indeg = {n: len(after[n]) for n in names}
    for n, deps in after.items():
        for d in deps:
            consumers[d].append(n)
    floor = {n: 0 for n in names}
    queue = [n for n in names if indeg[n] == 0]
    qi = 0
    while qi < len(queue):
        n = queue[qi]
        qi += 1
        for c in consumers[n]:
            floor[c] = max(floor[c], floor[n] + 1)
            indeg[c] -= 1
            if indeg[c] == 0:
                queue.append(c)
    if qi != len(names):
        cyc = sorted(n for n in names if indeg[n] > 0)
        raise ValueError("`after` cycle involving: %s" % cyc)
    members = set(names)
    verts = sorted(names, key=lambda n: (floor[n],
                                         -len(adj.get(n, set()) & members),
                                         order_index[n]))
    wave_of = {}
    for v in verts:
        used = {wave_of[u] for u in adj.get(v, set()) if u in wave_of}
        w = max([floor[v]] + [wave_of[p] + 1 for p in after[v] if p in wave_of])
        while w in used:
            w += 1
        wave_of[v] = w
    n_waves = max(wave_of.values()) + 1 if wave_of else 0
    waves = [[] for _ in range(n_waves)]
    for v in sorted(names, key=lambda n: order_index[n]):
        waves[wave_of[v]].append(v)
    return [w for w in waves if w]


def _after_connected(items):
    """Frozenset pairs with an `after` PATH between them (either direction) -
    their order is DECLARED, so they need no coupling_review verdict."""
    after = _after_edges(items)
    names = list(after)
    reach = {}
    for n in names:
        seen, stack = set(), list(after[n])
        while stack:
            p = stack.pop()
            if p in seen:
                continue
            seen.add(p)
            stack.extend(after[p])
        reach[n] = seen
    return {frozenset((a, b)) for a in names for b in reach[a]}


# ── trajectory memory (optional, additive) ──────────────────────────────────

def load_trajectories(path):
    """Read the append-only JSONL store; exclude superseded entries. A missing or
    unreadable file -> [] (the plan degrades to the marker-only path, no error)."""
    if not path:
        return []
    try:
        with open(path, encoding="utf-8") as f:
            raw = f.read()
    except OSError:
        return []
    entries = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue  # skip a corrupt line, don't fail the whole read
    superseded = {e.get("supersedes") for e in entries if e.get("supersedes")}
    return [e for e in entries if e.get("id") not in superseded]


def _basename(p):
    return p.rsplit("/", 1)[-1]


def _ref_matches_item(ref, item):
    """Does a free-text reference (a trajectory surface / file / regressed string)
    point at this item? Path-suffix match on an edited file first (precise), then
    a basename / filestem / item-name substring (catches surface-only entries)."""
    if not ref:
        return False
    r = str(ref).lower()
    for f in item["files"]:
        if _paths_match(str(ref), f):
            return True
        bn = _basename(f).lower()
        if bn and bn in r:
            return True
        stem = bn.rsplit(".", 1)[0]
        if len(stem) >= 4 and stem in r:
            return True
    nm = item["name"].lower()
    return len(nm) >= 4 and nm in r


def _entry_matches_item(entry, item):
    """Is this trajectory entry about this work-item? Edited-file overlap
    (precise) OR the entry's surface/tags reference one of the item's files or
    its name (fallback for entries whose surface is prose)."""
    for ef in (entry.get("files") or []):
        for itf in item["files"]:
            if _paths_match(str(ef), itf):
                return True
    hay = (entry.get("surface") or "") + " " + " ".join(entry.get("tags") or [])
    return _ref_matches_item(hay, item)


def _entry_regresses_item(entry, target_item):
    """Did fixing this entry's surface break the target item's surface? (the
    structured `regressed` list - a recorded 'fixing A broke B')."""
    return any(_ref_matches_item(r, target_item) for r in (entry.get("regressed") or []))


def history_tier_bump(item, trajectories):
    """A surface with a bad track record is high-risk regardless of path markers.
    Returns (bump?, reason). Bumps on a recorded revert, a speculative ship, a
    caused-regression, or >=2 prior wrong-surface traps on the matched surface."""
    matched = [e for e in trajectories if _entry_matches_item(e, item)]
    if not matched:
        return False, ""
    reverts = sum(1 for e in matched if e.get("outcome") == "reverted")
    spec = sum(1 for e in matched if e.get("outcome") == "speculative")
    regressed = sum(1 for e in matched if (e.get("regressed") or []))
    traps = sum(1 for e in matched if (e.get("what_failed") or []))
    parts = []
    if reverts:
        parts.append(f"{reverts} reverted")
    if spec:
        parts.append(f"{spec} speculative")
    if regressed:
        parts.append(f"{regressed} caused-regression")
    if traps >= 2:
        parts.append(f"{traps} prior traps")
    return bool(parts), ", ".join(parts)


# ── coupling + tier ─────────────────────────────────────────────────────────

def coupling_review(items, adj, risk_markers, trajectories=None):
    """For each file-disjoint, NOT-co-clustered pair, surface soft coupling
    signals that warrant an explicit parallelize-vs-serialize verdict before
    dispatch (the ORCHESTRATOR renders the verdict; this flags + defaults only):
      - import-adjacent:        their files are one hop apart in the graph
      - shared-risk-marker:<M>: the SAME risk-marker matches a file in both
      - regression-history:     trajectory memory records a fix on one surface
                                having broken the other (default 'serialize')
    default 'serialize' when they share a risk-marker or have a recorded
    regression (likely halves of one contract / known to break each other); else
    'parallel'. Signal-free pairs are omitted (auto-parallel)."""
    names = [it["name"] for it in items]
    by_name = {it["name"]: it for it in items}
    files = {it["name"]: set(it["files"]) for it in items}
    adj_keys = list(adj)
    gfiles = {n: _item_graph_files(files[n], adj_keys) for n in names}
    matched = ({n: [e for e in trajectories if _entry_matches_item(e, by_name[n])] for n in names}
               if trajectories else {n: [] for n in names})
    co = set()
    for c in cluster_items(items):
        for i in range(len(c)):
            for j in range(i + 1, len(c)):
                co.add(frozenset((c[i], c[j])))
    out = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            if frozenset((a, b)) in co or files[a] & files[b]:
                continue
            signals = []
            if any(bf in adj.get(af, ()) for af in gfiles[a] for bf in gfiles[b]):
                signals.append("import-adjacent")
            shared = sorted({m for m in risk_markers
                             if any(m in f for f in files[a]) and any(m in f for f in files[b])})
            signals += ["shared-risk-marker:" + m for m in shared]
            regression = (any(_entry_regresses_item(e, by_name[b]) for e in matched[a])
                          or any(_entry_regresses_item(e, by_name[a]) for e in matched[b]))
            if regression:
                signals.append("regression-history")
            if signals:
                out.append({"pair": [a, b], "signals": signals,
                            "default": "serialize" if (shared or regression) else "parallel"})
    return out


def tier_for(file_paths, risk_markers):
    for f in file_paths:
        if any(m in f for m in risk_markers):
            return "top"
    return "cheap"


def plan(items, graph_path, risk_markers, trajectories=None):
    """graph_path is OPTIONAL (None -> no import-adjacency signals; clustering,
    waves, tiers, and the marker/history coupling signals still compute)."""
    if graph_path:
        nodes, links = load_graph(graph_path)
        adj = build_file_coupling(nodes, links)
    else:
        adj = {}
    trajectories = trajectories or []
    tier, tier_notes = {}, {}
    for it in items:
        t = tier_for(it["files"], risk_markers)
        if t != "top" and trajectories:
            bump, reason = history_tier_bump(it, trajectories)
            if bump:
                t = "top"
                tier_notes[it["name"]] = "history: " + reason
        tier[it["name"]] = t
    conflict_adj = _conflict_adjacency(items)
    order_index = {it["name"]: i for i, it in enumerate(items)}
    decided = _after_connected(items)
    review = [p for p in coupling_review(items, adj, risk_markers, trajectories)
              if frozenset(p["pair"]) not in decided]
    result = {
        "clusters": cluster_items(items),
        "waves": global_waves(items, conflict_adj, order_index),
        "coupling_review": review,
        "tier": tier,
    }
    if tier_notes:  # only present when history actually bumped something
        result["tier_notes"] = tier_notes
    return result


def main():
    ap = argparse.ArgumentParser(description="Plan a fan-out from a graphify graph.")
    ap.add_argument("--graph", default=None,
                    help="path to graphify graph.json (optional: without it the "
                         "plan loses only the import-adjacency coupling signal)")
    ap.add_argument("--items", required=True,
                    help='JSON file: [{"name","files":[...],"contract_group"?:"tag",'
                         '"after"?:["producer-item", ...]}]')
    ap.add_argument("--risk-markers", default="",
                    help="comma-separated path substrings that force the top tier")
    ap.add_argument("--trajectories", default=DEFAULT_TRAJECTORY_STORE,
                    help="trajectory-kb JSONL store for history-aware tiering + coupling "
                         "(default: the global store; missing file = ignored)")
    ap.add_argument("--no-trajectories", action="store_true",
                    help="ignore trajectory memory (marker-only plan)")
    args = ap.parse_args()
    with open(args.items, encoding="utf-8") as f:
        items = json.load(f)
    markers = [m for m in args.risk_markers.split(",") if m]
    trajectories = [] if args.no_trajectories else load_trajectories(args.trajectories)
    print(json.dumps(plan(items, args.graph, markers, trajectories), indent=2))


if __name__ == "__main__":
    main()
