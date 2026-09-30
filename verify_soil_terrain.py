#!/usr/bin/env python3
"""
🔬 ВЕРИФИКАЦИЯ v2.0 — Почвы и рельеф влияют на симуляцию

Проверки:
  1. Поле с песком СУШЕ, чем с чернозёмом (одинаковый seed)
  2. Рельеф создаёт холмы и впадины
  3. В низинах влажнее, чем на холмах
  4. Почва + рельеф влияют на NDVI и здоровье растений

Запуск:
    python verify_soil_terrain.py
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from field import Field, FieldConfig, SoilType, TerrainGenerator


def print_separator(title: str):
    print()
    print("=" * 65)
    print(f"  {title}")
    print("=" * 65)


def test_soil_moisture_comparison():
    """
    Тест 1: Сравнение влажности разных типов почв.
    Ожидание: песок < глина < чернозём (по влажности).
    """
    print_separator("📊 ТЕСТ 1: Сравнение влажности по типам почв")
    print(f"{'Почва':<15} {'Влажность':<12} {'Здоровье':<12} {'NDVI':<10} {'Крит.зоны':<12}")
    print("-" * 65)

    results = []
    for soil in [SoilType.CHERNOZEM, SoilType.CLAY, SoilType.SAND]:
        config = FieldConfig(
            width=100, height=100, seed=42,
            soil_type=soil,
            terrain_enabled=False,  # без рельефа — чистый тест почв
        )
        field = Field(config)
        summary = field.get_health_summary()
        results.append({
            'soil': soil.value,
            'moisture': summary['mean_moisture'],
            'health': summary['mean_health'],
            'ndvi': summary['mean_ndvi'],
            'critical': summary['critical_areas'],
        })
        print(f"{soil.value:<15} {summary['mean_moisture']:<12.1%} "
              f"{summary['mean_health']:<12.1%} {summary['mean_ndvi']:<10.3f} "
              f"{summary['critical_areas']:<12}")

    # Проверка: песок суше чернозёма
    sand_m = [r['moisture'] for r in results if r['soil'] == 'песок'][0]
    chernozem_m = [r['moisture'] for r in results if r['soil'] == 'чернозём'][0]
    clay_m = [r['moisture'] for r in results if r['soil'] == 'глина'][0]

    assert sand_m < clay_m, (
        f"❌ Ошибка: песок ({sand_m:.1%}) не суше глины ({clay_m:.1%})!"
    )
    assert clay_m < chernozem_m, (
        f"❌ Ошибка: глина ({clay_m:.1%}) не суше чернозёма ({chernozem_m:.1%})!"
    )
    assert sand_m < chernozem_m, (
        f"❌ Ошибка: песок ({sand_m:.1%}) не суше чернозёма ({chernozem_m:.1%})!"
    )

    print(f"\n✅ Верификация пройдена: песок ({sand_m:.1%}) < глина ({clay_m:.1%}) < "
          f"чернозём ({chernozem_m:.1%}) по влажности")

    # Проверка по здоровью: чернозём > глина > песок
    sand_h = [r['health'] for r in results if r['soil'] == 'песок'][0]
    chernozem_h = [r['health'] for r in results if r['soil'] == 'чернозём'][0]
    assert chernozem_h > sand_h, (
        f"❌ Ошибка: чернозём ({chernozem_h:.1%}) не здоровее песка ({sand_h:.1%})!"
    )
    print(f"✅ Чернозём ({chernozem_h:.1%}) здоровее песка ({sand_h:.1%})")

    return results


def test_terrain_generation():
    """
    Тест 2: Проверка генерации 3D рельефа.
    Ожидание: есть холмы (elevation > 0.7) и впадины (elevation < 0.3).
    """
    print_separator("🏔️ ТЕСТ 2: Генерация 3D рельефа")

    terrain = TerrainGenerator(rows=100, cols=100, seed=42, octaves=4)
    elev = terrain.elevation_map

    print(f"   Размер: {terrain.rows}x{terrain.cols}")
    print(f"   Мин. высота: {elev.min():.3f}")
    print(f"   Макс. высота: {elev.max():.3f}")
    print(f"   Средняя высота: {elev.mean():.3f}")

    has_hills = float(elev.max()) > 0.7
    has_valleys = float(elev.min()) < 0.3
    has_variation = float(elev.std()) > 0.1

    print(f"   Есть холмы (>0.7):     {'✅' if has_hills else '❌'} ({elev.max():.3f})")
    print(f"   Есть впадины (<0.3):   {'✅' if has_valleys else '❌'} ({elev.min():.3f})")
    print(f"   Достаточная вариация:  {'✅' if has_variation else '❌'} (σ={elev.std():.3f})")

    assert has_hills, "❌ Нет холмов! Максимальная высота слишком низкая."
    assert has_valleys, "❌ Нет впадин! Минимальная высота слишком высокая."
    assert has_variation, "❌ Недостаточная вариация рельефа!"

    print(f"\n✅ Рельеф успешно генерирует холмы и впадины")

    return terrain


def test_terrain_affects_moisture():
    """
    Тест 3: Влияние рельефа на влажность.
    Ожидание: низины влажнее холмов.
    """
    print_separator("💧 ТЕСТ 3: Рельеф влияет на влажность")

    # Поле с рельефом
    config = FieldConfig(
        width=100, height=100, seed=42,
        soil_type=SoilType.CHERNOZEM,
        terrain_enabled=True,
    )
    field = Field(config)

    # Собираем точки по высоте
    low_points = field.elevation_map < 0.3  # низины
    high_points = field.elevation_map > 0.7  # холмы

    low_moisture = field.moisture_map[low_points].mean() if low_points.any() else 0
    high_moisture = field.moisture_map[high_points].mean() if high_points.any() else 0
    mid_moisture = field.moisture_map[(field.elevation_map >= 0.3) & (field.elevation_map <= 0.7)].mean()

    print(f"   Низины (высота<0.3): влажность {low_moisture:.1%}  ({low_points.sum()} кл.)")
    print(f"   Средний уровень:     влажность {mid_moisture:.1%}")
    print(f"   Холмы (высота>0.7):  влажность {high_moisture:.1%}  ({high_points.sum()} кл.)")

    assert low_moisture > high_moisture, (
        f"❌ Ошибка: низины ({low_moisture:.1%}) не влажнее холмов ({high_moisture:.1%})!"
    )
    print(f"\n✅ Рельеф влияет на влажность: в низинах ({low_moisture:.1%}) "
          f"влажнее, чем на холмах ({high_moisture:.1%})")


def test_soil_terrain_combined():
    """
    Тест 4: Совместное влияние почвы и рельефа.
    Ожидание: чернозём в низине > песок на холме (по влажности и здоровью).
    """
    print_separator("🧪 ТЕСТ 4: Совместное влияние почвы и рельефа")

    # Поле: чернозём с рельефом
    config_good = FieldConfig(
        width=100, height=100, seed=42,
        soil_type=SoilType.CHERNOZEM,
        terrain_enabled=True,
    )
    field_good = Field(config_good)

    # Поле: песок с рельефом
    config_bad = FieldConfig(
        width=100, height=100, seed=42,
        soil_type=SoilType.SAND,
        terrain_enabled=True,
    )
    field_bad = Field(config_bad)

    # Поле: глина с рельефом
    config_mid = FieldConfig(
        width=100, height=100, seed=42,
        soil_type=SoilType.CLAY,
        terrain_enabled=True,
    )
    field_mid = Field(config_mid)

    print(f"{'Почва':<15} {'Влажность':<12} {'Здоровье':<12} {'NDVI':<10}")
    print("-" * 55)
    for name, f in [('чернозём', field_good), ('глина', field_mid), ('песок', field_bad)]:
        s = f.get_health_summary()
        print(f"{name:<15} {s['mean_moisture']:<12.1%} {s['mean_health']:<12.1%} "
              f"{s['mean_ndvi']:<10.3f}")

    # Проверка
    assert field_good.get_health_summary()['mean_moisture'] > field_bad.get_health_summary()['mean_moisture']
    assert field_good.get_health_summary()['mean_health'] > field_bad.get_health_summary()['mean_health']

    print(f"\n✅ Почва + рельеф совместно влияют на параметры поля")


def test_moisture_elevation_correlation():
    """
    Тест 5: Корреляция влажности и высоты.
    Ожидание: отрицательная корреляция (выше = суше).
    """
    print_separator("📈 ТЕСТ 5: Корреляция влажность-высота")

    config = FieldConfig(
        width=100, height=100, seed=42,
        soil_type=SoilType.CHERNOZEM,
        terrain_enabled=True,
    )
    field = Field(config)

    # Вычисляем корреляцию Пирсона между высотой и влажностью
    elev_flat = field.elevation_map.flatten()
    moist_flat = field.moisture_map.flatten()

    correlation = float(np.corrcoef(elev_flat, moist_flat)[0, 1])

    print(f"   Корреляция высота-влажность: {correlation:.3f}")
    print(f"   (Отрицательное значение = выше = суше)")

    assert correlation < -0.1, (
        f"❌ Слабая корреляция: {correlation:.3f} (ожидалось < -0.1)"
    )
    print(f"✅ Выявлена отрицательная корреляция ({correlation:.3f}): "
          f"с ростом высоты влажность снижается")


if __name__ == "__main__":
    import numpy as np

    print("=" * 65)
    print("  🔬 ВЕРИФИКАЦИЯ v2.0: Почвы и 3D рельеф")
    print("=" * 65)

    all_passed = True

    try:
        # Тест 1: Почвы
        r1 = test_soil_moisture_comparison()

        # Тест 2: Рельеф
        r2 = test_terrain_generation()

        # Тест 3: Рельеф → влажность
        test_terrain_affects_moisture()

        # Тест 4: Почва + рельеф
        test_soil_terrain_combined()

        # Тест 5: Корреляция
        test_moisture_elevation_correlation()

        print()
        print("=" * 65)
        print("  ✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ")
        print("  Почвы и 3D рельеф корректно влияют на симуляцию")
        print("=" * 65)

    except AssertionError as e:
        print(f"\n❌ {e}")
        all_passed = False

    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        all_passed = False

    if not all_passed:
        print("\n❌ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОЙДЕНЫ")
        sys.exit(1)
