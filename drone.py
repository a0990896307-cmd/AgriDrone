"""
Модуль дрона — симуляция полёта и сбора данных.
"""

import numpy as np
from enum import Enum
from typing import List, Tuple, Optional


class DroneState(Enum):
    IDLE = "idle"
    TAKEOFF = "takeoff"
    SCANNING = "scanning"
    RETURNING = "returning"
    LANDED = "landed"
    LOW_BATTERY = "low_battery"


class Drone:
    """
    Виртуальный агро-дрон.
    Облетает поле по заданному маршруту, собирает данные с сенсоров.
    """

    def __init__(self, field_width: int, field_height: int,
                 speed: float = 2.0,   # метров в секунду
                 scan_width: float = 5.0,  # ширина захвата сканирования (метров)
                 battery_capacity: float = 100.0,  # минут полёта
                 altitude: float = 50.0):  # метров
        self.field_width = field_width
        self.field_height = field_height
        self.speed = speed
        self.scan_width = scan_width
        self.max_battery = battery_capacity
        self.battery = battery_capacity
        self.altitude = altitude

        # Позиция
        self.x = 0.0
        self.y = 0.0
        self.state = DroneState.IDLE

        # Собранные данные
        self.scan_data: List[dict] = []

        # Маршрут
        self.route: List[Tuple[float, float]] = []

    def plan_route_lawnmower(self) -> List[Tuple[float, float]]:
        """
        Планирует маршрут "газонокосилка" — эффективное покрытие всего поля.
        Возвращает список путевых точек (x, y).
        """
        route = []
        step = self.scan_width

        y = step / 2
        direction = 1  # 1 = слева направо, -1 = справа налево

        while y < self.field_height:
            if direction == 1:
                route.append((step / 2, y))
                route.append((self.field_width - step / 2, y))
            else:
                route.append((self.field_width - step / 2, y))
                route.append((step / 2, y))
            y += step
            direction *= -1

        self.route = route
        return route

    def plan_route_focused(self, hotspots: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """
        Планирует маршрут для детального обследования горячих точек.
        """
        route = [(self.field_width / 2, self.field_height / 2)]  # старт с центра
        for hx, hy in hotspots:
            route.append((hx, hy))
        self.route = route
        return route

    def takeoff(self):
        """Взлёт"""
        self.state = DroneState.TAKEOFF
        self.altitude = 10.0  # начальная высота

    def move_to(self, target_x: float, target_y: float) -> float:
        """
        Движение к целевой точке. Возвращает время полёта в секундах.
        """
        dx = target_x - self.x
        dy = target_y - self.y
        distance = np.sqrt(dx ** 2 + dy ** 2)
        time = distance / self.speed

        # Расход батареи (1 минута полёта = 1% батареи)
        battery_cost = time / 60.0
        self.battery -= battery_cost

        self.x, self.y = target_x, target_y
        return time

    def scan_cell(self, field_data: dict) -> dict:
        """
        Сканирует текущую клетку поля и возвращает данные.
        Симулирует работу мультиспектральной камеры.
        """
        if field_data is None:
            return None

        # Добавляем шум сенсора к реальным данным
        health_reading = field_data['health'] + np.random.normal(0, 0.02)
        moisture_reading = field_data['moisture'] + np.random.normal(0, 0.03)

        reading = {
            'x': self.x,
            'y': self.y,
            'health': float(np.clip(health_reading, 0.0, 1.0)),
            'moisture': float(np.clip(moisture_reading, 0.0, 1.0)),
            'ndvi': float(self._calculate_ndvi(health_reading)),
            'altitude': self.altitude,
            'battery': self.battery,
            'soil_type': field_data.get('soil_type', 'неизвестно'),
            'elevation': field_data.get('elevation', 0.5),
            'slope': field_data.get('slope', 0.0),
        }

        self.scan_data.append(reading)
        return reading

    def _calculate_ndvi(self, health: float) -> float:
        """
        Симулирует NDVI (Normalized Difference Vegetation Index).
        В реальности NDVI = (NIR - Red) / (NIR + Red).
        Здесь аппроксимируем через здоровье растений.
        """
        # NDVI обычно от -1 до 1, для здоровой растительности 0.6-0.9
        ndvi = -0.1 + health * 0.9 + np.random.normal(0, 0.02)
        return float(np.clip(ndvi, -0.1, 0.95))

    def execute_mission(self, field) -> List[dict]:
        """
        Выполняет полную миссию: взлёт, облёт поля по маршруту, сбор данных.
        Возвращает все собранные данные.
        """
        self.scan_data = []
        self.state = DroneState.SCANNING

        # Планируем маршрут если ещё не задан
        if not self.route:
            self.plan_route_lawnmower()

        total_time = 0.0

        print(f"\n🚁 Дрон стартовал! Батарея: {self.battery:.1f}%")
        print(f"📍 Маршрут: {len(self.route)} точек")
        print(f"{'─' * 50}")

        for i, (tx, ty) in enumerate(self.route):
            # Проверка батареи
            if self.battery < 5.0:
                print(f"⚠️  Низкий заряд батареи ({self.battery:.1f}%). Возврат...")
                self.state = DroneState.LOW_BATTERY
                break

            # Движение к точке
            travel_time = self.move_to(tx, ty)
            total_time += travel_time

            # Сканирование в точке
            cell_x = int(self.x)
            cell_y = int(self.y)
            data = self.scan_cell(field.get_cell_data(cell_x, cell_y))

            if data and i % 10 == 0:  # Логируем каждую 10-ю точку
                print(f"  [{i+1}/{len(self.route)}] ({self.x:.1f}, {self.y:.1f}) "
                      f"NDVI: {data['ndvi']:.2f} | "
                      f"Health: {data['health']:.2f} | "
                      f"Bat: {self.battery:.1f}%")

        # Возврат
        self.state = DroneState.RETURNING
        print(f"\n🏁 Миссия завершена за {total_time:.0f} сек")
        print(f"📊 Собрано точек: {len(self.scan_data)}")
        print(f"🔋 Остаток батареи: {self.battery:.1f}%")

        self.state = DroneState.LANDED
        return self.scan_data
