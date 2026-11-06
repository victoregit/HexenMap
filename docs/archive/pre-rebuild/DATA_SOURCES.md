# Data Sources, Licensing Audit & Extensible Importer Architecture

## 1. Marker Dataset Audit

Interactive maps for Genshin Impact rely on geographic exploration data (Oculi, Chests, Shrines, Challenges, Mineral Outcrops, Local Specialties). This section audits the primary existing data sources, evaluating their licensing, terms of service, and redistribution legality.

| Data Source | Curator / Platform | Data Completeness | Terms of Service / Restrictions | Redistribution Legality |
| :--- | :--- | :--- | :--- | :--- |
| **HoYoLAB Official Teyvat Map** | miHoYo / Cognosphere | 100% Official (Synchronized with game patches) | HoYoLAB Terms of Service prohibit unauthorized scraping, automated harvesting, and commercial exploitation. API endpoints require account authentication / cookie tokens. | **Non-Redistributable**: Raw proprietary game database. Scraping is subject to rate-limiting and copyright infringement claims. Direct bundled inclusion prohibited. |
| **Kongying Tavern (YuanShen.site)** | Kongying Tavern Community | Extremely high (~40,000+ points across all nations) | Community crowdsourced. Marker data distributed under CC-BY-NC-SA 4.0 (Creative Commons Non-Commercial Share-Alike) or MulanPSL depending on endpoint. | **Conditionally Redistributable**: Usable for non-commercial open-source tools with attribution to Kongying Tavern. |
| **Teyvat.moe Dataset** | EliteMasterEric | Covers Mondstadt, Liyue, Dragonspine, Inazuma | GPL-3.0 licensed repository with JSON dumps of marker locations. Archived and no longer maintained for newer nations. | **Copyleft Risk**: Data extraction must ensure clean separation from code to avoid GPL-3.0 virality. |
| **Genshin Gem Wish Demo Dataset** | Independent Clean-Room | Curated 50-point reference set | MIT License. Independently created coordinate approximations for Mondstadt and Liyue. | **100% Permissive**: Freely redistributable, modifiable, and usable for automated tests. |

---

## 2. Terms of Service & Legal Compliance Assessment

### 2.1 HoYoLAB Official Map Scraping Policy
- **Legal Risk**: High if bundled directly. HoYoLAB's terms explicitly state that all visual assets, coordinate structures, and API endpoints are proprietary property of Cognosphere PTE. LTD.
- **Sanctioned Approach**: The application does **not** scrape or bundle unauthorized proprietary HoYoLAB dumps. Instead, users may optionally import their own personal data or export personal bookmarks via pluggable importers.

### 2.2 Crowdsourced Marker Licensing
- Community projects like Kongying Tavern allow non-commercial usage provided attribution is prominently given.
- Any tool utilizing crowdsourced datasets must clearly credit the respective community map teams and respect CC-BY-NC-SA terms.

---

## 3. Standard JSON Marker Schema Specification

To decouple the application engine from external data formats, a normalized, schema-validated JSON specification is established:

```json
{
  "version": "1.0.0",
  "metadata": {
    "title": "Dataset Title",
    "description": "Exploration items and points of interest",
    "created_at": "ISO-8601 Timestamp",
    "total_markers": 50
  },
  "layers": [
    {
      "id": "surface",
      "name": "Teyvat Surface",
      "description": "Standard overworld terrain"
    },
    {
      "id": "underground",
      "name": "Underground / Caverns",
      "description": "Subterranean caves and ruins"
    }
  ],
  "categories": [
    {
      "id": "anemoculus",
      "name": "Anemoculus",
      "group": "Oculi",
      "color": "#6fe7c8",
      "icon": "anemoculus"
    }
  ],
  "regions": [
    {
      "id": "mondstadt",
      "name": "Mondstadt",
      "bounds": {
        "min_x": -3000.0,
        "min_y": -4000.0,
        "max_x": 1000.0,
        "max_y": 0.0
      }
    }
  ],
  "markers": [
    {
      "id": "mond_oculi_001",
      "name": "Anemoculus - Windrise Tree Branch",
      "category_id": "anemoculus",
      "region_id": "mondstadt",
      "layer": "surface",
      "coordinates": {
        "x": -818.0,
        "y": -2212.0,
        "z": 38.0
      },
      "description": "High on the southern branch of the great oak at Windrise.",
      "tags": ["oculi", "windrise"]
    }
  ]
}
```

### Schema Field Constraints
- `id` (string, required): Globally unique identifier (e.g. `reg_cat_001`).
- `name` (string, required): Human-readable name.
- `category_id` (string, required): Must match an existing entry in `categories`.
- `region_id` (string, required): Must match an entry in `regions`.
- `layer` (string, default: `"surface"`): Distinguishes subterranean (`"underground"`) from overworld (`"surface"`).
- `coordinates` (object, required):
  - `x` (float, required): Horizontal world coordinate.
  - `y` (float, required): Vertical world coordinate.
  - `z` (float, optional): Elevation / altitude in game units.
- `description` (string, optional): Clue, puzzle requirement, or collection guide.
- `tags` (array of strings, optional): Keyword search descriptors.

---

## 4. Pluggable Data Importer Interface

An extensible Python interface enables pluggable ingestion from external formats into the standard internal repository schema:

```python
from abc import ABC, abstractmethod
from typing import Any, Dict, List
from src.markers.models import Marker, MarkerCategory, RegionInfo

class BaseMarkerImporter(ABC):
    """Abstract base class for third-party marker dataset importers."""

    @abstractmethod
    def parse_source(self, raw_data: Any) -> Dict[str, Any]:
        """Convert external payload into standard Genshin Gem Wish schema dictionary."""
        pass

    @abstractmethod
    def fetch_remote(self, url: str) -> Dict[str, Any]:
        """Fetch and return standard schema dictionary from a remote endpoint."""
        pass
```
