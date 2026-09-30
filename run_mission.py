#!/usr/bin/env python3
"""
🚁 Агро-дрон: Симуляция миссии v2.0
Добавлены типы почв, 3D рельеф и их влияние на здоровье растений.

Запуск:
    python run_mission.py

Результаты:
    - field_analysis.png      — композитные графики (включая рельеф)
    - drone_view.png          — вид с дрона
    - terrain_3d.png          — 3D визуализация рельефа
    - report.txt              — текстовый отчёт (включая анализ почв)
"""

import sys
import os
import time

# Добавляем путь для импорта модулей
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from field import Field, FieldConfig, SoilType
from drone import Drone
from analytics import FieldAnalytics
from visualizer import plot_field_health, plot_drone_view, plot_terrain_3d


def main():
    print("=" * 55)
    print("  🌾 АГРО-ДРОН СИМУЛЯТОР v2.0")
    print("  Концепция: \"Компания как Apple\" — агро-экосистема")
    print("  🆕 Почвы + 3D рельеф + влияние на NDVI")
    print("=" * 55)

    # 1. Создаём поле 100x100 метров с чернозёмом и рельефом
    print("\n🌱 Генерация поля...")
    config = FieldConfig(
        width=100, height=100, seed=42,
        soil_type=SoilType.CHERNOZEM,
        terrain_enabled=True,
        terrain_octaves=4,
        terrain_scale=15.0,
    )
    field = Field(config)
    print(f"   Поле: {field}")
    summary = field.get_health_summary()
    print(f"   Почва: {config.soil_type.value}")
    print(f"   Рельеф: высота {summary['elevation_range'][0]:.2f}–{summary['elevation_range'][1]:.2f}")
    print(f"   Здоровье поля: среднее {summary['mean_health']:.1%}")
    print(f"   Влажность: {summary['mean_moisture']:.1%}")
    print(f"   Проблемных зон: {summary['problem_spots']}")

    # 2. Создаём дрон
    drone = Drone(
        field_width=field.config.width,
        field_height=field.config.height,
        speed=3.0,           # 3 м/с
        scan_width=5.0,      # захват 5 метров
        battery_capacity=100.0  # 100 минут
    )

    # 3. Планируем маршрут
    print("\n🗺️  Планирование маршрута...")
    route = drone.plan_route_lawnmower()
    print(f"   Маршрут: {len(route)} путевых точек")

    # 4. Запускаем миссию
    print(f"\n{'=' * 55}")
    print(f"  🚁 ЗАПУСК МИССИИ")
    print(f"{'=' * 55}")
    start_time = time.time()

    scan_data = drone.execute_mission(field)
    if not scan_data:
        print("\n❌ Миссия не выполнилась. Данных нет.")
        return

    elapsed = time.time() - start_time
    print(f"\n⏱  Реальное время симуляции: {elapsed:.2f} сек")

    # 5. Аналитика
    print(f"\n{'=' * 55}")
    print(f"  📊 АНАЛИТИКА ПОЛЯ v2.0")
    print(f"{'=' * 55}")

    analytics = FieldAnalytics(scan_data)
    report = analytics.generate_report()
    print()
    print(report)

    # Сохраняем отчёт
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    report_path = os.path.join(base_dir, "reports", "mission_report.txt")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"\n  📄 Отчёт сохранён: {report_path}")

    # План лечения
    treatment = analytics.get_treatment_plan()
    print(f"\n💊 Рекомендуемых действий: {len(treatment)}")
    for t in treatment[:5]:  # первые 5
        print(f"   - [{t['priority']}] ({t['x']:.0f}, {t['y']:.0f}) [{t['soil_type']}]: {t['action']}")

    # 6. Визуализация
    print(f"\n{'=' * 55}")
    print(f"  📈 ВИЗУАЛИЗАЦИЯ v2.0")
    print(f"{'=' * 55}")

    reports_dir = os.path.join(base_dir, "reports")
    os.makedirs(reports_dir, exist_ok=True)

    plot_field_health(
        field, scan_data, route,
        save_path=os.path.join(reports_dir, "field_analysis.png")
    )
    plot_drone_view(
        field, scan_data,
        save_path=os.path.join(reports_dir, "drone_view.png")
    )
    plot_terrain_3d(
        field,
        save_path=os.path.join(reports_dir, "terrain_3d.png")
    )

    print(f"\n{'=' * 55}")
    print(f"  ✅ МИССИЯ ВЫПОЛНЕНА")
    print(f"  Собрано точек: {len(scan_data)}")
    print(f"  Остаток батареи: {drone.battery:.1f}%")
    print(f"  Тип почвы: {field.config.soil_type.value}")
    print(f"  Рельеф: {'включён' if field.config.terrain_enabled else 'выключен'}")
    print(f"{'=' * 55}")


if __name__ == "__main__":
    main()
