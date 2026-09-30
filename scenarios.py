"""
Сценарии тестирования для научной работы.
Позволяет запускать серии экспериментов и собирать статистику.
"""

import sys
import os
import time
import json
import numpy as np
from typing import List, Dict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from field import Field, FieldConfig
from drone import Drone
from analytics import FieldAnalytics


class ScenarioRunner:
    """
    Запускает множество сценариев и собирает метрики.
    """

    def __init__(self):
        self.results = []

    def run_scenario(self, name: str, field_seed: int, drone_speed: float = 3.0,
                     scan_width: float = 5.0, battery: float = 100.0,
                     problem_fields: int = 0) -> Dict:
        """
        Запускает один сценарий и возвращает метрики.
        """
        # Создаём поле
        field = Field(FieldConfig(width=100, height=100, seed=field_seed))

        # Если нужно, форсируем количество проблемных зон
        # (у Field уже есть генерация, но мы можем пересоздать с контролем)

        # Создаём дрон
        drone = Drone(
            field_width=field.config.width,
            field_height=field.config.height,
            speed=drone_speed,
            scan_width=scan_width,
            battery_capacity=battery
        )

        # Планируем маршрут
        route = drone.plan_route_lawnmower()

        # Замеряем время симуляции полёта
        start_time = time.time()
        scan_data = drone.execute_mission(field)
        elapsed = time.time() - start_time

        # Анализируем
        analytics = FieldAnalytics(scan_data)
        summary = analytics.get_summary()
        treatment = analytics.get_treatment_plan()

        # Собираем метрики
        real_health = field.health_map
        problem_mask = real_health < 0.3  # реальные проблемы

        # Оценка детекции: считаем, сколько реальных проблемных клеток
        # было обнаружено (попало в сканы с низким health)
        detected_problems = 0
        total_problems = int(np.sum(problem_mask))
        for reading in scan_data:
            x, y = int(reading['x']), int(reading['y'])
            if 0 <= x < field.cols and 0 <= y < field.rows:
                if problem_mask[y, x] and reading['health'] < 0.3:
                    detected_problems += 1

        # Собираем метрики покрытия
        covered_cells = set()
        for reading in scan_data:
            covered_cells.add((int(reading['x']), int(reading['y'])))
        coverage_pct = len(covered_cells) / (field.rows * field.cols) * 100

        result = {
            'scenario': name,
            'field_seed': field_seed,
            'field_mean_health': float(np.mean(real_health)),
            'field_problem_pct': float(total_problems / (field.rows * field.cols) * 100),
            'drone_speed': drone_speed,
            'scan_width': scan_width,
            'mission': {
                'total_points': len(route),
                'scans_collected': len(scan_data),
                'coverage_pct': round(coverage_pct, 2),
                'battery_remaining': round(drone.battery, 2),
                'battery_used': round(battery - drone.battery, 2),
            },
            'detection': {
                'real_problems': total_problems,
                'detected_problems': detected_problems,
                'detection_rate': round(detected_problems / max(total_problems, 1) * 100, 2),
                'problem_zones_found': summary['problem_zones'],
                'false_positives': summary['problem_zones'],  # упрощённо
            },
            'analytics_summary': summary,
            'treatment_plan_count': len(treatment),
            'simulation_time_ms': round(elapsed * 1000, 2)
        }

        self.results.append(result)
        return result

    def run_benchmark(self) -> List[Dict]:
        """
        Запускает полный набор сценариев для научной работы.
        """
        print("=" * 60)
        print("  🔬 ЗАПУСК БЕНЧМАРКА СЦЕНАРИЕВ")
        print("=" * 60)

        scenarios = [
            # (name, seed, speed, scan_width, battery)
            ("A1_Здоровое_поле", 1, 3.0, 5.0, 100),
            ("A2_Здоровое_поле_быстро", 1, 5.0, 5.0, 100),
            ("B1_Проблемное_поле", 42, 3.0, 5.0, 100),
            ("B2_Проблемное_поле_широкий_захват", 42, 3.0, 10.0, 100),
            ("C1_Смешанное_поле", 99, 3.0, 5.0, 100),
            ("C2_Смешанное_поле_медленно_точно", 99, 1.5, 3.0, 100),
            ("D1_Экстремальное", 7, 3.0, 5.0, 100),
            ("E1_Ограниченная_батарея", 42, 3.0, 5.0, 30),
            ("E2_Максимальная_скорость", 42, 8.0, 5.0, 100),
        ]

        for name, seed, speed, swidth, batt in scenarios:
            print(f"\n▶  {name}")
            result = self.run_scenario(
                name=name,
                field_seed=seed,
                drone_speed=speed,
                scan_width=swidth,
                battery=batt
            )
            m = result['mission']
            d = result['detection']
            print(f"   Покрытие: {m['coverage_pct']}% | "
                  f"Детекция: {d['detection_rate']}% | "
                  f"Батарея: {m['battery_remaining']}%")

        # Сохраняем результаты
        self._save_results()
        return self.results

    def _save_results(self):
        """Сохраняет результаты в JSON"""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        reports_dir = os.path.join(base_dir, "reports")
        os.makedirs(reports_dir, exist_ok=True)

        path = os.path.join(reports_dir, "benchmark_results.json")
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        print(f"\n  💾 Результаты сохранены: {path}")

    def print_comparison_table(self):
        """Печатает сравнительную таблицу сценариев"""
        if not self.results:
            print("Нет результатов. Сначала запустите run_benchmark().")
            return

        print("\n" + "=" * 110)
        print(f"{'Сценарий':<35} {'Покрытие':<10} {'Проблемы':<10} {'Детекция':<10} "
              f"{'Батарея':<10} {'Время':<10}")
        print("=" * 110)

        for r in self.results:
            name = r['scenario'][:34]
            cov = f"{r['mission']['coverage_pct']}%"
            prob = f"{r['detection']['real_problems']}шт"
            det = f"{r['detection']['detection_rate']}%"
            bat = f"{r['mission']['battery_remaining']}%"
            t = f"{r['mission']['scans_collected']}ск"
            print(f"{name:<35} {cov:<10} {prob:<10} {det:<10} {bat:<10} {t:<10}")

        print("=" * 110)


if __name__ == "__main__":
    runner = ScenarioRunner()
    runner.run_benchmark()
    runner.print_comparison_table()
