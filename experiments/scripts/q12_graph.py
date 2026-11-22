#!/usr/bin/env python3
"""Shared offline graph helpers for the Q12 benchmark scripts (stdlib only; scripts load it with importlib because python3 -I
removes the script directory from the import path).

Reads ONLY the plain-CSV Neptune openCypher sidecar of a completed Phase 6 Spark export:
  <export-dir>/run-manifest.json
  <export-dir>/neptune-opencypher-csv/data/nodes/*.csv          RESEARCHER, WORK, TOPIC, INSTITUTION, VENUE nodes
  <export-dir>/neptune-opencypher-csv/data/graph-edges/*.csv    AUTHORED, HAS_TOPIC, AFFILIATED_WITH, PUBLISHED_IN edges
  <export-dir>/neptune-opencypher-csv/data/coauthor-edges/*.csv COAUTHORED_WITH edges, one row per stored window

Every definition is a port of modules/spark (Phase6DEJobs.scala, Phase6FGJobs.scala), so the expected answers do not depend on
the Parquet tables that Python here cannot read:
  distinct coauthors   count of distinct neighbours of the researcher in the window graph.
  components           connected components of the window graph; the label is the minimum researcher id of the component
                       (job04 min-label propagation); id = "component:" + sha256("graph-v1\\n<window>\\n<label>")
                       (StableIds.sparkAnalyticsId).
  communities          synchronous label propagation (job06): every vertex starts with its own id as label; each iteration a vertex
                       takes the label with the largest summed jointPublicationCount among its neighbours' labels, ties to the
                       smallest label (string order); at most 20 iterations (communityMaxIterations), stopping early when no
                       label changes. id = "community:" + sha256 of the same material.
  bridges              per vertex, over its neighbours in OTHER communities: crossCommunityDegree = number of such neighbours,
                       crossCommunityWeight = their summed jointPublicationCount, communitiesConnected = number of distinct other
                       communities, participationCoefficient = 1 - sum_c(n_c^2) / degree^2 (n_c = neighbours in community c).
  team size            maximumCoauthorsOnOnePaper = max over the researcher's works of (distinct researchers on the work - 1).
                       A work belongs to a window entirely (all its authors share its year), so a work's team size does not depend
                       on the window; the CSV sidecar has no work years, so the per-researcher maximum is computable only for
                       all-years (a cited work's team size can be checked in any window).
  temporal change      from/to window values of distinct coauthors and component size, delta = to - from; the Jaccard overlap of the
                       member sets of the researcher's from and to communities.
Vertices with no edge in a window are not in the CSV; researchers used in questions always have edges in the windows asked about.
"""
import csv
import glob
import hashlib
import json
import os

WINDOWS = ("all-years", "through-2009", "2010-2014", "2015-2019", "2020-2026", "since-2015")
POLICY = "graph-v1"
COMMUNITY_MAX_ITERATIONS = 20


class Refused(Exception):
    pass


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def norm_name(raw):
    return " ".join(raw.strip().lower().split())


def analytics_id(kind, window, label):
    """StableIds.sparkAnalyticsId(kind, "graph-v1", window, Seq(label))."""
    return "%s:%s" % (kind, sha256_text("\n".join((POLICY, window, label))))


def _csv_rows(path):
    with open(path, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            yield row


def _list_csv(directory):
    files = sorted(glob.glob(os.path.join(glob.escape(directory), "*.csv")))
    if not files:
        raise Refused("no CSV part files in %s" % directory)
    return files


class Export:
    """The parts of a Phase 6 export the Q12 scripts need, plus the sha256 of every file read."""

    def __init__(self, export_dir):
        export_dir = os.path.abspath(export_dir)
        manifest_path = os.path.join(export_dir, "run-manifest.json")
        if not os.path.isfile(manifest_path):
            raise Refused("%s has no run-manifest.json: not a Phase 6 Spark export" % os.path.basename(export_dir))
        with open(manifest_path, encoding="utf-8") as handle:
            self.run_id = json.load(handle).get("runId")
        if not isinstance(self.run_id, str) or not self.run_id.startswith("run:"):
            raise Refused("run-manifest.json holds no runId")
        data = os.path.join(export_dir, "neptune-opencypher-csv", "data")
        self.files_read = [("run-manifest.json", sha256_file(manifest_path))]
        self.researchers, self.works, self.topics, self.institutions, self.venues = {}, {}, {}, {}, {}
        self.authored = {}       # work id -> set of researcher ids
        self.authored_by = {}    # researcher id -> set of work ids
        self.has_topic = {}      # work id -> set of topic ids
        self.affiliated = {}     # researcher id -> set of institution ids
        self.edges = {w: {} for w in WINDOWS}      # window -> {(a, b): jointPublicationCount}
        self.edge_ids = {w: {} for w in WINDOWS}   # window -> {(a, b): edge id}
        self.edge_works = {w: {} for w in WINDOWS}  # window -> {(a, b): representative work ids (at most 5; all joint works when joint <= 5)}
        csv.field_size_limit(2 ** 31 - 1)
        by_label = {"RESEARCHER": self.researchers, "WORK": self.works, "TOPIC": self.topics,
                    "INSTITUTION": self.institutions, "VENUE": self.venues}
        for part in _list_csv(os.path.join(data, "nodes")):
            self.files_read.append((os.path.relpath(part, export_dir), sha256_file(part)))
            for row in _csv_rows(part):
                target = by_label.get(row[":LABEL"])
                if target is not None:
                    target[row[":ID"]] = row["label:String"]
        for part in _list_csv(os.path.join(data, "graph-edges")):
            self.files_read.append((os.path.relpath(part, export_dir), sha256_file(part)))
            for row in _csv_rows(part):
                kind, start, end = row[":TYPE"], row[":START_ID"], row[":END_ID"]
                if kind == "AUTHORED":
                    self.authored.setdefault(end, set()).add(start)
                    self.authored_by.setdefault(start, set()).add(end)
                elif kind == "HAS_TOPIC":
                    self.has_topic.setdefault(start, set()).add(end)
                elif kind == "AFFILIATED_WITH":
                    self.affiliated.setdefault(start, set()).add(end)
        for part in _list_csv(os.path.join(data, "coauthor-edges")):
            self.files_read.append((os.path.relpath(part, export_dir), sha256_file(part)))
            for row in _csv_rows(part):
                window = row["windowId:String"]
                if window not in self.edges:
                    continue
                a, b = sorted((row[":START_ID"], row[":END_ID"]))
                if a == b:
                    continue
                joint = int(row["jointPublicationCount:Long"] or 0)
                if joint >= self.edges[window].get((a, b), 0):
                    self.edges[window][(a, b)] = joint
                    self.edge_ids[window][(a, b)] = row["evidenceEdgeId:String"] or row[":ID"]
                    try:
                        works = json.loads(row.get("representativeWorkIdsJson:String") or "[]")
                    except ValueError:
                        works = []
                    self.edge_works[window][(a, b)] = tuple(sorted(w for w in works if isinstance(w, str)))
        if not self.researchers or not self.edges["all-years"]:
            raise Refused("the export holds no researcher nodes or no all-years coauthor edges")
        self.files_read.sort()
        self._windows = {}

    def window(self, window_id):
        if window_id not in self._windows:
            self._windows[window_id] = WindowGraph(window_id, self.edges[window_id])
        return self._windows[window_id]


class WindowGraph:
    """Undirected weighted graph of one stored window with the Phase 6 analytics (lazy and cached)."""

    def __init__(self, window_id, edges):
        self.window_id = window_id
        self.weight = edges
        self.adj = {}
        for (a, b), joint in edges.items():
            self.adj.setdefault(a, {})[b] = joint
            self.adj.setdefault(b, {})[a] = joint
        self._components = None
        self._communities = None
        self._bridges = None

    def degree(self, node):
        return len(self.adj.get(node, ()))

    def joint(self, a, b):
        return self.weight.get((a, b) if a < b else (b, a), 0)

    # components -------------------------------------------------------------------------------------------------------------
    def components(self):
        """Returns (label_of {node: min id of its component}, members {label: sorted ids})."""
        if self._components is None:
            parent = {node: node for node in self.adj}

            def find(x):
                root = x
                while parent[root] != root:
                    root = parent[root]
                while parent[x] != root:
                    parent[x], x = root, parent[x]
                return root
            for (a, b) in self.weight:
                ra, rb = find(a), find(b)
                if ra != rb:
                    if ra < rb:
                        parent[rb] = ra
                    else:
                        parent[ra] = rb
            label_of = {node: find(node) for node in self.adj}
            members = {}
            for node, label in label_of.items():
                members.setdefault(label, []).append(node)
            for label in members:
                members[label].sort()
            self._components = (label_of, members)
        return self._components

    def component_size(self, node):
        label_of, members = self.components()
        return len(members[label_of[node]]) if node in label_of else 1

    # shortest paths ---------------------------------------------------------------------------------------------------------
    def bfs(self, source, max_depth=None):
        """Returns (distance {node: hops}, number of shortest paths {node: n}) for nodes within max_depth hops of source."""
        dist, count = {source: 0}, {source: 1}
        frontier, depth = [source], 0
        while frontier and (max_depth is None or depth < max_depth):
            depth += 1
            nxt = []
            for u in frontier:
                for v in self.adj[u]:
                    if v not in dist:
                        dist[v], count[v] = depth, count[u]
                        nxt.append(v)
                    elif dist[v] == depth:
                        count[v] += count[u]
            frontier = nxt
        return dist, count

    def shortest_paths(self, a, b, limit=25, max_depth=6):
        """Returns (hops, number of shortest paths, up to `limit` shortest paths as id lists in lexicographic order).
        hops is None when b is not within max_depth hops of a (the runtime status is then Disconnected or ExceededMaxHops)."""
        if a not in self.adj or b not in self.adj:
            return None, 0, []
        da, count = self.bfs(a, max_depth)
        if b not in da:
            return None, 0, []
        hops = da[b]
        db, _ = self.bfs(b, hops)
        paths = []

        def walk(node, prefix):
            if len(paths) >= limit:
                return
            if node == b:
                paths.append(prefix)
                return
            for nxt in sorted(self.adj[node]):
                if da.get(nxt) == da[node] + 1 and db.get(nxt) == hops - da[nxt]:
                    walk(nxt, prefix + [nxt])
        walk(a, [a])
        return hops, count[b], paths

    # communities ------------------------------------------------------------------------------------------------------------
    def communities(self):
        """Returns (label {node: label}, iterations, finalChangedCount, converged)."""
        if self._communities is None:
            label = {node: node for node in self.adj}
            iterations, changed = 0, 1
            while changed > 0 and iterations < COMMUNITY_MAX_ITERATIONS:
                nxt, changed = {}, 0
                for node, neighbours in self.adj.items():
                    votes = {}
                    for other, weight in neighbours.items():
                        votes[label[other]] = votes.get(label[other], 0) + weight
                    best = min(votes, key=lambda lab: (-votes[lab], lab))
                    nxt[node] = best
                    if best != label[node]:
                        changed += 1
                label = nxt
                iterations += 1
            self._communities = (label, iterations, changed, changed == 0)
        return self._communities

    def community_members(self):
        label = self.communities()[0]
        members = {}
        for node, lab in label.items():
            members.setdefault(lab, []).append(node)
        for lab in members:
            members[lab].sort()
        return members

    def bridges(self):
        """{node: {crossCommunityDegree, crossCommunityWeight, communitiesConnected, participationCoefficient, degree}}."""
        if self._bridges is None:
            label = self.communities()[0]
            out = {}
            for node, neighbours in self.adj.items():
                per, weight_by = {}, {}
                for other, weight in neighbours.items():
                    per[label[other]] = per.get(label[other], 0) + 1
                    weight_by[label[other]] = weight_by.get(label[other], 0) + weight
                own, degree = label[node], len(neighbours)
                out[node] = {
                    "crossCommunityDegree": sum(n for c, n in per.items() if c != own),
                    "crossCommunityWeight": sum(w for c, w in weight_by.items() if c != own),
                    "communitiesConnected": sum(1 for c in per if c != own),
                    "participationCoefficient": 1.0 - sum(float(n) * float(n) for n in per.values()) / (float(degree) * float(degree)),
                    "degree": degree}
            self._bridges = out
        return self._bridges


def team_sizes(export):
    """{work id: number of distinct researchers on the work} from the AUTHORED edges."""
    return {work: len(people) for work, people in export.authored.items()}


def max_team(export, researcher, sizes):
    """(maximumCoauthorsOnOnePaper, sorted ids of the works that reach it) over all works of the researcher (all-years)."""
    works = export.authored_by.get(researcher, ())
    if not works:
        return 0, []
    best = max(sizes[w] - 1 for w in works)
    return best, sorted(w for w in works if sizes[w] - 1 == best)


def jaccard(a, b):
    a, b = set(a), set(b)
    return len(a & b) / len(a | b) if (a or b) else 0.0
