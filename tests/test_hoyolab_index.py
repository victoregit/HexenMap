"""Unit tests for the reproducible and verified HoYoLAB -> AppSample index."""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from scripts.build_hoyolab_index import (
    ROOT,
    EXPECTED_CATALOG_SHA256,
    build_index,
    verify_index,
)
from src.live.appsample_import import parse_catalog


@pytest.fixture(scope="module")
def appsample_catalog_points():
    catalog_path = ROOT / "userData/imports/appsample/catalog-9f0c3fe69094909c/catalog.json"
    data = json.loads(catalog_path.read_text(encoding="utf-8"))
    return parse_catalog(data)


@pytest.fixture(scope="module")
def valid_as_id_set(appsample_catalog_points):
    return {p.external_id for p in appsample_catalog_points}


@pytest.fixture(scope="module")
def index_data():
    index_path = ROOT / "extensions/hexen-map-exporter/hoyolab-index.json"
    assert index_path.exists(), "hoyolab-index.json must be generated"
    return json.loads(index_path.read_text(encoding="utf-8"))


def test_hoyolab_index_catalog_hash_and_version(index_data):
    assert index_data.get("version") == 1
    assert index_data.get("source_catalog_sha256") == EXPECTED_CATALOG_SHA256


def test_hoyolab_index_reproducible_and_deterministic():
    catalog_path = ROOT / "userData/imports/appsample/catalog-9f0c3fe69094909c/catalog.json"
    hl_path = ROOT / "userData/cache/hoyolab_map_2.json"
    index1 = build_index(catalog_path, hl_path)
    index2 = build_index(catalog_path, hl_path)
    raw1 = json.dumps(index1, sort_keys=True)
    raw2 = json.dumps(index2, sort_keys=True)
    assert raw1 == raw2


def test_hoyolab_index_keys_and_values_format(index_data, valid_as_id_set):
    mapping = index_data.get("mapping", {})
    assert len(mapping) > 4000
    for k, v in mapping.items():
        parts = k.split(":")
        assert len(parts) == 2, f"Key must be compound: {k}"
        map_id, point_id = parts
        assert map_id.isdigit(), f"map_id must be digit: {map_id}"
        assert point_id.isdigit(), f"point_id must be digit: {point_id}"
        assert isinstance(v, str), f"Value must be str: {v}"
        assert v.isdigit(), f"Value must be numeric decimal string: {v}"
        assert v in valid_as_id_set, f"Target ID {v} does not exist in AppSample catalog"


def test_hoyolab_index_no_duplicate_values_and_no_ambiguity(index_data):
    mapping = index_data.get("mapping", {})
    values = list(mapping.values())
    assert len(values) == len(set(values)), "Mapping must be strictly 1:1 with no duplicate AppSample targets"
    assert "ambiguous" not in values
    assert "" not in values
    assert None not in values


def test_hoyolab_index_residual_bounds(index_data):
    counts = index_data.get("counts", {})
    assert counts.get("total_mapped") == len(index_data["mapping"])
    assert counts.get("median_residual_px") <= 2.5
    assert counts.get("max_residual_px") <= 25.0


def test_hoyolab_index_category_counts_consistent(index_data):
    categories = index_data.get("categories", {})
    expected_categories = {
        # Map 2 (Teyvat)
        "common-chest", "exquisite-chest", "precious-chest", "luxurious-chest", "remarkable-chest",
        "anemoculus", "geoculus", "electroculus", "dendroculus", "hydroculus", "pyroculus",
        # Map 9 (Chasm)
        "chasm-common-chest", "chasm-exquisite-chest", "chasm-precious-chest", "chasm-luxurious-chest",
        # Map 34 (Bygone Eras)
        "bygone-common-chest", "bygone-exquisite-chest", "bygone-precious-chest", "bygone-luxurious-chest",
        "bygone-remarkable-chest", "bygone-hydroculus",
        # Map 36 (Sacred Mountain)
        "sacred-common-chest", "sacred-exquisite-chest", "sacred-precious-chest",
        "sacred-remarkable-chest", "sacred-pyroculus",
        # Map 7 (Enkanomiya - Phase B.1)
        "enkanomiya-common-chest", "enkanomiya-exquisite-chest", "enkanomiya-precious-chest",
        "enkanomiya-luxurious-chest", "enkanomiya-key-sigil-1", "enkanomiya-key-sigil-2",
        "enkanomiya-key-sigil-3", "enkanomiya-key-sigil-4", "enkanomiya-key-sigil-5",
        # Map 37 (Temple of Space - Phase B.2)
        "temple-common-chest", "temple-exquisite-chest", "temple-precious-chest",
        "temple-remarkable-chest",
        # Map 40 (Frost Moon - Phase B.3)
        "moon-common-chest", "moon-exquisite-chest", "moon-precious-chest",
        "moon-luxurious-chest", "moon-lunoculus",
    }
    assert set(categories.keys()) == expected_categories
    total_mapped_sum = sum(c["mapped"] for c in categories.values())
    assert total_mapped_sum == index_data["counts"]["total_mapped"]
    assert index_data["counts"]["total_ambiguous"] > 0
    assert index_data["counts"]["total_unmatched"] > 0


def test_verify_index_helper_accepts_valid_and_rejects_corrupted(index_data, valid_as_id_set):
    # Valid index passes
    verify_index(index_data, valid_as_id_set)

    # Corrupted version raises ValueError
    bad_ver = dict(index_data, version=2)
    with pytest.raises(ValueError, match="Invalid index version"):
        verify_index(bad_ver, valid_as_id_set)

    # Unknown AppSample ID raises ValueError
    bad_mapping = dict(index_data["mapping"])
    bad_mapping["2:999999999"] = "999999999999"
    bad_index = dict(index_data, mapping=bad_mapping)
    with pytest.raises(ValueError, match="does not exist in catalog"):
        verify_index(bad_index, valid_as_id_set)


def test_resort_brisa_tranquila_regional_mapping(index_data):
    """Verify that Resort da Brisa Tranquila markers are strictly mapped to their AppSample counterparts."""
    mapping = index_data.get("mapping", {})
    counts = index_data.get("counts", {})
    assert counts.get("total_mapped") == 4937
    assert sum(1 for k in mapping if k.startswith("2:")) == 4321
    assert sum(1 for k in mapping if k.startswith("9:")) == 90
    assert sum(1 for k in mapping if k.startswith("34:")) == 94
    assert sum(1 for k in mapping if k.startswith("36:")) == 51
    assert sum(1 for k in mapping if k.startswith("7:")) == 186
    assert sum(1 for k in mapping if k.startswith("37:")) == 47
    assert sum(1 for k in mapping if k.startswith("40:")) == 148
    assert counts.get("total_unmatched") == 1

    expected_resort_samples = {
        "2:87035": "87788",  # Luxurious Chest
        "2:87034": "87789",  # Precious Chest
        "2:87033": "87790",  # Exquisite Chest
        "2:86065": "87416",  # Common Chest
        "2:86052": "87429",  # Remarkable Chest
        "2:86034": "87447",  # Pyroculus
    }
    for k, expected_as_id in expected_resort_samples.items():
        assert mapping.get(k) == expected_as_id, f"Resort sample {k} expected {expected_as_id}, got {mapping.get(k)}"

    # Confirm ambiguous cluster (2 adjacent Common chests separated by <5px) are safely excluded
    assert "2:86059" not in mapping
    assert "2:86060" not in mapping


def test_phase_b1_enkanomiya_mapping(index_data):
    """Verify Phase B.1 Enkanomiya (Map 7) mappings, categories, and zero regressions."""
    mapping = index_data.get("mapping", {})
    map7_pairs = {k: v for k, v in mapping.items() if k.startswith("7:")}
    assert len(map7_pairs) == 186

    # Verify known sample mappings across categories
    sample_checks = {
        "7:24379": "27063",  # Common Chest
        "7:21756": "25292",  # Common Chest
        "7:21681": "25367",  # Exquisite Chest
        "7:21680": "25368",  # Exquisite Chest
        "7:22184": "24867",  # Key Sigil 1
        "7:22183": "24868",  # Key Sigil 1
    }
    for k, expected_as_id in sample_checks.items():
        assert mapping.get(k) == expected_as_id, f"Enkanomiya sample {k} expected {expected_as_id}, got {mapping.get(k)}"

    # Confirm strictly unique AppSample target IDs for Map 7
    map7_as_ids = list(map7_pairs.values())
    assert len(map7_as_ids) == len(set(map7_as_ids)), "Map 7 AppSample IDs must be 1:1 with no duplicate targets"


def test_phase_b2_temple_of_space_mapping(index_data):
    """Verify Phase B.2 Temple of Space (Map 37) mappings, categories, and zero regressions."""
    mapping = index_data.get("mapping", {})
    map37_pairs = {k: v for k, v in mapping.items() if k.startswith("37:")}
    assert len(map37_pairs) == 47

    # Verify known sample mappings across categories
    sample_checks = {
        "37:96569": "96388",  # Common Chest
        "37:96593": "96364",  # Precious Chest
        "37:96941": "97530",  # Remarkable Chest
    }
    for k, expected_as_id in sample_checks.items():
        assert mapping.get(k) == expected_as_id, f"Temple of Space sample {k} expected {expected_as_id}, got {mapping.get(k)}"

    # Confirm strictly unique AppSample target IDs for Map 37
    map37_as_ids = list(map37_pairs.values())
    assert len(map37_as_ids) == len(set(map37_as_ids)), "Map 37 AppSample IDs must be 1:1 with no duplicate targets"


def test_phase_b3_frost_moon_mapping(index_data):
    """Verify Phase B.3 Frost Moon (Map 40) mappings, categories, and zero regressions."""
    mapping = index_data.get("mapping", {})
    map40_pairs = {k: v for k, v in mapping.items() if k.startswith("40:")}
    assert len(map40_pairs) == 148

    # Verify known sample mappings across categories
    sample_checks = {
        "40:100285": "100874",  # Common Chest
        "40:99457": "100497",   # Exquisite Chest
        "40:100154": "100743",  # Precious Chest
        "40:99981": "99973",    # Luxurious Chest
        "40:99404": "100550",   # Lunoculus
    }
    for k, expected_as_id in sample_checks.items():
        assert mapping.get(k) == expected_as_id, f"Frost Moon sample {k} expected {expected_as_id}, got {mapping.get(k)}"

    # Confirm strictly unique AppSample target IDs for Map 40
    map40_as_ids = list(map40_pairs.values())
    assert len(map40_as_ids) == len(set(map40_as_ids)), "Map 40 AppSample IDs must be 1:1 with no duplicate targets"
