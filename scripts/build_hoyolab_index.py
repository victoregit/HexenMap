"""Build reproducible, deterministic, and verified HoYoLAB -> AppSample marker index."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.live.appsample_import import parse_catalog
from src.live.appsample_catalog import project

EXPECTED_CATALOG_SHA256 = "0d57491936253a8c0546f16c13b1bb0f7ac4c1f90754d06fd4c2f83d5e49f5cc"

# Teyvat (Map 2) target labels
TARGET_LABELS: dict[int, tuple[str, str]] = {
    17: ("o17", "common-chest"),
    44: ("o44", "exquisite-chest"),
    45: ("o45", "precious-chest"),
    46: ("o46", "luxurious-chest"),
    269: ("o269", "remarkable-chest"),
    5: ("o5", "anemoculus"),
    6: ("o6", "geoculus"),
    194: ("o194", "electroculus"),
    403: ("o403", "dendroculus"),
    508: ("o508", "hydroculus"),
    626: ("o626", "pyroculus"),
}

# Calibrated regional affine offsets for Teyvat (Map 2)
OFFSET_INAZUMA = (3885.50, -2323.46)
OFFSET_TEYVAT_MAIN = (6089.55, -2323.46)
OFFSET_RESORT = (8084.75, -2323.46)
MAX_DISTANCE_PX = 25.0

# Phase A & Phase B Independent Maps: Calibrated affine parameters and permanent target categories
PHASE_A_INDEPENDENT_MAPS: dict[int, dict] = {
    7: {
        "name": "enkanomiya",
        "cache_filename": "hoyolab_map_7.json",
        "scale_x": 3.990421,
        "scale_y": 3.990412,
        "offset_x": -802.7516,
        "offset_y": -1072.9036,
        "max_distance_px": 5.0,
        "target_labels": {
            17: ("o17", "enkanomiya-common-chest"),
            44: ("o44", "enkanomiya-exquisite-chest"),
            45: ("o45", "enkanomiya-precious-chest"),
            46: ("o46", "enkanomiya-luxurious-chest"),
            323: ("o323", "enkanomiya-key-sigil-1"),
            324: ("o324", "enkanomiya-key-sigil-2"),
            325: ("o325", "enkanomiya-key-sigil-3"),
            326: ("o326", "enkanomiya-key-sigil-4"),
            327: ("o327", "enkanomiya-key-sigil-5"),
        },
    },
    9: {
        "name": "chasm",
        "cache_filename": "hoyolab_map_9.json",
        "scale_x": 7.980874,
        "scale_y": 7.980858,
        "offset_x": 1618.7925,
        "offset_y": 87.7926,
        "target_labels": {
            17: ("o17", "chasm-common-chest"),
            44: ("o44", "chasm-exquisite-chest"),
            45: ("o45", "chasm-precious-chest"),
            46: ("o46", "chasm-luxurious-chest"),
        },
    },
    34: {
        "name": "sea-of-bygone-eras",
        "cache_filename": "hoyolab_map_34.json",
        "scale_x": 4.000615,
        "scale_y": 4.000392,
        "offset_x": 380.0468,
        "offset_y": 360.0380,
        "target_labels": {
            17: ("o17", "bygone-common-chest"),
            44: ("o44", "bygone-exquisite-chest"),
            45: ("o45", "bygone-precious-chest"),
            46: ("o46", "bygone-luxurious-chest"),
            269: ("o269", "bygone-remarkable-chest"),
            508: ("o508", "bygone-hydroculus"),
        },
    },
    36: {
        "name": "ancient-sacred-mountain",
        "cache_filename": "hoyolab_map_36.json",
        "scale_x": 6.000203,
        "scale_y": 6.000201,
        "offset_x": 0.0,
        "offset_y": 0.0,
        "target_labels": {
            17: ("o17", "sacred-common-chest"),
            44: ("o44", "sacred-exquisite-chest"),
            45: ("o45", "sacred-precious-chest"),
            269: ("o269", "sacred-remarkable-chest"),
            626: ("o626", "sacred-pyroculus"),
        },
    },
    37: {
        "name": "temple-of-space",
        "cache_filename": "hoyolab_map_37.json",
        "scale_x": 3.996210,
        "scale_y": 3.996280,
        "offset_x": -47.9618,
        "offset_y": -499.5338,
        "max_distance_px": 5.0,
        "target_labels": {
            17: ("o17", "temple-common-chest"),
            44: ("o44", "temple-exquisite-chest"),
            45: ("o45", "temple-precious-chest"),
            269: ("o269", "temple-remarkable-chest"),
        },
    },
    40: {
        "name": "frost-moon",
        "cache_filename": "hoyolab_map_40.json",
        "scale_x": 1.742026,
        "scale_y": 1.742061,
        "offset_x": -4036.2665,
        "offset_y": -1.7414,
        "max_distance_px": 2.0,
        "target_labels": {
            17: ("o17", "moon-common-chest"),
            44: ("o44", "moon-exquisite-chest"),
            45: ("o45", "moon-precious-chest"),
            46: ("o46", "moon-luxurious-chest"),
            694: ("o694", "moon-lunoculus"),
        },
    },
}


def build_index(catalog_path: Path, hoyolab_map2_path: Path, cache_dir: Path | None = None) -> dict:
    catalog_bytes = catalog_path.read_bytes()
    catalog_sha256 = hashlib.sha256(catalog_bytes).hexdigest()
    if catalog_sha256 != EXPECTED_CATALOG_SHA256:
        raise ValueError(f"Catalog SHA-256 mismatch: {catalog_sha256} != {EXPECTED_CATALOG_SHA256}")

    if cache_dir is None:
        cache_dir = hoyolab_map2_path.parent

    as_points = parse_catalog(json.loads(catalog_bytes.decode("utf-8")))
    valid_as_ids = {p.external_id: p for p in as_points}

    # Group AppSample points by (map_id, marker_type)
    as_by_map_type: dict[tuple[int, str], list[dict]] = defaultdict(list)
    for p in as_points:
        px, py = project(p.x, p.y)
        as_by_map_type[(p.map_id, p.marker_type)].append({
            "external_id": p.external_id,
            "x": px,
            "y": py,
            "raw_x": p.x,
            "raw_y": p.y,
            "level": p.level,
        })

    mapping: dict[str, str] = {}
    categories_stats: dict[str, dict] = {}
    residuals: list[float] = []
    total_ambiguous = 0
    total_unmatched = 0

    # -------------------------------------------------------------
    # 1. Teyvat (Map 2) Calibration & Matching (Preserved 100%)
    # -------------------------------------------------------------
    hl_data = json.loads(hoyolab_map2_path.read_bytes().decode("utf-8"))
    hl_points = hl_data.get("data", {}).get("point_list", [])

    for label_id, (as_type, cat_name) in TARGET_LABELS.items():
        hl_subset = [p for p in hl_points if p.get("label_id") == label_id]
        as_subset = as_by_map_type[(2, as_type)]

        as_candidate_counts: Counter[str] = Counter()
        first_pass_matches: list[tuple[int, str, float]] = []

        ambiguous_in_cat = 0
        unmatched_in_cat = 0

        for hp in hl_subset:
            hx = float(hp["x_pos"])
            hy = float(hp["y_pos"])
            area = hp.get("area_id", 0)

            if area == 3:
                dx, dy = OFFSET_INAZUMA
            elif area == 11 and hx < -13000:
                dx, dy = OFFSET_RESORT
            else:
                dx, dy = OFFSET_TEYVAT_MAIN

            target_px = hx + dx
            target_py = hy + dy

            close_candidates = []
            for ap in as_subset:
                dist = math.hypot(ap["x"] - target_px, ap["y"] - target_py)
                if dist <= MAX_DISTANCE_PX:
                    close_candidates.append((ap["external_id"], dist))

            if len(close_candidates) == 1:
                best_as_id, dist = close_candidates[0]
                first_pass_matches.append((hp["id"], best_as_id, dist))
                as_candidate_counts[best_as_id] += 1
            elif len(close_candidates) > 1:
                ambiguous_in_cat += 1
            else:
                unmatched_in_cat += 1

        cat_mapped = 0
        cat_residuals = []
        for hl_id, as_id, dist in first_pass_matches:
            if as_candidate_counts[as_id] == 1:
                key = f"2:{hl_id}"
                mapping[key] = as_id
                cat_mapped += 1
                cat_residuals.append(dist)
                residuals.append(dist)
            else:
                ambiguous_in_cat += 1

        total_ambiguous += ambiguous_in_cat
        total_unmatched += unmatched_in_cat

        categories_stats[cat_name] = {
            "map_id": 2,
            "label_id": label_id,
            "as_type": as_type,
            "total_hl": len(hl_subset),
            "total_as": len(as_subset),
            "mapped": cat_mapped,
            "ambiguous": ambiguous_in_cat,
            "unmatched": unmatched_in_cat,
            "median_residual_px": round(sorted(cat_residuals)[len(cat_residuals) // 2], 2) if cat_residuals else 0.0,
            "max_residual_px": round(max(cat_residuals), 2) if cat_residuals else 0.0,
        }

    # -------------------------------------------------------------
    # 2. Phase A Independent Maps: Map 9, Map 34, Map 36
    # -------------------------------------------------------------
    for mid, mcfg in PHASE_A_INDEPENDENT_MAPS.items():
        cache_file = cache_dir / mcfg["cache_filename"]
        if not cache_file.exists():
            raise FileNotFoundError(f"Missing cache file for Map {mid}: {cache_file}")

        hl_map_data = json.loads(cache_file.read_bytes().decode("utf-8"))
        hl_map_points = hl_map_data.get("data", {}).get("point_list", [])
        sx, sy = mcfg["scale_x"], mcfg["scale_y"]
        tx, ty = mcfg["offset_x"], mcfg["offset_y"]

        for label_id, (as_type, cat_name) in mcfg["target_labels"].items():
            hl_subset = [p for p in hl_map_points if p.get("label_id") == label_id]
            as_subset = as_by_map_type[(mid, as_type)]

            as_candidate_counts = Counter()
            first_pass_matches = []
            ambiguous_in_cat = 0
            unmatched_in_cat = 0

            for hp in hl_subset:
                hx = float(hp["x_pos"])
                hy = float(hp["y_pos"])
                target_px = hx * sx + tx
                target_py = hy * sy + ty

                max_dist = mcfg.get("max_distance_px", MAX_DISTANCE_PX)
                close_candidates = []
                for ap in as_subset:
                    dist = math.hypot(ap["x"] - target_px, ap["y"] - target_py)
                    if dist <= max_dist:
                        close_candidates.append((ap["external_id"], dist))

                if len(close_candidates) == 1:
                    best_as_id, dist = close_candidates[0]
                    first_pass_matches.append((hp["id"], best_as_id, dist))
                    as_candidate_counts[best_as_id] += 1
                elif len(close_candidates) > 1:
                    ambiguous_in_cat += 1
                else:
                    unmatched_in_cat += 1

            cat_mapped = 0
            cat_residuals = []
            for hl_id, as_id, dist in first_pass_matches:
                if as_candidate_counts[as_id] == 1:
                    key = f"{mid}:{hl_id}"
                    mapping[key] = as_id
                    cat_mapped += 1
                    cat_residuals.append(dist)
                    residuals.append(dist)
                else:
                    ambiguous_in_cat += 1

            total_ambiguous += ambiguous_in_cat
            total_unmatched += unmatched_in_cat

            categories_stats[cat_name] = {
                "map_id": mid,
                "label_id": label_id,
                "as_type": as_type,
                "total_hl": len(hl_subset),
                "total_as": len(as_subset),
                "mapped": cat_mapped,
                "ambiguous": ambiguous_in_cat,
                "unmatched": unmatched_in_cat,
                "median_residual_px": round(sorted(cat_residuals)[len(cat_residuals) // 2], 2) if cat_residuals else 0.0,
                "max_residual_px": round(max(cat_residuals), 2) if cat_residuals else 0.0,
            }

    # Deterministic sorting of mapping keys by (map_id, point_id)
    def sort_key(k: str) -> tuple[int, int]:
        m, p = k.split(":")
        return int(m), int(p)

    sorted_mapping = {k: mapping[k] for k in sorted(mapping.keys(), key=sort_key)}

    # Ensure every single mapped AppSample ID exists in valid_as_ids
    for k, as_id in sorted_mapping.items():
        if as_id not in valid_as_ids:
            raise ValueError(f"Integrity check failed: mapped ID {as_id} not found in AppSample catalog!")

    # Verify no duplicate AppSample values
    val_counts = Counter(sorted_mapping.values())
    dups = [vid for vid, cnt in val_counts.items() if cnt > 1]
    if dups:
        raise ValueError(f"Integrity check failed: duplicate AppSample IDs in mapping: {dups[:5]}")

    median_res = round(sorted(residuals)[len(residuals) // 2], 2) if residuals else 0.0
    max_res = round(max(residuals), 2) if residuals else 0.0

    return {
        "version": 1,
        "source_catalog_sha256": catalog_sha256,
        "counts": {
            "total_mapped": len(sorted_mapping),
            "total_ambiguous": total_ambiguous,
            "total_unmatched": total_unmatched,
            "median_residual_px": median_res,
            "max_residual_px": max_res,
        },
        "categories": categories_stats,
        "mapping": sorted_mapping,
    }


def verify_index(index_dict: dict, valid_as_ids: set[str]) -> None:
    if index_dict.get("version") != 1:
        raise ValueError("Invalid index version")
    if index_dict.get("source_catalog_sha256") != EXPECTED_CATALOG_SHA256:
        raise ValueError("Index catalog SHA-256 does not match expected canonical catalog")

    mapping = index_dict.get("mapping", {})
    if not isinstance(mapping, dict):
        raise ValueError("Invalid mapping dictionary")

    seen_vals = set()
    for k, v in mapping.items():
        parts = k.split(":")
        if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
            raise ValueError(f"Invalid compound key: {k}")
        if not isinstance(v, str) or not v.isdigit() or len(v) > 32:
            raise ValueError(f"Invalid AppSample target ID format: {v}")
        if v not in valid_as_ids:
            raise ValueError(f"AppSample ID {v} does not exist in catalog")
        if v in seen_vals:
            raise ValueError(f"Duplicate AppSample target ID in mapping: {v}")
        seen_vals.add(v)

    if index_dict.get("counts", {}).get("total_mapped") != len(mapping):
        raise ValueError("Mapping count mismatch")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build and verify HoYoLAB -> AppSample index")
    parser.add_argument("--catalog", type=Path, default=ROOT / "userData/imports/appsample/catalog-9f0c3fe69094909c/catalog.json")
    parser.add_argument("--hoyolab-map2", type=Path, default=ROOT / "userData/cache/hoyolab_map_2.json")
    parser.add_argument("--cache-dir", type=Path, default=ROOT / "userData/cache")
    parser.add_argument("--output", type=Path, default=ROOT / "extensions/hexen-map-exporter/hoyolab-index.json")
    parser.add_argument("--verify", action="store_true", help="Only verify existing index")
    args = parser.parse_args()

    as_points = parse_catalog(json.loads(args.catalog.read_bytes().decode("utf-8")))
    valid_as_ids = {p.external_id for p in as_points}

    if args.verify:
        if not args.output.exists():
            print(f"Error: {args.output} does not exist for verification.")
            return 1
        data = json.loads(args.output.read_bytes().decode("utf-8"))
        verify_index(data, valid_as_ids)
        print(f"Verification successful: {data['counts']['total_mapped']} mappings verified.")
        return 0

    index = build_index(args.catalog, args.hoyolab_map2, args.cache_dir)
    verify_index(index, valid_as_ids)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(index, indent=2, ensure_ascii=False)
    args.output.write_text(raw + "\n", encoding="utf-8")
    print(f"Index successfully written to {args.output}")
    print(f"Total mapped: {index['counts']['total_mapped']}")
    print(f"Total ambiguous (rejected): {index['counts']['total_ambiguous']}")
    print(f"Total unmatched (rejected): {index['counts']['total_unmatched']}")
    print(f"Median residual: {index['counts']['median_residual_px']} px")
    print(f"Max residual: {index['counts']['max_residual_px']} px")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
