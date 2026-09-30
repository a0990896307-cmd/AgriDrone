"""
Модуль визуализации — отрисовка карт поля, маршрутов и данных.
v2.0 — Добавлены карты рельефа и типа почв.
"""

import matplotlib
matplotlib.use('Agg')  # no display needed, saves to files
import matplotlib.pyplot as plt
import numpy as np
from typing import List, Optional
import os


def plot_field_health(field, scan_data: Optional[List[dict]] = None,
                      route: Optional[List] = None,
                      save_path: str = "field_analysis.png",
                      show: bool = False):
    """
    Строит композитный график: карта здоровья поля + маршрут дрона + точки сканирования.
    v2.0: Добавлены карты рельефа и типа почв.
    """
    # Определяем layout в зависимости от того, есть ли рельеф
    has_terrain = hasattr(field, 'elevation_map') and field.elevation_map is not None

    if has_terrain:
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        n_plots = 6
    else:
        fig, axes = plt.subplots(2, 2, figsize=(14, 12))
        n_plots = 4

    fig.suptitle('🌾 Агро-Дрон: Анализ поля v2.0', fontsize=16, fontweight='bold')

    ax_idx = 0

    # 1. Карта здоровья поля (реальная)
    ax1 = axes[0, 0]
    im1 = ax1.imshow(field.health_map, cmap='RdYlGn', vmin=0, vmax=1, aspect='equal')
    ax1.set_title('Реальная карта здоровья растений')
    ax1.set_xlabel('X (метры)')
    ax1.set_ylabel('Y (метры)')
    plt.colorbar(im1, ax=ax1, label='Health index')

    # Наложить проблемные зоны
    for spot in field.problem_spots:
        circle = plt.Circle((spot['x'], spot['y']), spot['radius'],
                            color='red', fill=False, linestyle='--', linewidth=1.5)
        ax1.add_patch(circle)
        ax1.text(spot['x'], spot['y'] - spot['radius'] - 2,
                 spot['type'], color='red', fontsize=8, ha='center')

    # 2. Карта влажности
    ax2 = axes[0, 1]
    im2 = ax2.imshow(field.moisture_map, cmap='Blues', vmin=0, vmax=1, aspect='equal')
    ax2.set_title('Карта влажности почвы')
    ax2.set_xlabel('X (метры)')
    ax2.set_ylabel('Y (метры)')
    plt.colorbar(im2, ax=ax2, label='Moisture')

    # 3. Карта рельефа (если есть)
    if has_terrain:
        ax3 = axes[0, 2]
        im3 = ax3.imshow(field.elevation_map, cmap='terrain', aspect='equal')
        ax3.set_title('3D Рельеф (высота)')
        ax3.set_xlabel('X (метры)')
        ax3.set_ylabel('Y (метры)')
        plt.colorbar(im3, ax=ax3, label='Elevation')
    else:
        ax3 = axes[1, 0]

    # 4. Точки сканирования дрона
    ax4 = axes[1, 0] if not has_terrain else axes[1, 0]
    ax4.imshow(field.health_map, cmap='RdYlGn', vmin=0, vmax=1, aspect='equal',
               alpha=0.4)
    ax4.set_title('Данные сканирования дрона')
    ax4.set_xlabel('X (метры)')
    ax4.set_ylabel('Y (метры)')

    if scan_data:
        xs = [d['x'] for d in scan_data]
        ys = [d['y'] for d in scan_data]
        healths = [d['health'] for d in scan_data]
        scatter = ax4.scatter(xs, ys, c=healths, cmap='RdYlGn',
                              vmin=0, vmax=1, s=20, alpha=0.8)
        plt.colorbar(scatter, ax=ax4, label='Scanned health')

    # Маршрут дрона
    if route:
        route_x = [p[0] for p in route]
        route_y = [p[1] for p in route]
        ax4.plot(route_x, route_y, 'b-', alpha=0.5, linewidth=1, label='Route')
        ax4.plot(route_x[0], route_y[0], 'go', markersize=8, label='Start')
        ax4.plot(route_x[-1], route_y[-1], 'rs', markersize=8, label='End')
        ax4.legend(loc='upper right')

    # 5. Распределение NDVI / здоровья
    ax5 = axes[1, 1] if has_terrain else axes[1, 1]
    if scan_data:
        health_values = [d['health'] for d in scan_data]
        ndvi_values = [d['ndvi'] for d in scan_data]

        ax5.hist(health_values, bins=20, alpha=0.6, label='Health', color='green')
        ax5.hist(ndvi_values, bins=20, alpha=0.6, label='NDVI', color='blue')
        ax5.axvline(np.mean(health_values), color='green', linestyle='--',
                    label=f'Mean health: {np.mean(health_values):.2f}')
        ax5.axvline(np.mean(ndvi_values), color='blue', linestyle='--',
                    label=f'Mean NDVI: {np.mean(ndvi_values):.2f}')
        ax5.set_title('Распределение показателей')
        ax5.set_xlabel('Индекс')
        ax5.set_ylabel('Количество сканов')
        ax5.legend()

    # 6. Тип почвы и влажность (если есть рельеф)
    if has_terrain:
        ax6 = axes[1, 2]
        ax6.axis('off')

        soil = field.config.soil_type
        summary = field.get_health_summary()

        info_text = (
            f"📋 ПАРАМЕТРЫ ПОЛЯ\n"
            f"{'─' * 25}\n"
            f"Культура:    {field.config.crop_type}\n"
            f"Почва:       {soil.value}\n"
            f"  влажность: ×{soil.moisture_factor:.2f}\n"
            f"  плодородие: {soil.fertility:.0%}\n"
            f"Рельеф:      {'вкл' if field.config.terrain_enabled else 'выкл'}\n"
            f"  мин/макс:  {summary['elevation_range'][0]:.2f}/{summary['elevation_range'][1]:.2f}\n"
            f"{'─' * 25}\n"
            f"Средний NDVI:     {summary['mean_ndvi']:.3f}\n"
            f"Сред. здоровье:   {summary['mean_health']:.1%}\n"
            f"Сред. влажность:  {summary['mean_moisture']:.1%}\n"
            f"Критических:      {summary['critical_areas']} кл.\n"
            f"Здоровых:         {summary['good_areas']} кл.\n"
            f"Проблемных зон:   {summary['problem_spots']}\n"
        )
        ax6.text(0.05, 0.95, info_text, transform=ax6.transAxes,
                 fontsize=11, fontfamily='monospace', verticalalignment='top',
                 bbox=dict(boxstyle='round,pad=0.5', facecolor='lightyellow',
                           edgecolor='gray', alpha=0.9))

    plt.tight_layout()

    # Сохраняем
    os.makedirs(os.path.dirname(save_path) if os.path.dirname(save_path) else '.', exist_ok=True)
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    print(f"  📊 Графики сохранены: {save_path}")

    if show:
        plt.show()

    plt.close()


def plot_drone_view(field, scan_data: List[dict], save_path: str = "drone_view.png"):
    """
    Имитация вида с дрона — тепловая карта поля с высоты.
    """
    fig, ax = plt.subplots(1, 1, figsize=(10, 8))

    # Интерполируем данные сканирования в полную карту
    if scan_data:
        xs = np.array([d['x'] for d in scan_data])
        ys = np.array([d['y'] for d in scan_data])
        vals = np.array([d['health'] for d in scan_data])

        # Создаём сетку
        xi = np.linspace(0, field.cols - 1, field.cols)
        yi = np.linspace(0, field.rows - 1, field.rows)
        from scipy.interpolate import griddata
        grid = griddata((xs, ys), vals, (xi[None, :], yi[:, None]), method='cubic')

        ax.imshow(grid, cmap='RdYlGn', vmin=0, vmax=1, aspect='equal',
                  interpolation='bilinear')
        ax.set_title('🚁 Вид с дрона: интерполированная карта поля', fontsize=14)
        ax.set_xlabel('X (метры)')
        ax.set_ylabel('Y (метры)')

        # Наложим исходные точки
        ax.scatter(xs, ys, c='black', s=5, alpha=0.3)

    plt.colorbar(ax.images[0], ax=ax, label='Health index')
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    print(f"  🚁 Вид с дрона сохранён: {save_path}")
    plt.close()


def plot_terrain_3d(field, save_path: str = "terrain_3d.png"):
    """
    3D визуализация рельефа поля.
    """
    if not hasattr(field, 'elevation_map') or field.elevation_map is None:
        print("  ⚠️  Рельеф не включён. Пропускаем 3D-визуализацию.")
        return

    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')

    X, Y = np.meshgrid(np.arange(field.cols), np.arange(field.rows))
    Z = field.elevation_map

    # Окрашиваем по высоте
    surf = ax.plot_surface(X, Y, Z, cmap='terrain', edgecolor='none',
                           alpha=0.9, antialiased=True)

    ax.set_title('🏔️ 3D Рельеф поля', fontsize=14, fontweight='bold')
    ax.set_xlabel('X (метры)')
    ax.set_ylabel('Y (метры)')
    ax.set_zlabel('Высота')
    fig.colorbar(surf, ax=ax, label='Elevation', shrink=0.5)

    plt.tight_layout()
    os.makedirs(os.path.dirname(save_path) if os.path.dirname(save_path) else '.', exist_ok=True)
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    print(f"  🏔️ 3D рельеф сохранён: {save_path}")
    plt.close()
