"""
Модуль поля — виртуальное сельскохозяйственное поле.
Генерирует карту здоровья растений, влажности, вредителей и т.д.
Поддерживает реалистичные NDVI-диапазоны для разных культур.

v2.0 — Добавлены:
  - Типы почв: чернозём, песок, глина (влияют на влажность)
  - 3D рельеф: класс TerrainGenerator (холмы, впадины)
  - Рельеф и почва влияют на NDVI/здоровье растений
"""

import numpy as np
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Tuple, Optional


# NDVI-диапазоны для реальных сельскохозяйственных культур
# (min_ndvi, max_ndvi) — типичные значения для здорового поля
CROP_NDVI_RANGES: dict[str, Tuple[float, float]] = {
    'wheat':       (0.60, 0.85),   # Пшеница — плотный полог, высокий NDVI
    'potato':      (0.50, 0.80),   # Картофель — умеренный полог
    'sugar_beet':  (0.55, 0.90),   # Сахарная свёкла — широкий диапазон
}


class SoilType(Enum):
    """Типы почв с коэффициентом удержания влаги.
    
    Коэффициент > 1.0 — почва удерживает влагу лучше базового уровня.
    Коэффициент < 1.0 — почва быстро теряет влагу (песок).
    """
    CHERNOZEM = 'чернозём'     # плодородная, отлично держит влагу
    SAND      = 'песок'        # быстро пропускает воду, сухая
    CLAY      = 'глина'        # плотная, медленно пропускает воду

    @property
    def moisture_factor(self) -> float:
        """Коэффициент удержания влаги относительно базовой влажности."""
        return {
            SoilType.CHERNOZEM: 1.25,   # чернозём держит влагу лучше всех
            SoilType.SAND:      0.50,   # песок почти не держит влагу
            SoilType.CLAY:      0.85,   # глина — средний вариант
        }[self]

    @property
    def fertility(self) -> float:
        """Базовое плодородие почвы (0..1), влияет на здоровье растений."""
        return {
            SoilType.CHERNOZEM: 0.90,
            SoilType.SAND:      0.35,
            SoilType.CLAY:      0.55,
        }[self]

    @staticmethod
    def random(seed: Optional[int] = None) -> 'SoilType':
        """Случайный тип почвы с seed-контролем."""
        rng = random.Random(seed)
        return rng.choice(list(SoilType))


class TerrainGenerator:
    """
    Генератор 3D рельефа поля методом Value Noise с несколькими октавами.
    
    Создаёт реалистичный ландшафт с холмами и впадинами.
    Высота в каждой точке влияет на влажность и здоровье растений.
    
    Features:
    - Многооктавный шум для естественного рельефа
    - Холмы (высокие точки) — более сухие
    - Впадины (низкие точки) — собирают влагу
    - Нормированная высота: 0.0 (впадина) … 1.0 (вершина холма)
    """

    def __init__(self, rows: int, cols: int, seed: Optional[int] = None,
                 octaves: int = 4, scale: float = 15.0,
                 amplitude: float = 1.0, roughness: float = 0.5):
        """
        Parameters
        ----------
        rows, cols : int
            Размеры карты высот.
        seed : int or None
            Сид для воспроизводимости.
        octaves : int
            Количество октав шума (больше = детальнее рельеф).
        scale : float
            Масштаб шума (больше = более пологие формы).
        amplitude : float
            Амплитуда (макс. высота рельефа).
        roughness : float
            Шероховатость — как быстро убывает амплитуда с октавами.
        """
        self.rows = rows
        self.cols = cols
        self.seed = seed or 0
        self.octaves = octaves
        self.scale = scale
        self.amplitude = amplitude
        self.roughness = roughness

        self._generate()

    def _smooth_noise_2d(self, xs: np.ndarray, ys: np.ndarray,
                         grid_size: int, offset: Tuple[float, float]) -> np.ndarray:
        """
        Билинейно интерполированный Value Noise на сетке grid_size x grid_size.
        """
        ox, oy = offset
        # Целые координаты углов
        ix = np.floor((xs + ox) / self.scale * grid_size).astype(int)
        iy = np.floor((ys + oy) / self.scale * grid_size).astype(int)

        # Дробная часть для интерполяции
        fx = ((xs + ox) / self.scale * grid_size) - ix
        fy = ((ys + oy) / self.scale * grid_size) - iy

        # Случайная сетка
        rng = np.random.default_rng(self.seed + grid_size + int(ox * 100) + int(oy * 100))
        grid = rng.random((grid_size + 2, grid_size + 2))

        ix = ix % (grid_size + 1)
        iy = iy % (grid_size + 1)

        # Четыре угла
        v00 = grid[iy, ix]
        v10 = grid[iy, ix + 1]
        v01 = grid[iy + 1, ix]
        v11 = grid[iy + 1, ix + 1]

        # Гладкая ступень (smoothstep)
        sx = fx * fx * (3 - 2 * fx)
        sy = fy * fy * (3 - 2 * fy)

        # Билинейная интерполяция
        top = v00 + (v10 - v00) * sx
        bottom = v01 + (v11 - v01) * sx
        return top + (bottom - top) * sy

    def _generate(self):
        """Генерирует карту высот через суммирование октав."""
        xs, ys = np.meshgrid(np.arange(self.cols), np.arange(self.rows))

        elevation = np.zeros((self.rows, self.cols))
        max_val = 0.0

        for octave in range(self.octaves):
            grid_size = 2 ** (octave + 2)  # 4, 8, 16, 32...
            amp = self.amplitude * (self.roughness ** octave)
            offset = (octave * 31.7, octave * 73.1)  # сдвиг для разнообразия октав

            noise = self._smooth_noise_2d(xs, ys, grid_size, offset)
            elevation += amp * noise
            max_val += amp

        # Нормируем в [0, 1]
        self.elevation_map = np.clip(elevation / max_val, 0.0, 1.0)

    def get_elevation(self, x: int, y: int) -> float:
        """Возвращает высоту в конкретной точке [0, 1]."""
        if 0 <= x < self.cols and 0 <= y < self.rows:
            return float(self.elevation_map[y, x])
        return 0.5

    def slope(self, x: int, y: int) -> float:
        """Возвращает крутизну склона [0, 1] в точке."""
        if not (0 < x < self.cols - 1 and 0 < y < self.rows - 1):
            return 0.0
        gx = self.elevation_map[y, min(x + 1, self.cols - 1)] - self.elevation_map[y, max(x - 1, 0)]
        gy = self.elevation_map[min(y + 1, self.rows - 1), x] - self.elevation_map[max(y - 1, 0), x]
        return float(np.clip(np.sqrt(gx ** 2 + gy ** 2), 0.0, 1.0))

    def __repr__(self) -> str:
        return (
            f"TerrainGenerator({self.rows}x{self.cols}, "
            f"octaves={self.octaves}, scale={self.scale}, "
            f"elevation=[{self.elevation_map.min():.2f}–{self.elevation_map.max():.2f}])"
        )


@dataclass
class FieldConfig:
    """Конфигурация поля"""
    width: int = 100          # метры
    height: int = 100         # метры
    resolution: float = 1.0   # метров на клетку
    seed: Optional[int] = None
    crop_type: str = 'wheat'      # тип культуры: wheat, potato, sugar_beet
    soil_type: SoilType = SoilType.CHERNOZEM  # тип почвы
    terrain_enabled: bool = True   # включить ли 3D рельеф
    terrain_octaves: int = 4       # детализация рельефа
    terrain_scale: float = 15.0    # масштаб неровностей


class Field:
    """
    Виртуальное поле с различными зонами здоровья растений.
    Значения:
      0.0 - мёртвая зона
      0.5 - среднее здоровье
      1.0 - отличное здоровье

    NDVI (ndvi_map) масштабируется под конкретную культуру:
      wheat      — 0.60–0.85
      potato     — 0.50–0.80
      sugar_beet — 0.55–0.90

    Новое в v2.0:
      - Тип почвы (soil_type) влияет на влажность и плодородие
      - 3D рельеф (terrain) создаёт холмы и впадины
      - Влажность зависит от высоты: в низинах влажнее, на холмах суше
      - Здоровье растений зависит от почвы и рельефа
    """

    def __init__(self, config: FieldConfig = None):
        self.config = config or FieldConfig()
        self.rows = int(self.config.height / self.config.resolution)
        self.cols = int(self.config.width / self.config.resolution)

        if self.config.seed is not None:
            np.random.seed(self.config.seed)
            random.seed(self.config.seed)

        # --- 3D рельеф ---
        if self.config.terrain_enabled:
            self.terrain = TerrainGenerator(
                rows=self.rows, cols=self.cols,
                seed=self.config.seed,
                octaves=self.config.terrain_octaves,
                scale=self.config.terrain_scale,
            )
            self.elevation_map = self.terrain.elevation_map
        else:
            self.terrain = None
            # Без рельефа — ровная поверхность на 0.5
            self.elevation_map = np.full((self.rows, self.cols), 0.5)

        # --- Основные карты ---
        # Генерируем базовый ландшафт здоровья (0–1)
        self.health_map = self._generate_health()

        # Масштабируем NDVI под выбранную культуру
        self.ndvi_map = self._apply_crop_params()

        # Генерируем карту влажности (теперь зависит от почвы + рельефа)
        self.moisture_map = self._generate_moisture()

        # Генерируем очаги проблем (сорняки, вредители, болезни)
        self.problem_spots = self._generate_problems()

    # ──────────────────────────────────────────
    # Внутренние методы
    # ──────────────────────────────────────────

    def _apply_crop_params(self) -> np.ndarray:
        """
        Масштабирует health_map (0..1) в реалистичный NDVI-диапазон
        для выбранной культуры.

        Returns
        -------
        np.ndarray
            ndvi_map — спектральный индекс, соответствующий crop_type.
        """
        if self.config.crop_type not in CROP_NDVI_RANGES:
            raise ValueError(
                f"Неизвестный тип культуры: '{self.config.crop_type}'. "
                f"Доступные: {list(CROP_NDVI_RANGES.keys())}"
            )

        ndvi_min, ndvi_max = CROP_NDVI_RANGES[self.config.crop_type]
        # Линейное масштабирование: health [0, 1] → NDVI [ndvi_min, ndvi_max]
        return ndvi_min + self.health_map * (ndvi_max - ndvi_min)

    def _generate_health(self) -> np.ndarray:
        """Генерирует карту здоровья растений на поле.
        
        Учитывает:
        - Базовый случайный ландшафт (как раньше)
        - Пятна хороших/плохих зон
        - Плодородие почвы (через self.config.soil_type.fertility)
        - Влияние рельефа (на склонах растениям хуже)
        """
        # База — случайный ландшафт
        base = np.random.rand(self.rows, self.cols)

        # Добавляем крупные "пятна" хороших и плохих зон
        for _ in range(random.randint(3, 8)):
            cx = random.randint(0, self.cols - 1)
            cy = random.randint(0, self.rows - 1)
            radius = random.randint(5, 20)
            value = random.choice([0.1, 0.3, 0.8, 0.95])
            for y in range(max(0, cy - radius), min(self.rows, cy + radius)):
                for x in range(max(0, cx - radius), min(self.cols, cx + radius)):
                    dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
                    if dist < radius:
                        influence = 1.0 - (dist / radius)
                        base[y, x] = base[y, x] * (1 - influence) + value * influence

        # --- Влияние почвы ---
        soil_fert = self.config.soil_type.fertility
        # Почва задаёт базовый уровень: плодородная почва = выше здоровье
        base = base * 0.4 + soil_fert * 0.6

        # --- Влияние рельефа ---
        # На крутых склонах эрозия, растениям хуже
        if self.terrain is not None:
            for y in range(self.rows):
                for x in range(self.cols):
                    s = self.terrain.slope(x, y)
                    # Пологий склон (0–0.1) — почти не влияет
                    # Крутой склон (>0.3) — сильно снижает здоровье
                    slope_penalty = s * 0.5
                    base[y, x] = max(0.0, base[y, x] - slope_penalty)

        # Добавляем шум
        noise = np.random.normal(0, 0.05, (self.rows, self.cols))
        health = np.clip(base + noise, 0.0, 1.0)

        return health

    def _generate_moisture(self) -> np.ndarray:
        """Генерирует карту влажности почвы.
        
        Учитывает:
        - Базовую корреляцию со здоровьем (как раньше)
        - Тип почвы (soil_type.moisture_factor)
        - Рельеф: в низинах влажно, на холмах сухо
        """
        # Базовая влажность (коррелирует со здоровьем + шум)
        moisture = self.health_map + np.random.normal(0, 0.15, (self.rows, self.cols))

        # --- Влияние типа почвы ---
        moisture = moisture * self.config.soil_type.moisture_factor

        # --- Влияние рельефа ---
        # Низины (elevation ≈ 0) — влажно
        # Холмы (elevation ≈ 1) — сухо
        terrain_moisture = 1.0 - self.elevation_map  # 1 в низине, 0 на холме
        # Смешиваем: 70% базовая влажность, 30% от рельефа
        moisture = moisture * 0.7 + terrain_moisture * 0.3

        return np.clip(moisture, 0.0, 1.0)

    def _generate_problems(self) -> list:
        """Генерирует список проблемных зон (очаги болезней/вредителей)"""
        problems = []
        for _ in range(random.randint(2, 5)):
            problems.append({
                'x': random.randint(0, self.cols - 1),
                'y': random.randint(0, self.rows - 1),
                'radius': random.randint(3, 10),
                'severity': random.uniform(0.3, 0.9),
                'type': random.choice(['pest', 'weed', 'disease', 'dryness'])
            })
        return problems

    # ──────────────────────────────────────────
    # Публичные методы
    # ──────────────────────────────────────────

    def get_cell_data(self, x: int, y: int) -> dict:
        """Возвращает данные конкретной клетки поля"""
        if not (0 <= x < self.cols and 0 <= y < self.rows):
            return None
        return {
            'health': float(self.health_map[y, x]),
            'ndvi': float(self.ndvi_map[y, x]),
            'moisture': float(self.moisture_map[y, x]),
            'crop': self.config.crop_type,
            'soil_type': self.config.soil_type.value,
            'elevation': float(self.elevation_map[y, x]),
            'slope': float(self.terrain.slope(x, y)) if self.terrain else 0.0,
            'position': (x, y),
        }

    def get_health_summary(self) -> dict:
        """Возвращает сводку по здоровью поля"""
        return {
            'mean_health': float(np.mean(self.health_map)),
            'mean_ndvi': float(np.mean(self.ndvi_map)),
            'mean_moisture': float(np.mean(self.moisture_map)),
            'crop_type': self.config.crop_type,
            'soil_type': self.config.soil_type.value,
            'terrain_enabled': self.config.terrain_enabled,
            'ndvi_range': CROP_NDVI_RANGES.get(self.config.crop_type, (0.0, 1.0)),
            'critical_areas': int(np.sum(self.health_map < 0.3)),
            'good_areas': int(np.sum(self.health_map > 0.7)),
            'total_cells': self.rows * self.cols,
            'problem_spots': len(self.problem_spots),
            'elevation_range': (
                float(np.min(self.elevation_map)),
                float(np.max(self.elevation_map)),
            ) if self.elevation_map.size > 0 else (0.0, 0.0),
        }

    def __repr__(self) -> str:
        crop = self.config.crop_type
        soil = self.config.soil_type.value
        return (
            f"Field({self.cols}x{self.rows}, "
            f"crop={crop}, soil={soil}, "
            f"NDVI: {np.mean(self.ndvi_map):.2f})"
        )
