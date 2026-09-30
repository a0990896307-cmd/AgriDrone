# Agri-Drone Analytics Engine

> Field health analytics for agricultural drones — NDVI crop-health mapping,
> soil-type modelling, 3D terrain influence, problem-zone detection and
> agronomic recommendations.

A Python engine that simulates and analyses drone flights over agricultural
fields: it generates realistic crop data, maps vegetation health, models how
soil and terrain affect plant growth, and flags the areas that need attention.

---

## Highlights

| Module | What it does |
|---|---|
| **`field.py`** | Field generator: realistic NDVI ranges per crop, soil types (chernozem / sand / clay) with moisture retention coefficients, 3D terrain (hills, depressions) |
| **`analytics.py`** | Health maps, problem-zone detection, agronomic recommendations |
| **`drone.py`** | Drone flight path, scanning, battery/mission logic |
| **`visualizer.py`** | Field visualisation, interactive web map |
| **`run_mission.py`** | Full mission: fly → scan → analyse → report |
| **`scenarios.py`** | Predefined scenarios (drought, pest outbreak, nutrient deficiency) |
| **`verify_soil_terrain.py`** | Verification suite for soil and terrain models |

---

## Crop NDVI ranges

Realistic per-crop vegetation index ranges, not one flat threshold:

| Crop | NDVI range |
|---|---|
| Wheat | 0.60 – 0.85 |
| Potato | 0.50 – 0.80 |
| Sugar beet | 0.55 – 0.90 |

---

## Soil model

Soil type changes how fast water is lost — this directly affects NDVI and
plant health:

| Soil | Moisture retention |
|---|---|
| Chernozem | high — fertile, holds water |
| Sand | low — drains fast, dries out |
| Clay | medium — compact, slow drainage |

---

## Terrain influence

Terrain class (hills, depressions) is generated per field and affects light
exposure, water accumulation and therefore crop health on the map.

---

## Quick start

```bash
git clone https://github.com/a0990896307-cmd/AgriDrone.git
cd AgriDrone
pip install -r requirements.txt

python -m run_mission        # run a full mission
python -m scenarios          # run predefined scenarios
```

---

## What I can build for you

- Drone data processing pipelines (NDVI, NDWI, vegetation indices)
- Field health dashboards and interactive maps
- Agronomic analytics and recommendation engines
- Simulation models for crop and soil behaviour
- Custom ML classifiers for crop disease detection

**Contact:** Alexander L — Python & AI Developer

---

## Stack

Python · NumPy · data visualization · FastAPI (web map)

---

## License

MIT — see `LICENSE`.
