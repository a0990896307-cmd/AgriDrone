"""
Модуль аналитики — анализ собранных дроном данных.
v2.0 — Добавлен анализ почв и рельефа.
"""

import numpy as np
from typing import List, Dict, Tuple


class FieldAnalytics:
    """
    Анализирует данные, собранные дроном.
    Определяет проблемные зоны, строит карты, генерирует рекомендации.
    v2.0 — анализирует влияние почвы и рельефа на здоровье растений.
    """

    def __init__(self, scan_data: List[dict]):
        self.scan_data = scan_data
        self.health_map = self._build_health_map()
        self.problem_zones = self._detect_problems()

    def _build_health_map(self) -> Dict[Tuple[int, int], float]:
        """Строит карту здоровья из сканов"""
        health_map = {}
        for reading in self.scan_data:
            key = (int(reading['x']), int(reading['y']))
            health_map[key] = reading['health']
        return health_map

    def _detect_problems(self) -> List[dict]:
        """
        Находит проблемные зоны:
        - Низкий NDVI (< 0.3)
        - Аномальная влажность
        - Резкие перепады здоровья
        - Проблемы связанные с почвой/рельефом
        """
        problems = []

        for reading in self.scan_data:
            issues = []

            if reading['ndvi'] < 0.3:
                issues.append('low_ndvi')
            if reading['health'] < 0.3:
                issues.append('low_health')
            if reading['moisture'] < 0.2:
                issues.append('drought')
            if reading['moisture'] > 0.9:
                issues.append('overwatered')

            # Анализ рельефа (если данные доступны)
            if 'elevation' in reading:
                if reading['elevation'] > 0.8 and reading['moisture'] < 0.2:
                    issues.append('hill_drought')  # на вершине холма — засуха
                if reading['elevation'] < 0.2 and reading['moisture'] > 0.85:
                    issues.append('valley_waterlog')  # в низине — застой воды
                if reading.get('slope', 0) > 0.3 and reading['health'] < 0.4:
                    issues.append('erosion_risk')  # крутой склон — эрозия

            if issues:
                problem = {
                    'x': reading['x'],
                    'y': reading['y'],
                    'ndvi': reading['ndvi'],
                    'health': reading['health'],
                    'moisture': reading['moisture'],
                    'issues': issues,
                    'severity': len(issues) / 4.0,  # 0.25-1.0
                }
                # Добавляем доп. поля если есть
                if 'soil_type' in reading:
                    problem['soil_type'] = reading['soil_type']
                if 'elevation' in reading:
                    problem['elevation'] = reading['elevation']
                problems.append(problem)

        return problems

    def get_summary(self) -> Dict:
        """Возвращает сводку по результатам облёта"""
        if not self.scan_data:
            return {"error": "Нет данных для анализа"}

        health_values = [d['health'] for d in self.scan_data]
        ndvi_values = [d['ndvi'] for d in self.scan_data]
        moisture_values = [d['moisture'] for d in self.scan_data]

        # Собираем статистику по почвам
        soil_stats = {}
        for d in self.scan_data:
            soil = d.get('soil_type', 'неизвестно')
            if soil not in soil_stats:
                soil_stats[soil] = {'health': [], 'moisture': [], 'ndvi': []}
            soil_stats[soil]['health'].append(d['health'])
            soil_stats[soil]['moisture'].append(d['moisture'])
            soil_stats[soil]['ndvi'].append(d.get('ndvi', 0))

        soil_summary = {}
        for soil, stats in soil_stats.items():
            soil_summary[soil] = {
                'mean_health': float(np.mean(stats['health'])),
                'mean_moisture': float(np.mean(stats['moisture'])),
                'mean_ndvi': float(np.mean(stats['ndvi'])),
                'cells': len(stats['health']),
            }

        return {
            "total_scans": len(self.scan_data),
            "problem_zones": len(self.problem_zones),
            "mean_health": float(np.mean(health_values)),
            "mean_ndvi": float(np.mean(ndvi_values)),
            "mean_moisture": float(np.mean(moisture_values)),
            "min_health": float(np.min(health_values)),
            "max_health": float(np.max(health_values)),
            "critical_count": sum(1 for d in self.scan_data if d['health'] < 0.3),
            "healthy_count": sum(1 for d in self.scan_data if d['health'] > 0.7),
            "soil_analysis": soil_summary,
        }

    def generate_report(self) -> str:
        """Генерирует текстовый отчёт для владельца поля"""
        summary = self.get_summary()

        report = []
        report.append("=" * 55)
        report.append("📋 АГРО-ОТЧЁТ ПО РЕЗУЛЬТАТАМ ОБЛЁТА v2.0")
        report.append("=" * 55)
        report.append(f"\n📊 Общая статистика:")
        report.append(f"   Сканировано точек:    {summary['total_scans']}")
        report.append(f"   Средний NDVI:         {summary['mean_ndvi']:.3f}")
        report.append(f"   Среднее здоровье:     {summary['mean_health']:.1%}")
        report.append(f"   Средняя влажность:    {summary['mean_moisture']:.1%}")
        report.append(f"   Здоровых участков:    {summary['healthy_count']} "
                      f"({summary['healthy_count']/summary['total_scans']*100:.0f}%)")
        report.append(f"   Критических участков: {summary['critical_count']} "
                      f"({summary['critical_count']/summary['total_scans']*100:.0f}%)")

        # Статистика по типам почв
        if summary.get('soil_analysis'):
            report.append(f"\n🌱 Анализ по типам почв:")
            for soil, stats in summary['soil_analysis'].items():
                report.append(f"   {soil}:")
                report.append(f"      здоровье:  {stats['mean_health']:.1%}")
                report.append(f"      влажность: {stats['mean_moisture']:.1%}")
                report.append(f"      NDVI:      {stats['mean_ndvi']:.3f}")
                report.append(f"      клеток:    {stats['cells']}")

        report.append(f"\n⚠️  Проблемных зон: {summary['problem_zones']}")

        if self.problem_zones:
            report.append(f"\n🔍 Детали проблемных зон (первые 10):")
            for i, zone in enumerate(self.problem_zones[:10], 1):
                issues_str = ', '.join(zone['issues'])
                soil_info = f" | Почва: {zone.get('soil_type', '?')}" if 'soil_type' in zone else ''
                report.append(f"   {i}. Координаты ({zone['x']:.0f}, {zone['y']:.0f}) | "
                              f"NDVI: {zone['ndvi']:.2f} | "
                              f"Проблемы: {issues_str}{soil_info}")
                if 'elevation' in zone:
                    report.append(f"      Высота: {zone['elevation']:.2f}")

        report.append("\n" + "=" * 55)
        report.append("💡 Рекомендации:")

        if summary['critical_count'] > summary['total_scans'] * 0.1:
            report.append("   🔴 Требуется срочное вмешательство — более 10% поля в критическом состоянии.")
        if summary['mean_ndvi'] < 0.4:
            report.append("   🟡 Общий низкий NDVI — возможна нехватка удобрений или проблемы с поливом.")
        if summary['mean_moisture'] > 0.8:
            report.append("   🔵 Высокая влажность — риск грибковых заболеваний, рекомендуется дренаж.")
        if summary['mean_moisture'] < 0.3:
            report.append("   🟠 Низкая влажность — требуется срочный полив.")

        # Рекомендации по почвам
        if summary.get('soil_analysis'):
            for soil, stats in summary['soil_analysis'].items():
                if soil == 'песок' and stats['mean_moisture'] < 0.25:
                    report.append(f"   🟠 Песчаные участки слишком сухие (влажность {stats['mean_moisture']:.1%}) — "
                                  f"рекомендуется капельный полив и внесение органики.")
                if soil == 'глина' and stats['mean_moisture'] > 0.8:
                    report.append(f"   🔵 Глинистые участки переувлажнены (влажность {stats['mean_moisture']:.1%}) — "
                                  f"рекомендуется дренаж.")

        report.append(f"\n📅 Дата отчёта: симулирована автоматически")
        report.append("=" * 55)

        return '\n'.join(report)

    def get_treatment_plan(self) -> List[Dict]:
        """Формирует план действий для обработки проблемных зон"""
        plan = []
        for zone in sorted(self.problem_zones, key=lambda z: z['severity'], reverse=True):
            for issue in zone['issues']:
                if issue == 'low_ndvi':
                    action = "Внести азотные удобрения"
                elif issue == 'drought':
                    action = "Запланировать полив"
                elif issue == 'overwatered':
                    action = "Проверить дренаж, приостановить полив"
                elif issue == 'low_health':
                    action = "Осмотр агрономом, возможна обработка фунгицидами"
                elif issue == 'hill_drought':
                    action = "Капельный полив на возвышенностях, мульчирование"
                elif issue == 'valley_waterlog':
                    action = "Улучшить дренаж в низинах"
                elif issue == 'erosion_risk':
                    action = "Укрепить склоны, высадить почвопокровные растения"
                else:
                    action = "Дополнительное обследование"

                plan.append({
                    'x': zone['x'],
                    'y': zone['y'],
                    'issue': issue,
                    'action': action,
                    'priority': 'high' if zone['severity'] > 0.5 else 'medium',
                    'soil_type': zone.get('soil_type', '?'),
                })
        return plan
