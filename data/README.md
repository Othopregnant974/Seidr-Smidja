# data/ — Runtime Data Files
**Keeper:** Forge Worker (Eldra Járnsdóttir) — populated in Phase 5
**Layer:** Runtime assets (not gitignored; part of the deliverable)

---

## What This Directory Is

The `data/` directory is the home of all YAML data files that the forge reads at runtime. No compliance rules, catalog entries, or configurable data values are hardcoded in Python source. They live here, in files the Forge Worker populates and the gate loads dynamically.

This directory is **not gitignored**. Its contents are part of the deliverable — agents installing this package need these files to be present for the forge to operate.

---

## Expected Contents (Forge Worker will populate in Phase 5)

```
data/
├── README.md                     ← This file.
├── hoard_catalog.yaml            ← Hoard asset catalog. Maps asset_id → file path + metadata.
└── compliance_rules/
    ├── vrchat.yaml               ← VRChat compliance rules: polygon budgets, bone requirements,
    │                               viseme coverage, material limits, texture size constraints.
    └── vtube_studio.yaml         ← VTube Studio compliance rules: VRM spec version, expression/
                                    blendshape coverage, lookat configuration.
```

---

## Rules for This Directory

1. **YAML only.** All files in this directory are YAML. No Python, no JSON embedded in YAML, no binary files.
2. **No hardcoded values in Python.** If you find a compliance rule, an asset catalog entry, or a configurable threshold written directly in Python source code, it belongs here instead.
3. **Rule files are loaded at runtime.** The Gate loads `compliance_rules/` files on each invocation. This means rules can be updated without recompiling or reinstalling the package.
4. **The Hoard catalog is the source of truth for asset IDs.** Any `base_asset_id` used in a Loom spec must have a matching entry in `hoard_catalog.yaml`, or `hoard.resolve()` will raise `AssetNotFoundError`.

---

## Cross-References

- [`src/seidr_smidja/hoard/INTERFACE.md`](../src/seidr_smidja/hoard/INTERFACE.md) — `catalog_path()` returns the path to `hoard_catalog.yaml`.
- [`src/seidr_smidja/gate/INTERFACE.md`](../src/seidr_smidja/gate/INTERFACE.md) — Gate loads compliance rules from this directory.
- [`docs/PHILOSOPHY.md §III Sacred Law I`](../docs/PHILOSOPHY.md) — "No Hardcoded Wyrd." All data lives in files.
- [`docs/ARCHITECTURE.md §VIII`](../docs/ARCHITECTURE.md) — Configuration model (note: this directory is data, not configuration; config/ holds process-level settings, data/ holds domain data).

---

*Placeholder written by Eirwyn Rúnblóm, Scribe — 2026-05-06. Forge Worker populates contents in Phase 5.*
