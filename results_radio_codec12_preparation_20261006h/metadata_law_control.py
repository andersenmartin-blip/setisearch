"""Pure metadata-law control: no native package, HDF5 file, or payload access."""
import ast
import copy
import hashlib
import json
from pathlib import Path

from preparation import LAW_NAMES, PIPELINE, canonical

GUARD_SHA256 = "65533ad8ead2bd7283beee9645a18b3a652a3ede50425573b64aaca69120e6a6"


class MetadataDataset:
    def __init__(self, entries):
        self.entries = entries
        self.payload_index_attempts = 0

    def get_create_plist(self):
        return self

    def get_nfilters(self):
        return len(self.entries)

    def get_filter(self, index):
        return self.entries[index]

    @property
    def id(self):
        return self

    def __getitem__(self, key):
        self.payload_index_attempts += 1
        raise RuntimeError("payload indexing is forbidden")


def _guard(repo_root):
    raw = (Path(repo_root) / "src/seti_repeater/hdf5_filter_contract_radio.py").read_bytes()
    if hashlib.sha256(raw).hexdigest() != GUARD_SHA256:
        raise ValueError("filter guard pin differs")
    tree = ast.parse(raw)
    if any(not isinstance(node, (ast.Expr, ast.FunctionDef)) for node in tree.body):
        raise ValueError("pure guard capability differs")
    namespace = {"__builtins__": __builtins__}
    exec(compile(tree, "<pinned-metadata-filter-guard>", "exec"), namespace)
    return namespace


def observe(repo_root):
    guard = _guard(repo_root)
    cases, datasets = [], []

    def expect(name, operation, rejects=False):
        observed = "accept"
        try:
            operation()
        except ValueError:
            observed = "reject"
        expected = "reject" if rejects else "accept"
        if observed != expected:
            raise AssertionError("metadata law mismatch: " + name)
        cases.append({"index": len(cases), "name": name, "expected": expected, "observed": observed})

    positive = MetadataDataset(copy.deepcopy(PIPELINE)); datasets.append(positive)
    expect("exact_pipeline", lambda: guard["check_dataset"](positive, PIPELINE))
    named = [[32008, 1, [0, 3, 4, 0, 2], "display label is not codec authority"]]
    named_dataset = MetadataDataset(named); datasets.append(named_dataset)
    expect("display_name_ignored", lambda: guard["check_dataset"](named_dataset, PIPELINE))
    expect("explicit_unfiltered", lambda: guard["declared"]({"observed_hdf5_filters": []}, required=True))
    expect("missing_optional_local_declaration", lambda: guard["declared"]({}, required=False))
    expect("missing_required_declaration", lambda: guard["declared"]({}, required=True), True)

    mutated = []
    for position in (0, 1):
        value = copy.deepcopy(PIPELINE); value[0][position] += 1
        mutated.append(("pipeline_" + ("id" if position == 0 else "flags") + "_mutation", value))
    for index in range(5):
        value = copy.deepcopy(PIPELINE); value[0][2][index] += 1
        mutated.append(("client_datum_" + str(index) + "_mutation", value))
    mutated.extend((("removed_filter", []), ("extra_filter", PIPELINE + [[1, 1, [4]]])))
    for name, entries in mutated:
        dataset = MetadataDataset(entries); datasets.append(dataset)
        expect(name, lambda dataset=dataset: guard["check_dataset"](dataset, PIPELINE), True)
    for index, invalid in enumerate((True, -1, 2.0, "2")):
        value = copy.deepcopy(PIPELINE); value[0][2][4] = invalid
        expect("invalid_client_datum_type_" + str(index), lambda value=value: guard["signature"](value), True)
    for name, entries in (("boolean_filter_id", [[True, 1, []]]),
                          ("boolean_filter_flags", [[32008, True, []]]),
                          ("nonexplicit_pipeline", {}),
                          ("malformed_filter_entry", [[32008, 1]])):
        expect(name, lambda entries=entries: guard["signature"](entries), True)

    if tuple(row["name"] for row in cases) != LAW_NAMES or any(ds.payload_index_attempts for ds in datasets):
        raise AssertionError("case order or metadata-only boundary differs")
    return {"schema": "codec12-pure-metadata-laws-v1", "status": "PASS_METADATA_ONLY",
            "guard_sha256": GUARD_SHA256, "cases": cases, "case_count": len(cases),
            "payload_index_attempts": sum(ds.payload_index_attempts for ds in datasets),
            "native_imports": 0, "hdf5_files_opened": 0, "archive_values_read": 0,
            "scientific_certificate_issued": False}


def main():
    here = Path(__file__).resolve().parent
    result = observe(here.parent)
    with (here / "METADATA_LAW_OBSERVATION.json").open("xb") as handle:
        handle.write(canonical(result))
    print("PASS_METADATA_ONLY: 22/22 laws; zero payload access")


if __name__ == "__main__":
    main()
