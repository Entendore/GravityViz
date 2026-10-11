#!/usr/bin/env python3
"""
Gravity Education — Professional Edition
Interactive visualizations of gravity, black holes, and celestial mechanics.
"""

import sys
import math
import random
import numpy as np
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QSlider, QPushButton, QComboBox, QDoubleSpinBox,
    QStackedWidget, QScrollArea, QGridLayout, QSizePolicy, QFrame,
    QListWidget
)
from PySide6.QtCore import Qt, QTimer, QElapsedTimer
from PySide6.QtGui import QPixmap, QImage
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.patches import Circle
from matplotlib.collections import LineCollection
from matplotlib import cm, colors as mcolors
import matplotlib
matplotlib.use("QtAgg")

# ═══════════════════════════════════════════════════════════════════════════════
#  PHYSICAL CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════
G = 6.674e-11
c = 2.998e8
M_SUN = 1.989e30
M_EARTH = 5.972e24
R_EARTH = 6.371e6
AU = 1.496e11
hbar = 1.055e-34
k_B = 1.381e-23
sigma_SB = 5.670e-8

# ═══════════════════════════════════════════════════════════════════════════════
#  STYLESHEETS
# ═══════════════════════════════════════════════════════════════════════════════
DARK_STYLE = """
QMainWindow{background-color:#0d1117}
QWidget{background-color:#0d1117;color:#c9d1d9;font-family:'Segoe UI',Arial;font-size:13px}
QGroupBox{border:1px solid #30363d;border-radius:8px;margin-top:14px;padding:16px;padding-top:28px;font-weight:bold;color:#58a6ff;font-size:14px}
QGroupBox::title{subcontrol-origin:margin;left:14px;padding:0 8px}
QSlider::groove:horizontal{height:6px;background:#21262d;border-radius:3px}
QSlider::handle:horizontal{width:18px;height:18px;margin:-6px 0;background:qradialgradient(cx:0.5,cy:0.5,radius:0.5,fx:0.5,fy:0.3,stop:0 #79c0ff,stop:1 #1f6feb);border-radius:9px;border:2px solid #0d1117}
QSlider::sub-page:horizontal{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #1f6feb,stop:1 #58a6ff);border-radius:3px}
QPushButton{background-color:#21262d;border:1px solid #30363d;border-radius:6px;padding:7px 18px;color:#c9d1d9;font-weight:bold;font-size:12px}
QPushButton:hover{background-color:#30363d;border-color:#58a6ff}
QPushButton:pressed{background-color:#1f6feb;color:white}
QPushButton:checked{background-color:#1f6feb;color:white}
QDoubleSpinBox,QComboBox{background-color:#161b22;border:1px solid #30363d;border-radius:5px;padding:5px 10px;color:#c9d1d9;min-width:85px;font-size:12px}
QComboBox::drop-down{border:none;padding-right:8px}
QComboBox QAbstractItemView{background-color:#161b22;color:#c9d1d9;selection-background-color:#1f6feb}
QScrollArea{border:none}
QLabel{background-color:transparent}
"""

SIDEBAR_STYLE = """
QListWidget{background-color:#0d1117;border:none;border-right:1px solid #21262d;outline:none;font-size:13px;padding:8px 6px}
QListWidget::item{padding:14px 16px;margin:3px 4px;border-radius:8px;color:#8b949e}
QListWidget::item:selected{background-color:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #1f6feb,stop:1 rgba(31,111,235,0.3));color:#fff;font-weight:bold}
QListWidget::item:hover:!selected{background-color:#161b22;color:#c9d1d9}
"""


# ═══════════════════════════════════════════════════════════════════════════════
#  UTILITIES
# ═══════════════════════════════════════════════════════════════════════════════
def fmt(value, unit="", precision=4):
    if value == 0:
        return f"0 {unit}".strip()
    if abs(value) >= 1e6 or abs(value) < 1e-2:
        return f"{value:.{precision}e} {unit}".strip()
    return f"{value:.{precision}f} {unit}".strip()


def styled_label(text, size=13, color="#c9d1d9", bold=False):
    lbl = QLabel(text)
    w = "bold" if bold else "normal"
    lbl.setStyleSheet(f"font-size:{size}px;color:{color};font-weight:{w}")
    lbl.setWordWrap(True)
    return lbl


def render_latex(latex_str, font_size=20, figsize=(8, 0.8), color="white"):
    fig = Figure(figsize=figsize, dpi=120)
    fig.patch.set_alpha(0)
    ax = fig.add_subplot(111)
    ax.axis("off")
    ax.text(0.5, 0.5, f"${latex_str}$", transform=ax.transAxes,
            fontsize=font_size, ha="center", va="center", color=color)
    import io
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight",
                transparent=True, pad_inches=0.03)
    buf.seek(0)
    qimg = QImage()
    qimg.loadFromData(buf.read())
    return QPixmap.fromImage(qimg)

class EquationLabel(QLabel):
    def __init__(self, latex_str, font_size=22, color="white", figsize=(8, 0.8), parent=None):
        super().__init__(parent)
        px = render_latex(latex_str, font_size=font_size, figsize=figsize, color=color)
        self.setPixmap(px)
        self.setAlignment(Qt.AlignCenter)

def generate_stars(n, xlim, ylim, seed=42):
    rng = np.random.RandomState(seed)
    x = rng.uniform(*xlim, n)
    y = rng.uniform(*ylim, n)
    sizes = rng.exponential(0.8, n) + 0.2
    brightnesses = rng.uniform(0.2, 1.0, n)
    return x, y, sizes, brightnesses


def draw_glow(ax, x, y, color, max_radius=0.5, n_layers=12, zorder=5):
    for i in range(n_layers, 0, -1):
        r = max_radius * (i / n_layers) ** 0.6
        alpha = 0.06 * (1 - (i / n_layers) ** 0.5)
        ax.add_patch(Circle((x, y), r, fc=color, alpha=alpha,
                            ec="none", zorder=zorder))


def style_ax(ax, title="", xlabel="", ylabel=""):
    ax.set_facecolor("#0d1117")
    ax.tick_params(colors="#6e7681", labelsize=9, direction="in", length=4)
    ax.xaxis.label.set_color("#8b949e")
    ax.yaxis.label.set_color("#8b949e")
    ax.title.set_color("#58a6ff")
    for spine in ax.spines.values():
        spine.set_color("#21262d")
        spine.set_linewidth(0.5)
    if title:
        ax.set_title(title, fontsize=14, fontweight="bold", pad=10)
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=11)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=11)


class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=7, height=5, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.fig.patch.set_facecolor("#0d1117")
        self.fig.subplots_adjust(left=0.1, right=0.95, top=0.92, bottom=0.1)
        super().__init__(self.fig)
        self.setParent(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.ax = self.fig.add_subplot(111)
        style_ax(self.ax)

    def fresh_ax(self, projection=None):
        self.fig.clear()
        if projection:
            ax = self.fig.add_subplot(111, projection=projection)
        else:
            ax = self.fig.add_subplot(111)
        style_ax(ax)
        return ax


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN APPLICATION
# ═══════════════════════════════════════════════════════════════════════════════
class GravityEducationApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gravity Education — Black Holes & Celestial Mechanics")
        self.setMinimumSize(1200, 800)
        self.resize(1500, 950)
        self.setStyleSheet(DARK_STYLE)

        self.anim_timer = QTimer()
        self.anim_timer.setInterval(33)
        self.anim_timer.timeout.connect(self._on_anim_tick)
        self.anim_elapsed = QElapsedTimer()
        self.anim_elapsed.start()

        self.orbit_angle = 0.0
        self.orbit_trail = []
        self.bh_disk_angle = 0.0
        self.td_clock_far = 0.0
        self.td_clock_near = 0.0
        self.td_factor = 1.0
        self.overview_particles = []
        self.sim_masses = []
        self._bh_stars = None

        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        ml = QHBoxLayout(central)
        ml.setSpacing(0)
        ml.setContentsMargins(0, 0, 0, 0)

        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(260)
        self.sidebar.setStyleSheet(SIDEBAR_STYLE)
        for p in [
            "🏠  Overview", "🍎  Newton's Gravity", "🚀  Escape Velocity",
            "🪐  Orbital Mechanics", "🕳️  Black Holes", "⏰  Time Dilation",
            "🔥  Hawking Radiation", "🌀  Field Simulator"
        ]:
            self.sidebar.addItem(p)
        self.sidebar.setCurrentRow(0)
        self.sidebar.currentRowChanged.connect(self._switch_page)

        self.stack = QStackedWidget()
        self._build_overview()
        self._build_newton()
        self._build_escape()
        self._build_orbital()
        self._build_blackhole()
        self._build_timedilation()
        self._build_hawking()
        self._build_simulator()

        ml.addWidget(self.sidebar)
        ml.addWidget(self.stack, 1)

    def _switch_page(self, idx):
        self.stack.setCurrentIndex(idx)
        if idx in (0, 3, 4, 5):
            self.anim_timer.start()
        else:
            self.anim_timer.stop()
        if idx == 0:
            self._init_overview_particles()
        elif idx == 4:
            self._update_blackhole()

    def _on_anim_tick(self):
        idx = self.stack.currentIndex()
        if idx == 0:
            self._animate_overview()
        elif idx == 3:
            self._animate_orbit()
        elif idx == 4:
            self._animate_blackhole()
        elif idx == 5:
            self._animate_timedilation()

    def _scroll_wrap(self, w):
        s = QScrollArea()
        s.setWidget(w)
        s.setWidgetResizable(True)
        s.setFrameShape(QFrame.NoFrame)
        return s

    @staticmethod
    def _solve_kepler(M_anom, e, tol=1e-10):
        E = M_anom
        for _ in range(200):
            dE = (E - e * math.sin(E) - M_anom) / (1 - e * math.cos(E))
            E -= dE
            if abs(dE) < tol:
                break
        return E

    # ══════════════════════════════════════════════════════════════════════════
    #  PAGE 0 — OVERVIEW
    # ══════════════════════════════════════════════════════════════════════════
    def _build_overview(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(32, 28, 32, 28)
        lay.setSpacing(14)

        lay.addWidget(styled_label(
            "Gravity — The Force That Shapes the Universe", 30, "#58a6ff", True))
        lay.addWidget(EquationLabel(
            r"F=G\frac{m_1 m_2}{r^2}\qquad r_s=\frac{2GM}{c^2}\qquad T_H=\frac{\hbar c^3}{8\pi G M k_B}",
            18, "#f0883e", (10, 0.7)))

        topics = [
            ("🍎 Newton's Law", "F = Gm₁m₂/r²",
             "Every mass attracts every other mass — the universal law."),
            ("🚀 Escape Velocity", "v = √(2GM/r)",
             "How fast must you go to leave a planet — or a black hole?"),
            ("🪐 Orbital Mechanics", "T² ∝ r³",
             "Kepler's laws and the elegant geometry of orbits."),
            ("🕳️ Black Holes", "rₛ = 2GM/c²",
             "Where gravity becomes so extreme that not even light escapes."),
            ("⏰ Time Dilation", "dτ = dt√(1−rₛ/r)",
             "Gravity warps time — clocks tick slower near massive objects."),
            ("🔥 Hawking Radiation", "T = ℏc³/(8πGMk_B)",
             "Black holes radiate, shrink, and eventually evaporate!"),
        ]
        grid = QGridLayout()
        grid.setSpacing(10)
        for i, (title, eq, desc) in enumerate(topics):
            card = QFrame()
            card.setStyleSheet("""
                QFrame{background-color:qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 #161b22,stop:1 #0d1117);border:1px solid #21262d;
                border-radius:10px;padding:12px}
                QFrame:hover{border-color:#58a6ff}""")
            cl = QVBoxLayout(card)
            cl.setSpacing(3)
            cl.addWidget(styled_label(title, 13, "#58a6ff", True))
            cl.addWidget(EquationLabel(eq, 13, "#f0883e", (4, 0.4)))
            cl.addWidget(styled_label(desc, 10, "#8b949e"))
            grid.addWidget(card, i // 3, i % 3)
        lay.addLayout(grid)

        self.overview_canvas = MplCanvas(self, 10, 5)
        lay.addWidget(self.overview_canvas, 1)
        self._init_overview_particles()
        self.stack.addWidget(self._scroll_wrap(page))

    def _init_overview_particles(self):
        self.overview_particles = []
        for i in range(10):
            a = i * 2 * math.pi / 10 + random.uniform(-0.3, 0.3)
            r = random.uniform(6, 13)
            self.overview_particles.append(dict(
                r=r, theta=a, vr=-0.03 - random.uniform(0, 0.02),
                vtheta=0.04 + random.uniform(0, 0.02)))

    def _animate_overview(self):
        ax = self.overview_canvas.fresh_ax(projection="3d")
        r = np.linspace(1.2, 14, 200)
        theta = np.linspace(0, 2 * np.pi, 200)
        R, Theta = np.meshgrid(r, theta)
        X, Y, Z = R * np.cos(Theta), R * np.sin(Theta), -2.0 / R

        cmap = mcolors.LinearSegmentedColormap.from_list("grav", [
            "#0d1117", "#0d1f3c", "#1a3a5c", "#2d6a8f",
            "#4a9eba", "#7ec8d9", "#f0c866", "#f0883e", "#ff4444"])
        ax.plot_surface(X, Y, Z, cmap=cmap, alpha=0.65, rstride=4, cstride=4,
                        edgecolor="none", antialiased=True)

        for p in self.overview_particles:
            p["r"] += p["vr"]
            p["theta"] += p["vtheta"] / max(p["r"], 0.5)
            p["vtheta"] += 0.001
            if p["r"] < 1.5:
                p["r"] = random.uniform(10, 14)
                p["theta"] = random.uniform(0, 2 * math.pi)
                p["vr"] = -0.03 - random.uniform(0, 0.02)
            px = p["r"] * math.cos(p["theta"])
            py = p["r"] * math.sin(p["theta"])
            pz = -2.0 / max(p["r"], 1.2) + 0.15
            ax.scatter([px], [py], [pz], color="#ffd700", s=30, alpha=0.9,
                       edgecolors="#ff8c00", linewidths=0.5, zorder=10)

        ax.set_axis_off()
        t = self.anim_elapsed.elapsed() / 5000.0
        ax.view_init(elev=35 + 5 * math.sin(t), azim=t * 30 % 360)
        ax.set_title("Gravitational Potential Well — Particles Spiraling In",
                      color="#58a6ff", fontsize=13, fontweight="bold", pad=-5)
        self.overview_canvas.draw()

    # ══════════════════════════════════════════════════════════════════════════
    #  PAGE 1 — NEWTON
    # ══════════════════════════════════════════════════════════════════════════
    def _build_newton(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(32, 28, 32, 28)
        lay.setSpacing(10)

        lay.addWidget(styled_label(
            "Newton's Law of Universal Gravitation", 26, "#58a6ff", True))
        lay.addWidget(EquationLabel(
            r"F=G\,\frac{m_1 m_2}{r^2}\qquad g=\frac{GM}{r^2}",
            24, "#f0883e", (8, 0.8)))
        lay.addWidget(styled_label(
            "Every particle of matter attracts every other particle with a force "
            "proportional to the product of their masses and inversely proportional "
            "to the square of the distance between them.", 12, "#8b949e"))

        ctrl = QHBoxLayout()
        ctrl.addWidget(styled_label("m₁ (M☉):", 11))
        self.nt_m1 = QDoubleSpinBox()
        self.nt_m1.setRange(0.01, 1000)
        self.nt_m1.setValue(1.0)
        self.nt_m1.setSingleStep(0.1)
        ctrl.addWidget(self.nt_m1)
        ctrl.addWidget(styled_label("m₂ (M☉):", 11))
        self.nt_m2 = QDoubleSpinBox()
        self.nt_m2.setRange(0.01, 1000)
        self.nt_m2.setValue(1.0)
        self.nt_m2.setSingleStep(0.1)
        ctrl.addWidget(self.nt_m2)
        ctrl.addWidget(styled_label("r (AU):", 11))
        self.nt_r = QDoubleSpinBox()
        self.nt_r.setRange(0.01, 200)
        self.nt_r.setValue(1.0)
        self.nt_r.setSingleStep(0.1)
        ctrl.addWidget(self.nt_r)
        btn = QPushButton("⟳  Calculate")
        btn.clicked.connect(self._update_newton)
        ctrl.addWidget(btn)
        ctrl.addStretch()
        lay.addLayout(ctrl)

        self.nt_result = styled_label("", 14, "#7ee787", True)
        lay.addWidget(self.nt_result)

        self.nt_canvas = MplCanvas(self, 10, 5.5)
        lay.addWidget(self.nt_canvas, 1)
        self._update_newton()
        self.stack.addWidget(self._scroll_wrap(page))

    def _update_newton(self):
        m1 = self.nt_m1.value() * M_SUN
        m2 = self.nt_m2.value() * M_SUN
        r_val = self.nt_r.value() * AU
        F = G * m1 * m2 / r_val ** 2

        self.nt_result.setText(
            f"Gravitational Force  F = {fmt(F, 'N')}   |   "
            f"Gravitational acceleration  g = {fmt(G * m1 / r_val**2, 'm/s²')}")

        fig = self.nt_canvas.fig
        fig.clear()

        # LEFT: Force diagram
        ax1 = fig.add_subplot(121)
        style_ax(ax1, title="Force Diagram")
        ax1.set_facecolor("#0d1117")
        ax1.set_aspect("equal")

        sx, sy, ss, sb = generate_stars(150, (-6, 6), (-3, 3), seed=7)
        for i in range(len(sx)):
            ax1.plot(sx[i], sy[i], ".", color="white",
                     markersize=ss[i], alpha=sb[i] * 0.35, zorder=0)

        pos1, pos2 = -1.5, 1.5
        sc1 = min(0.8, 0.2 + self.nt_m1.value() * 0.1)
        sc2 = min(0.8, 0.2 + self.nt_m2.value() * 0.1)

        draw_glow(ax1, pos1, 0, "#58a6ff", sc1 * 1.5, 15)
        draw_glow(ax1, pos2, 0, "#f0883e", sc2 * 1.5, 15)
        ax1.add_patch(Circle((pos1, 0), sc1 * 0.3, fc="#58a6ff",
                             ec="#79c0ff", lw=1.5, zorder=10))
        ax1.add_patch(Circle((pos2, 0), sc2 * 0.3, fc="#f0883e",
                             ec="#ffa657", lw=1.5, zorder=10))
        ax1.text(pos1, -0.85, f"m₁={self.nt_m1.value():.1f} M☉",
                 ha="center", color="#58a6ff", fontsize=9, fontweight="bold")
        ax1.text(pos2, -0.85, f"m₂={self.nt_m2.value():.1f} M☉",
                 ha="center", color="#f0883e", fontsize=9, fontweight="bold")

        arrow_len = min(1.0, F / 1e25 * 0.5)
        ax1.annotate("", xy=(pos1 + sc1 * 0.3 + arrow_len, 0),
                     xytext=(pos1 + sc1 * 0.3, 0),
                     arrowprops=dict(arrowstyle="->", color="#ff7b72",
                                     lw=2.5, mutation_scale=15))
        ax1.annotate("", xy=(pos2 - sc2 * 0.3 - arrow_len, 0),
                     xytext=(pos2 - sc2 * 0.3, 0),
                     arrowprops=dict(arrowstyle="->", color="#ff7b72",
                                     lw=2.5, mutation_scale=15))
        ax1.text(0, 0.35, "F", ha="center", color="#ff7b72",
                 fontsize=14, fontweight="bold")

        ax1.annotate("", xy=(pos2, -0.55), xytext=(pos1, -0.55),
                     arrowprops=dict(arrowstyle="<->", color="#8b949e", lw=1))
        ax1.text(0, -0.7, f"r = {self.nt_r.value():.2f} AU",
                 ha="center", color="#8b949e", fontsize=9)

        for y_off in np.linspace(-0.5, 0.5, 5):
            xs = np.linspace(pos1 + 0.4, pos2 - 0.4, 50)
            ys = y_off * np.sin(np.linspace(0, np.pi, 50)) * 0.5
            ax1.plot(xs, ys, color="#58a6ff", alpha=0.12, lw=0.8, zorder=1)

        ax1.set_xlim(-4, 4)
        ax1.set_ylim(-2, 1.5)
        ax1.set_axis_off()

        # RIGHT: F vs r
        ax2 = fig.add_subplot(122)
        style_ax(ax2, "Force vs Distance", "Distance (AU)", "Force (N)")

        distances = np.linspace(0.05, 5, 500) * AU
        forces = G * m1 * m2 / distances ** 2
        ax2.plot(distances / AU, forces, color="#58a6ff", lw=2.5, zorder=5)
        ax2.fill_between(distances / AU, forces, alpha=0.12, color="#58a6ff")
        ax2.scatter([self.nt_r.value()], [F], color="#f0883e", s=100, zorder=10,
                    edgecolors="white", linewidths=1.5)
        ax2.axvline(self.nt_r.value(), color="#f0883e", ls="--", alpha=0.4)
        ax2.axhline(F, color="#f0883e", ls="--", alpha=0.25)
        ax2.annotate(f"F = {F:.2e} N", xy=(self.nt_r.value(), F),
                     xytext=(self.nt_r.value() + 0.8, F * 3),
                     arrowprops=dict(arrowstyle="->", color="#f0883e", lw=1),
                     color="#f0883e", fontsize=10, fontweight="bold",
                     bbox=dict(boxstyle="round,pad=0.3", fc="#161b22",
                               ec="#f0883e", alpha=0.9))
        ax2.set_yscale("log")
        ax2.grid(True, alpha=0.1, color="#30363d")
        fig.tight_layout()
        self.nt_canvas.draw()

    # ══════════════════════════════════════════════════════════════════════════
    #  PAGE 2 — ESCAPE VELOCITY
    # ══════════════════════════════════════════════════════════════════════════
    def _build_escape(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(32, 28, 32, 28)
        lay.setSpacing(10)

        lay.addWidget(styled_label("Escape Velocity", 26, "#58a6ff", True))
        lay.addWidget(EquationLabel(
            r"v_e=\sqrt{\frac{2GM}{r}}\qquad r_s=\frac{2GM}{c^2}\text{ when }v_e=c",
            22, "#f0883e", (9, 0.8)))
        lay.addWidget(styled_label(
            "The minimum speed to escape a body's gravitational pull. When vₑ = c, "
            "we get the Schwarzschild radius — the event horizon of a black hole.",
            12, "#8b949e"))

        ctrl = QHBoxLayout()
        ctrl.addWidget(styled_label("Preset:", 11))
        self.esc_combo = QComboBox()
        self.esc_combo.addItems([
            "Custom", "Moon", "Mars", "Earth", "Jupiter", "Sun",
            "White Dwarf", "Neutron Star", "Stellar BH (10 M☉)", "Sgr A* (4M M☉)"])
        self.esc_combo.currentIndexChanged.connect(self._esc_preset)
        ctrl.addWidget(self.esc_combo)
        ctrl.addWidget(styled_label("Mass (M☉):", 11))
        self.esc_mass = QDoubleSpinBox()
        self.esc_mass.setRange(1e-12, 1e8)
        self.esc_mass.setValue(1.0)
        self.esc_mass.setDecimals(10)
        ctrl.addWidget(self.esc_mass)
        ctrl.addWidget(styled_label("Radius (km):", 11))
        self.esc_radius = QDoubleSpinBox()
        self.esc_radius.setRange(0.0001, 1e9)
        self.esc_radius.setValue(696340)
        self.esc_radius.setDecimals(4)
        ctrl.addWidget(self.esc_radius)
        btn = QPushButton("⟳  Calculate")
        btn.clicked.connect(self._update_escape)
        ctrl.addWidget(btn)
        ctrl.addStretch()
        lay.addLayout(ctrl)

        self.esc_result = styled_label("", 14, "#7ee787", True)
        lay.addWidget(self.esc_result)

        self.esc_canvas = MplCanvas(self, 10, 5.5)
        lay.addWidget(self.esc_canvas, 1)
        self._update_escape()
        self.stack.addWidget(self._scroll_wrap(page))

    _ESC_PRESETS = {
        1: (7.342e22 / M_SUN, 1737.4), 2: (6.417e23 / M_SUN, 3389.5),
        3: (1.0, 6371), 4: (317.8, 69911), 5: (1.0, 696340),
        6: (1.0, 5000), 7: (1.4, 10),
        8: (10.0, 2 * G * 10 * M_SUN / c ** 2 / 1000),
        9: (4e6, 2 * G * 4e6 * M_SUN / c ** 2 / 1000),
    }

    def _esc_preset(self, idx):
        if idx in self._ESC_PRESETS:
            m, r = self._ESC_PRESETS[idx]
            self.esc_mass.setValue(m)
            self.esc_radius.setValue(r)

    def _update_escape(self):
        M = self.esc_mass.value() * M_SUN
        r = self.esc_radius.value() * 1e3
        if r <= 0:
            return
        ve = math.sqrt(2 * G * M / r)
        pct_c = ve / c * 100
        rs = 2 * G * M / c ** 2
        self.esc_result.setText(
            f"vₑ = {fmt(ve / 1e3, 'km/s')}  ({pct_c:.4f}% c)  |  "
            f"Schwarzschild radius: {fmt(rs / 1e3, 'km')}")

        fig = self.esc_canvas.fig
        fig.clear()

        # LEFT: gravitational well
        ax1 = fig.add_subplot(121)
        style_ax(ax1, "Gravitational Well & Escape")
        ax1.set_facecolor("#050510")
        ax1.set_aspect("equal")

        sx, sy, ss, sb = generate_stars(120, (-5, 5), (-4, 6), seed=10)
        for i in range(len(sx)):
            ax1.plot(sx[i], sy[i], ".", color="white",
                     markersize=ss[i], alpha=sb[i] * 0.3, zorder=0)

        well_x = np.linspace(-3, 3, 300)
        well_y = -1.5 * np.exp(-well_x ** 2 / 2.0)
        ax1.fill_between(well_x, well_y, -4, color="#0a1a3a", alpha=0.5, zorder=1)
        ax1.plot(well_x, well_y, color="#58a6ff", lw=2, zorder=2)
        draw_glow(ax1, 0, -1.5, "#58a6ff", 1.0, 18, zorder=3)
        ax1.add_patch(Circle((0, -1.5), 0.4, fc="#1a3a5c", ec="#58a6ff",
                             lw=2, zorder=10))

        arrows = [(0.0, "#7ee787", "vₑ (escapes)", 2.5, True),
                  (0.8, "#f0883e", "0.5 vₑ", 1.2, False),
                  (1.6, "#ff7b72", "0.25 vₑ", 0.6, False)]
        for y_off, col, label, alen, escapes in arrows:
            y0 = -1.5 + 0.4 + 0.1
            ax1.annotate("", xy=(alen, y0 + y_off), xytext=(0, y0 + y_off),
                         arrowprops=dict(arrowstyle="->", color=col,
                                         lw=2.5, mutation_scale=15))
            if not escapes:
                t = np.linspace(0, 2.5, 80)
                traj_y = y0 + y_off + (alen / 2.5) * t - 0.3 * t ** 2
                ax1.plot(alen * t / 2.5 - 0.3 * t, traj_y,
                         color=col, alpha=0.3, lw=1, ls="--", zorder=4)
            ax1.text(alen + 0.15, y0 + y_off, label, color=col,
                     fontsize=8, fontweight="bold", va="center")

        ax1.text(3.2, 5, "✓ ESCAPES", color="#7ee787", fontsize=11,
                 fontweight="bold", ha="center",
                 bbox=dict(fc="#0d1117", ec="#7ee787", pad=3, alpha=0.8))
        ax1.text(-3.2, 5, "✗ FALLS BACK", color="#ff7b72", fontsize=11,
                 fontweight="bold", ha="center",
                 bbox=dict(fc="#0d1117", ec="#ff7b72", pad=3, alpha=0.8))

        ax1.set_xlim(-5, 5)
        ax1.set_ylim(-4, 6)
        ax1.set_axis_off()

        # RIGHT: comparison bar chart
        ax2 = fig.add_subplot(122)
        style_ax(ax2, "Escape Velocities Compared", "vₑ (km/s)")

        bodies = [
            ("Moon", 7.342e22, 1737.4e3, "#8b949e"),
            ("Mars", 6.417e23, 3389.5e3, "#c1440e"),
            ("Earth", M_EARTH, R_EARTH, "#58a6ff"),
            ("Jupiter", 1.898e27, 69911e3, "#f0883e"),
            ("Sun", M_SUN, 696340e3, "#ffd700"),
            ("W.Dwarf", M_SUN, 5000e3, "#aaaaff"),
            ("N.Star", 1.4 * M_SUN, 10e3, "#ff6666"),
            ("BH 10M☉", 10 * M_SUN, 2 * G * 10 * M_SUN / c ** 2, "#ff4444"),
        ]
        names = [b[0] for b in bodies]
        vescs = [math.sqrt(2 * G * b[1] / b[2]) / 1e3 for b in bodies]
        cols = [b[3] for b in bodies]

        bars = ax2.barh(names, vescs, color=cols, edgecolor="#30363d",
                        height=0.6, alpha=0.85)
        ax2.axvline(ve / 1e3, color="#7ee787", ls="--", lw=2,
                    label=f"Selected: {ve / 1e3:.1f} km/s")
        ax2.axvline(ve / 1e3, color="#7ee787", lw=8, alpha=0.08)
        ax2.axvline(c / 1e3, color="#ff7b72", ls=":", lw=2,
                    label="Speed of light c")

        for bar, v in zip(bars, vescs):
            ax2.text(v + c / 1e3 * 0.02, bar.get_y() + bar.get_height() / 2,
                     f"{v:.0f}", va="center", color="#c9d1d9", fontsize=8)

        ax2.set_xscale("log")
        ax2.legend(facecolor="#161b22", edgecolor="#30363d",
                   labelcolor="#c9d1d9", fontsize=9, loc="lower right")
        ax2.grid(True, axis="x", alpha=0.1, color="#30363d")
        fig.tight_layout()
        self.esc_canvas.draw()

    # ══════════════════════════════════════════════════════════════════════════
    #  PAGE 3 — ORBITAL MECHANICS
    # ══════════════════════════════════════════════════════════════════════════
    def _build_orbital(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(32, 28, 32, 28)
        lay.setSpacing(10)

        lay.addWidget(styled_label("Orbital Mechanics — Kepler's Laws",
                                   26, "#58a6ff", True))
        lay.addWidget(EquationLabel(
            r"v_{orbit}=\sqrt{\frac{GM}{r}}\qquad T=2\pi\sqrt{\frac{r^3}{GM}}\qquad T^2\propto r^3",
            18, "#f0883e", (10, 0.7)))

        ctrl = QHBoxLayout()
        ctrl.addWidget(styled_label("Star (M☉):", 11))
        self.orb_mass = QDoubleSpinBox()
        self.orb_mass.setRange(0.1, 100)
        self.orb_mass.setValue(1.0)
        ctrl.addWidget(self.orb_mass)
        ctrl.addWidget(styled_label("a (AU):", 11))
        self.orb_sma = QDoubleSpinBox()
        self.orb_sma.setRange(0.05, 50)
        self.orb_sma.setValue(1.0)
        self.orb_sma.setSingleStep(0.1)
        ctrl.addWidget(self.orb_sma)
        ctrl.addWidget(styled_label("Eccentricity:", 11))
        self.orb_ecc = QDoubleSpinBox()
        self.orb_ecc.setRange(0.0, 0.95)
        self.orb_ecc.setValue(0.3)
        self.orb_ecc.setSingleStep(0.05)
        self.orb_ecc.setDecimals(2)
        ctrl.addWidget(self.orb_ecc)
        self.orb_pause = QPushButton("⏸  Pause")
        self.orb_pause.setCheckable(True)
        ctrl.addWidget(self.orb_pause)
        ctrl.addStretch()
        lay.addLayout(ctrl)

        self.orb_info = styled_label("", 12, "#7ee787", True)
        lay.addWidget(self.orb_info)

        self.orb_canvas = MplCanvas(self, 10, 6.5)
        lay.addWidget(self.orb_canvas, 1)
        self.orbit_trail = []
        self.orbit_angle = 0.0
        self.stack.addWidget(self._scroll_wrap(page))

    def _animate_orbit(self):
        if self.orb_pause.isChecked():
            return

        M_star = self.orb_mass.value() * M_SUN
        a = self.orb_sma.value() * AU
        e = self.orb_ecc.value()
        T = 2 * math.pi * math.sqrt(a ** 3 / (G * M_star))
        omega = 2 * math.pi / T
        dt = T / 300
        self.orbit_angle += omega * dt
        if self.orbit_angle > 2 * math.pi:
            self.orbit_angle -= 2 * math.pi

        E = self._solve_kepler(self.orbit_angle, e)
        x = a * (math.cos(E) - e)
        y = a * math.sqrt(1 - e ** 2) * math.sin(E)
        r = a * (1 - e * math.cos(E))
        v = math.sqrt(G * M_star * (2 / r - 1 / a))
        KE = 0.5 * M_EARTH * v ** 2
        PE = -G * M_star * M_EARTH / r

        self.orb_info.setText(
            f"Period: {fmt(T / 86400 / 365.25, 'yr')}  |  "
            f"v: {fmt(v / 1e3, 'km/s')}  |  r: {fmt(r / AU, 'AU')}  |  "
            f"KE: {fmt(KE, 'J')}  |  PE: {fmt(PE, 'J')}  |  "
            f"E: {fmt(KE + PE, 'J')}")

        self.orbit_trail.append((x / AU, y / AU))
        if len(self.orbit_trail) > 250:
            self.orbit_trail = self.orbit_trail[-250:]

        ax = self.orb_canvas.fresh_ax()
        style_ax(ax, "Orbital Simulation")

        sx, sy, ss, sb = generate_stars(200, (-3, 3), (-3, 3), seed=12)
        for i in range(len(sx)):
            ax.plot(sx[i], sy[i], ".", color="white",
                    markersize=ss[i], alpha=sb[i] * 0.3, zorder=0)

        thetas = np.linspace(0, 2 * np.pi, 500)
        ax.plot((a * (np.cos(thetas) - e)) / AU,
                (a * np.sqrt(1 - e ** 2) * np.sin(thetas)) / AU,
                color="#30363d", lw=1, ls="--", zorder=1)

        # Swept area
        n_sweep = max(2, len(self.orbit_trail) // 6)
        if len(self.orbit_trail) > 2:
            sweep_x = [0] + [p[0] for p in self.orbit_trail[-n_sweep:]] + [0]
            sweep_y = [0] + [p[1] for p in self.orbit_trail[-n_sweep:]] + [0]
            ax.fill(sweep_x, sweep_y, color="#1f6feb", alpha=0.10, zorder=2)

        # Fading trail
        if len(self.orbit_trail) > 2:
            trail = np.array(self.orbit_trail)
            n = len(trail)
            alphas = np.linspace(0.03, 0.95, n - 1)
            for j in range(n - 1):
                ax.plot(trail[j:j + 2, 0], trail[j:j + 2, 1],
                        color="#58a6ff", alpha=alphas[j], lw=2.2, zorder=3)

        draw_glow(ax, 0, 0, "#ffd700", 0.3, 18)
        ax.scatter([0], [0], color="#ffd700", s=200, zorder=10,
                   edgecolors="#ff8c00", linewidths=1.5)

        draw_glow(ax, x / AU, y / AU, "#58a6ff", 0.18, 12)
        ax.scatter([x / AU], [y / AU], color="#58a6ff", s=80, zorder=11,
                   edgecolors="white", linewidths=1)

        # Velocity arrow
        dE_dt = omega / (1 - e * math.cos(E))
        vx = -a * math.sin(E) * dE_dt
        vy = a * math.sqrt(1 - e ** 2) * math.cos(E) * dE_dt
        v_mag = math.sqrt(vx ** 2 + vy ** 2)
        sc = 0.12 * a / max(v_mag, 1e-10)
        ax.annotate("", xy=((x + vx * sc) / AU, (y + vy * sc) / AU),
                    xytext=(x / AU, y / AU),
                    arrowprops=dict(arrowstyle="->", color="#7ee787",
                                    lw=2.5, mutation_scale=15), zorder=12)

        if e > 0.01:
            rp = a * (1 - e) / AU
            ra = a * (1 + e) / AU
            ax.scatter([rp], [0], color="#f0883e", marker="^", s=55, zorder=8)
            ax.scatter([-ra], [0], color="#f0883e", marker="v", s=55, zorder=8)
            ax.annotate("Periapsis", (rp, 0), textcoords="offset points",
                        xytext=(5, 10), color="#f0883e", fontsize=8)
            ax.annotate("Apoapsis", (-ra, 0), textcoords="offset points",
                        xytext=(5, 10), color="#f0883e", fontsize=8)

        lim = max(a * (1 + e) / AU * 1.4, 0.3)
        ax.set_xlim(-lim, lim)
        ax.set_ylim(-lim, lim)
        ax.set_xlabel("x (AU)")
        ax.set_ylabel("y (AU)")
        ax.set_aspect("equal")
        ax.grid(True, alpha=0.05, color="#30363d")
        self.orb_canvas.fig.tight_layout()
        self.orb_canvas.draw()

    # ══════════════════════════════════════════════════════════════════════════
    #  PAGE 4 — BLACK HOLES
    # ══════════════════════════════════════════════════════════════════════════
    def _build_blackhole(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(32, 28, 32, 28)
        lay.setSpacing(10)

        lay.addWidget(styled_label(
            "Black Holes — Event Horizon & Lensing", 24, "#58a6ff", True))
        lay.addWidget(EquationLabel(
            r"r_s=\frac{2GM}{c^2}\qquad \theta_E=\sqrt{\frac{4GM}{c^2 D}}",
            22, "#f0883e", (9, 0.8)))
        lay.addWidget(styled_label(
            "The Schwarzschild radius defines the event horizon. Gravitational lensing "
            "bends light around the black hole, creating the Einstein ring. The accretion "
            "disk shows Doppler beaming — the approaching side is brighter.", 12, "#8b949e"))

        ctrl = QHBoxLayout()
        ctrl.addWidget(styled_label("BH Mass (M☉):", 11))
        self.bh_mass = QDoubleSpinBox()
        self.bh_mass.setRange(0.1, 1e8)
        self.bh_mass.setValue(10.0)
        self.bh_mass.setSingleStep(1)
        ctrl.addWidget(self.bh_mass)
        ctrl.addWidget(styled_label("Distance (kpc):", 11))
        self.bh_dist = QDoubleSpinBox()
        self.bh_dist.setRange(0.1, 100)
        self.bh_dist.setValue(8.0)
        self.bh_dist.setSingleStep(0.5)
        ctrl.addWidget(self.bh_dist)
        ctrl.addWidget(styled_label("Inclination (°):", 11))
        self.bh_incl = QSlider(Qt.Horizontal)
        self.bh_incl.setRange(10, 85)
        self.bh_incl.setValue(70)
        self.bh_incl_lbl = styled_label("70°", 11, "#f0883e")
        self.bh_incl.valueChanged.connect(
            lambda v: self.bh_incl_lbl.setText(f"{v}°"))
        ctrl.addWidget(self.bh_incl)
        ctrl.addWidget(self.bh_incl_lbl)
        btn = QPushButton("⟳  Recalculate")
        btn.clicked.connect(self._update_blackhole)
        ctrl.addWidget(btn)
        ctrl.addStretch()
        lay.addLayout(ctrl)

        self.bh_result = styled_label("", 12, "#7ee787", True)
        lay.addWidget(self.bh_result)

        self.bh_canvas = MplCanvas(self, 10, 7)
        lay.addWidget(self.bh_canvas, 1)
        self.bh_disk_angle = 0.0
        self._update_blackhole()
        self.stack.addWidget(self._scroll_wrap(page))

    def _update_blackhole(self):
        M = self.bh_mass.value() * M_SUN
        rs = 2 * G * M / c ** 2
        D = self.bh_dist.value() * 3.086e19
        theta_E = math.sqrt(4 * G * M / (c ** 2 * D)) * 206265

        self.bh_result.setText(
            f"rₛ = {fmt(rs / 1e3, 'km')}  |  "
            f"Photon sphere = {fmt(1.5 * rs / 1e3, 'km')}  |  "
            f"ISCO = {fmt(3 * rs / 1e3, 'km')}  |  "
            f"Einstein angle = {theta_E:.4f}\"")

        self._bh_stars = self._generate_lensed_stars()

    def _generate_lensed_stars(self):
        rng = np.random.RandomState(42)
        n = 500
        bx = rng.uniform(-5, 5, n)
        by = rng.uniform(-5, 5, n)
        beta = np.sqrt(bx ** 2 + by ** 2)
        beta = np.maximum(beta, 1e-6)

        tp = (beta + np.sqrt(beta ** 2 + 4)) / 2
        tm = (beta - np.sqrt(beta ** 2 + 4)) / 2
        cp, sp = bx / beta, by / beta

        mu_p = 0.5 + (beta ** 2 + 2) / (2 * beta * np.sqrt(beta ** 2 + 4))
        mu_m = -0.5 + (beta ** 2 + 2) / (2 * beta * np.sqrt(beta ** 2 + 4))

        sizes = rng.exponential(1.0, n) + 0.3
        cstars = rng.choice(["#ffffff", "#aaccff", "#ffddaa", "#ffaaaa"], n)
        return (tp * cp, tp * sp, tm * cp, tm * sp, mu_p, np.abs(mu_m),
                sizes, cstars, beta)

    def _animate_blackhole(self):
        self.bh_disk_angle += 0.04
        incl = self.bh_incl.value() * math.pi / 180

        fig = self.bh_canvas.fig
        fig.clear()

        # LEFT: gravitational lensing
        ax1 = fig.add_subplot(121)
        style_ax(ax1, "Gravitational Lensing")
        ax1.set_facecolor("#050510")
        ax1.set_aspect("equal")

        (i1x, i1y, i2x, i2y, mp, mm,
         sizes, cstars, beta) = self._bh_stars

        for i in range(len(i1x)):
            if beta[i] > 0.3 and abs(i1x[i]) < 4.5 and abs(i1y[i]) < 4.5:
                ms = min(sizes[i] * mp[i] * 0.8, 8)
                ax1.plot(i1x[i], i1y[i], ".", color=cstars[i],
                         markersize=ms, alpha=min(0.9, 0.3 + mp[i] * 0.08),
                         zorder=5)

        for i in range(len(i2x)):
            if beta[i] > 0.3 and abs(i2x[i]) < 4.5 and abs(i2y[i]) < 4.5:
                ms = min(sizes[i] * mm[i] * 0.5, 4)
                ax1.plot(i2x[i], i2y[i], ".", color=cstars[i],
                         markersize=ms, alpha=min(0.5, 0.1 + mm[i] * 0.08),
                         zorder=5)

        ax1.add_patch(Circle((0, 0), 1.0, fc="none", ec="#58a6ff",
                             lw=1.3, ls="--", alpha=0.5, zorder=8))
        ax1.text(1.1, 0.15, "Einstein\nring", color="#58a6ff",
                 fontsize=7, alpha=0.7)
        ax1.add_patch(Circle((0, 0), 0.5, fc="black", ec="none", zorder=9))
        for k in range(10):
            ax1.add_patch(Circle((0, 0), 0.52 + k * 0.035, fc="none",
                                 ec="#ff6600", lw=2,
                                 alpha=0.15 * (1 - k / 10), zorder=8))

        ax1.set_xlim(-4, 4)
        ax1.set_ylim(-4, 4)
        ax1.set_xlabel("θ / θ_E")
        ax1.set_ylabel("θ / θ_E")

        # RIGHT: accretion disk
        ax2 = fig.add_subplot(122)
        style_ax(ax2, "Accretion Disk & Event Horizon")
        ax2.set_facecolor("#050510")
        ax2.set_aspect("equal")

        for k in range(15, 0, -1):
            r = 18 * (k / 15)
            ax2.add_patch(Circle((0, 0), r, fc="#1a0500", alpha=0.03,
                                 ec="none", zorder=0))

        n_rings, n_per = 25, 70
        for j in range(n_rings, 0, -1):
            rd = 3 + j * 0.5
            tf = (3 / rd) ** 0.75
            ok = (3 / rd) ** 1.5
            for k in range(n_per):
                phi = 2 * math.pi * k / n_per + self.bh_disk_angle * ok
                x3 = rd * math.cos(phi)
                y3 = rd * math.sin(phi)
                xp = x3
                yp = y3 * math.cos(incl)
                vlos = rd * ok * math.sin(phi) * math.sin(incl)
                doppler = 1.0 / (1.0 + vlos * 0.3)
                bright = min(1.0, tf * doppler * 1.5)
                if tf > 0.7:
                    col = cm.hot(min(1.0, bright * 1.2))
                elif tf > 0.4:
                    col = cm.inferno(min(1.0, bright))
                else:
                    col = cm.magma(min(1.0, bright * 0.8))
                ax2.plot(xp, yp, ".", color=col,
                         markersize=max(1, 3 * tf),
                         alpha=min(0.9, bright), zorder=5)

        ax2.add_patch(Circle((0, 0), 2.5, fc="black", ec="none", zorder=10))
        ax2.add_patch(Circle((0, 0), 2.5, fc="none", ec="#ff4444",
                             lw=2, zorder=11))
        for k in range(12):
            ax2.add_patch(Circle((0, 0), 2.5 + k * 0.12, fc="none",
                                 ec="#ff6600", lw=2.5,
                                 alpha=0.08 * (1 - k / 12), zorder=9))

        ax2.add_patch(Circle((0, 0), 3.75, fc="none", ec="#ffd700",
                             lw=1, ls="--", alpha=0.6, zorder=11))
        ax2.add_patch(Circle((0, 0), 7.5, fc="none", ec="#7ee787",
                             lw=1, ls=":", alpha=0.5, zorder=11))

        ax2.text(2.7, -0.6, "Event\nHorizon", color="#ff4444",
                 fontsize=7, zorder=12)
        ax2.text(3.9, -0.6, "Photon\nSphere", color="#ffd700",
                 fontsize=7, alpha=0.7, zorder=12)
        ax2.text(7.7, -0.6, "ISCO", color="#7ee787",
                 fontsize=7, alpha=0.6, zorder=12)
        ax2.text(-13, 9, "← Approaching\n   (blueshifted)",
                 color="#79c0ff", fontsize=8, alpha=0.7)
        ax2.text(5, 9, "Receding →\n(redshifted)",
                 color="#ff7b72", fontsize=8, alpha=0.7)

        ax2.set_xlim(-18, 18)
        ax2.set_ylim(-13, 13)
        ax2.set_xlabel("r / rₛ")
        ax2.set_ylabel("r / rₛ")

        fig.tight_layout()
        self.bh_canvas.draw()

    # ══════════════════════════════════════════════════════════════════════════
    #  PAGE 5 — TIME DILATION
    # ══════════════════════════════════════════════════════════════════════════
    def _build_timedilation(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(32, 28, 32, 28)
        lay.setSpacing(10)

        lay.addWidget(styled_label("Gravitational Time Dilation",
                                   26, "#58a6ff", True))
        lay.addWidget(EquationLabel(
            r"d\tau=dt\,\sqrt{1-\frac{r_s}{r}}=dt\,\sqrt{1-\frac{2GM}{rc^2}}",
            22, "#f0883e", (9, 0.8)))

        ctrl = QHBoxLayout()
        ctrl.addWidget(styled_label("Mass (M☉):", 11))
        self.td_mass = QDoubleSpinBox()
        self.td_mass.setRange(0.1, 1e8)
        self.td_mass.setValue(10.0)
        ctrl.addWidget(self.td_mass)
        ctrl.addWidget(styled_label("Distance (rₛ):", 11))
        self.td_slider = QSlider(Qt.Horizontal)
        self.td_slider.setRange(105, 3000)
        self.td_slider.setValue(200)
        self.td_lbl = styled_label("2.00 rₛ", 11, "#f0883e")
        self.td_slider.valueChanged.connect(
            lambda v: self.td_lbl.setText(f"{v / 100:.2f} rₛ"))
        ctrl.addWidget(self.td_slider)
        ctrl.addWidget(self.td_lbl)
        btn = QPushButton("⟳  Update")
        btn.clicked.connect(self._update_td)
        ctrl.addWidget(btn)
        ctrl.addStretch()
        lay.addLayout(ctrl)

        self.td_result = styled_label("", 13, "#7ee787", True)
        lay.addWidget(self.td_result)

        self.td_canvas = MplCanvas(self, 10, 6.5)
        lay.addWidget(self.td_canvas, 1)
        self.td_clock_far = 0.0
        self.td_clock_near = 0.0
        self.td_factor = 1.0
        self._update_td()
        self.stack.addWidget(self._scroll_wrap(page))

    def _update_td(self):
        M = self.td_mass.value() * M_SUN
        rs = 2 * G * M / c ** 2
        rm = self.td_slider.value() / 100.0
        r = rm * rs
        if r <= rs:
            self.td_result.setText(
                "⚠️ Inside the event horizon — time dilation is infinite!")
            self.td_factor = 0.0
        else:
            self.td_factor = math.sqrt(1 - rs / r)
            self.td_result.setText(
                f"dτ/dt = {self.td_factor:.6f}  |  "
                f"1 sec far away = {self.td_factor:.6f} sec here  |  "
                f"Time runs {100 * (1 - self.td_factor):.4f}% slower")

    def _draw_clock(self, ax, cx, cy, radius, angle, label, color, bg):
        ax.add_patch(Circle((cx, cy), radius, fc=bg, ec=color, lw=2.5, zorder=10))
        for k in range(5):
            ax.add_patch(Circle((cx, cy), radius * (1 + 0.05 * (k + 1)),
                                fc="none", ec=color, lw=1.5,
                                alpha=0.1 * (1 - k / 5), zorder=9))
        for h in range(12):
            a = h * math.pi / 6
            ax.plot([cx + radius * 0.8 * math.sin(a),
                     cx + radius * 0.92 * math.sin(a)],
                    [cy + radius * 0.8 * math.cos(a),
                     cy + radius * 0.92 * math.cos(a)],
                    color=color, lw=1.5, alpha=0.6, zorder=11)
        hl = radius * 0.72
        ax.plot([cx, cx + hl * math.sin(angle)],
                [cy, cy + hl * math.cos(angle)],
                color=color, lw=2, zorder=12)
        ax.plot(cx, cy, "o", color=color, markersize=4, zorder=13)
        ax.text(cx, cy - radius - 0.2, label, ha="center", color=color,
                fontsize=9, fontweight="bold", zorder=12)

    def _animate_timedilation(self):
        dt = 0.05
        self.td_clock_far += dt
        self.td_clock_near += dt * self.td_factor

        fig = self.td_canvas.fig
        fig.clear()

        # TOP: animated clocks
        ax1 = fig.add_subplot(211)
        style_ax(ax1, "Clock Comparison — Gravitational Time Dilation")
        ax1.set_facecolor("#0d1117")
        ax1.set_aspect("equal")
        ax1.set_xlim(-3.5, 3.5)
        ax1.set_ylim(-1.8, 2.0)
        ax1.set_axis_off()

        self._draw_clock(ax1, -1.5, 0.3, 0.85,
                         self.td_clock_far * 2 * math.pi,
                         "Far Observer\n(normal time)", "#7ee787", "#0a1a0a")
        self._draw_clock(ax1, 1.5, 0.3, 0.85,
                         self.td_clock_near * 2 * math.pi,
                         f"Near BH\n({self.td_factor:.3f}× rate)", "#ff7b72", "#1a0a0a")

        ax1.annotate("", xy=(0.4, 0.3), xytext=(-0.4, 0.3),
                     arrowprops=dict(arrowstyle="<->", color="#f0883e", lw=2))
        ratio = 1 / max(self.td_factor, 0.001)
        ax1.text(0, 0.7, f"×{ratio:.2f} slower", ha="center",
                 color="#f0883e", fontsize=12, fontweight="bold")

        # BOTTOM: curve
        ax2 = fig.add_subplot(212)
        style_ax(ax2, "Time Dilation Factor", "r / rₛ", "dτ / dt")

        rr = np.linspace(1.001, 25, 1000)
        ff = np.sqrt(1 - 1 / rr)
        ax2.fill_between(rr, ff, alpha=0.1, color="#58a6ff")
        ax2.plot(rr, ff, color="#58a6ff", lw=2.5, zorder=5)

        rm = self.td_slider.value() / 100.0
        if self.td_factor > 0:
            ax2.scatter([rm], [self.td_factor], color="#f0883e", s=110,
                        zorder=10, edgecolors="white", linewidths=1.5)
            ax2.annotate(f"{self.td_factor:.4f}", xy=(rm, self.td_factor),
                         xytext=(rm + 2, self.td_factor - 0.08),
                         arrowprops=dict(arrowstyle="->", color="#f0883e"),
                         color="#f0883e", fontsize=10, fontweight="bold")

        ax2.axvspan(1.0, 1.5, alpha=0.08, color="red")
        ax2.axvline(1.5, color="#ffd700", ls=":", alpha=0.5, lw=1)
        ax2.axvline(3.0, color="#7ee787", ls=":", alpha=0.5, lw=1)
        ax2.text(1.25, 0.95, "Inside\nEH", ha="center", color="#ff4444",
                 fontsize=8, fontweight="bold")
        ax2.text(1.55, 0.88, "Photon\nsphere", ha="center",
                 color="#ffd700", fontsize=7, alpha=0.7)
        ax2.text(3.05, 0.88, "ISCO", ha="center",
                 color="#7ee787", fontsize=7, alpha=0.7)

        ax2.set_xlim(1, 25)
        ax2.set_ylim(0, 1.05)
        ax2.grid(True, alpha=0.08, color="#30363d")
        fig.tight_layout()
        self.td_canvas.draw()

    # ══════════════════════════════════════════════════════════════════════════
    #  PAGE 6 — HAWKING RADIATION
    # ══════════════════════════════════════════════════════════════════════════
    def _build_hawking(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(32, 28, 32, 28)
        lay.setSpacing(10)

        lay.addWidget(styled_label("Hawking Radiation & Evaporation",
                                   24, "#58a6ff", True))
        lay.addWidget(EquationLabel(
            r"T_H=\frac{\hbar c^3}{8\pi G M k_B}\qquad t_{evap}\approx\frac{5120\pi G^2 M^3}{\hbar c^4}",
            18, "#f0883e", (10, 0.8)))
        lay.addWidget(styled_label(
            "Black holes radiate thermal radiation due to quantum effects near the event "
            "horizon. Virtual particle pairs form; one falls in, one escapes. Smaller "
            "black holes are hotter and evaporate faster.", 12, "#8b949e"))

        ctrl = QHBoxLayout()
        ctrl.addWidget(styled_label("BH Mass (M☉):", 11))
        self.hk_mass = QDoubleSpinBox()
        self.hk_mass.setRange(1e-20, 1e6)
        self.hk_mass.setValue(1.0)
        self.hk_mass.setDecimals(10)
        ctrl.addWidget(self.hk_mass)
        btn = QPushButton("⟳  Calculate")
        btn.clicked.connect(self._update_hawking)
        ctrl.addWidget(btn)
        ctrl.addStretch()
        lay.addLayout(ctrl)

        self.hk_result = styled_label("", 12, "#7ee787", True)
        lay.addWidget(self.hk_result)

        self.hk_canvas = MplCanvas(self, 10, 6)
        lay.addWidget(self.hk_canvas, 1)
        self._update_hawking()
        self.stack.addWidget(self._scroll_wrap(page))

    def _update_hawking(self):
        M = self.hk_mass.value() * M_SUN
        T_H = hbar * c ** 3 / (8 * math.pi * G * M * k_B)
        t_evap = 5120 * math.pi * G ** 2 * M ** 3 / (hbar * c ** 4)
        rs = 2 * G * M / c ** 2
        A = 4 * math.pi * rs ** 2
        L = sigma_SB * A * T_H ** 4
        T_CMB = 2.725

        self.hk_result.setText(
            f"T_H = {fmt(T_H, 'K')}  |  "
            f"t_evap = {fmt(t_evap / 3.156e7, 'yr')}  |  "
            f"Luminosity = {fmt(L, 'W')}  |  "
            f"{'Hotter' if T_H > T_CMB else 'Colder'} than CMB ({T_CMB} K)")

        fig = self.hk_canvas.fig
        fig.clear()

        # LEFT: mechanism diagram
        ax1 = fig.add_subplot(121)
        style_ax(ax1, "Hawking Radiation Mechanism")
        ax1.set_facecolor("#050510")
        ax1.set_aspect("equal")

        ax1.add_patch(Circle((0, 0), 1.0, fc="black", ec="#ff4444",
                             lw=2, zorder=10))
        for k in range(10):
            ax1.add_patch(Circle((0, 0), 1.02 + k * 0.04, fc="none",
                                 ec="#ff4444", lw=1.5,
                                 alpha=0.12 * (1 - k / 10), zorder=9))

        rng = np.random.RandomState(123)
        for i in range(14):
            angle = rng.uniform(0, 2 * math.pi)
            r_start = 1.05 + rng.uniform(0, 0.15)
            sep = rng.uniform(0.15, 0.35)
            xe = (r_start + sep) * math.cos(angle)
            ye = (r_start + sep) * math.sin(angle)
            ax1.plot(xe, ye, "o", color="#7ee787", markersize=4, zorder=12)
            dx, dy = 0.3 * math.cos(angle), 0.3 * math.sin(angle)
            ax1.annotate("", xy=(xe + dx, ye + dy), xytext=(xe, ye),
                         arrowprops=dict(arrowstyle="->", color="#7ee787",
                                         lw=1.5, alpha=0.7), zorder=11)
            xf = (r_start - sep * 0.5) * math.cos(angle)
            yf = (r_start - sep * 0.5) * math.sin(angle)
            ax1.plot(xf, yf, "o", color="#ff7b72", markersize=3, zorder=12)

        ax1.text(0, 0, "BH", ha="center", va="center", color="white",
                 fontsize=10, fontweight="bold", zorder=15)
        ax1.text(1.8, 1.5, "Particle\nescapes ↑", color="#7ee787",
                 fontsize=9, fontweight="bold")
        ax1.text(-2.2, -1.5, "Particle\nfalls in ↓", color="#ff7b72",
                 fontsize=9, fontweight="bold")
        ax1.text(0, -2.2, "Virtual pair\ncreation", color="#ffd700",
                 fontsize=9, ha="center", fontweight="bold")

        ax1.set_xlim(-2.8, 2.8)
        ax1.set_ylim(-2.8, 2.8)
        ax1.set_axis_off()

        # RIGHT: temperature vs mass
        ax2 = fig.add_subplot(122)
        style_ax(ax2, "Hawking Temperature vs Mass", "Mass (M☉)", "Temperature (K)")

        ms = np.logspace(-20, 6, 1000)
        mk = ms * M_SUN
        temps = hbar * c ** 3 / (8 * math.pi * G * mk * k_B)

        pts = np.array([np.log10(ms), np.log10(temps)]).T.reshape(-1, 1, 2)
        segs = np.concatenate([pts[:-1], pts[1:]], axis=1)
        norm = mcolors.Normalize(vmin=np.log10(temps.min()),
                                 vmax=np.log10(temps.max()))
        lc = LineCollection(segs, cmap="hot", norm=norm, lw=3, zorder=5)
        lc.set_array(np.log10(temps[:-1]))
        ax2.add_collection(lc)

        ax2.axhline(2.725, color="#58a6ff", ls="--", lw=2,
                    label="CMB: 2.725 K", zorder=6)
        ax2.scatter([self.hk_mass.value()], [T_H], color="#7ee787", s=120,
                    zorder=10, edgecolors="white", linewidths=2)
        ax2.annotate(f"{T_H:.2e} K", xy=(self.hk_mass.value(), T_H),
                     xytext=(self.hk_mass.value() * 80, T_H * 8),
                     arrowprops=dict(arrowstyle="->", color="#7ee787", lw=1.5),
                     color="#7ee787", fontsize=10, fontweight="bold",
                     bbox=dict(boxstyle="round,pad=0.3", fc="#161b22",
                               ec="#7ee787", alpha=0.9))

        Mc = hbar * c ** 3 / (8 * math.pi * G * 2.725 * k_B)
        ax2.axvline(Mc / M_SUN, color="#ffd700", ls=":", alpha=0.5)
        ax2.text(Mc / M_SUN * 3, 1e5,
                 f"Crossover\n{Mc / M_SUN:.2e} M☉",
                 color="#ffd700", fontsize=8, alpha=0.7)

        ax2.set_xscale("log")
        ax2.set_yscale("log")
        ax2.set_xlim(1e-20, 1e6)
        ax2.set_ylim(1e-20, 1e12)
        ax2.legend(facecolor="#161b22", edgecolor="#30363d",
                   labelcolor="#c9d1d9", fontsize=9)
        ax2.grid(True, alpha=0.08, color="#30363d", which="both")
        fig.tight_layout()
        self.hk_canvas.draw()

    # ══════════════════════════════════════════════════════════════════════════
    #  PAGE 7 — FIELD SIMULATOR
    # ══════════════════════════════════════════════════════════════════════════
    def _build_simulator(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(32, 28, 32, 28)
        lay.setSpacing(10)

        lay.addWidget(styled_label("Gravitational Field Simulator",
                                   26, "#58a6ff", True))
        lay.addWidget(EquationLabel(
            r"\vec{g}=-\nabla\Phi=-\sum_i\frac{Gm_i}{|\vec{r}-\vec{r}_i|^2}\hat{r}_i\qquad\nabla^2\Phi=4\pi G\rho",
            18, "#f0883e", (10, 0.7)))
        lay.addWidget(styled_label(
            "Click to place masses. The colormap shows gravitational potential, "
            "streamlines show field direction. Adjust mass and extent below.",
            12, "#8b949e"))

        ctrl = QHBoxLayout()
        ctrl.addWidget(styled_label("Mass (M☉):", 11))
        self.sim_mass_spin = QDoubleSpinBox()
        self.sim_mass_spin.setRange(0.1, 100)
        self.sim_mass_spin.setValue(1.0)
        self.sim_mass_spin.setSingleStep(0.5)
        ctrl.addWidget(self.sim_mass_spin)
        ctrl.addWidget(styled_label("Extent (AU):", 11))
        self.sim_extent = QDoubleSpinBox()
        self.sim_extent.setRange(0.5, 50)
        self.sim_extent.setValue(5.0)
        self.sim_extent.setSingleStep(0.5)
        ctrl.addWidget(self.sim_extent)
        btn_c = QPushButton("🗑  Clear")
        btn_c.clicked.connect(self._clear_sim)
        ctrl.addWidget(btn_c)
        btn_u = QPushButton("⟳  Redraw")
        btn_u.clicked.connect(self._update_sim)
        ctrl.addWidget(btn_u)
        ctrl.addStretch()
        lay.addLayout(ctrl)

        self.sim_canvas = MplCanvas(self, 10, 7)
        self.sim_canvas.mpl_connect("button_press_event", self._on_sim_click)
        lay.addWidget(self.sim_canvas, 1)
        self.sim_info = styled_label("Click on the plot to place masses",
                                     11, "#8b949e")
        lay.addWidget(self.sim_info)
        self.sim_masses = [(0, 0, 1.0 * M_SUN)]
        self._update_sim()
        self.stack.addWidget(self._scroll_wrap(page))

    def _on_sim_click(self, event):
        if event.inaxes is None:
            return
        m = self.sim_mass_spin.value() * M_SUN
        self.sim_masses.append((event.xdata, event.ydata, m))
        self._update_sim()

    def _clear_sim(self):
        self.sim_masses.clear()
        self._update_sim()

    def _update_sim(self):
        ax = self.sim_canvas.fresh_ax()
        ax.set_aspect("equal")
        ext = self.sim_extent.value()
        N = 250
        x = np.linspace(-ext, ext, N)
        y = np.linspace(-ext, ext, N)
        X, Y = np.meshgrid(x, y)
        Phi = np.zeros_like(X)
        gx = np.zeros_like(X)
        gy = np.zeros_like(Y)

        for mx, my, m in self.sim_masses:
            dx, dy = X - mx, Y - my
            r = np.maximum(np.sqrt(dx ** 2 + dy ** 2), 0.05)
            rm = r * AU
            Phi += -G * m / rm
            r3 = rm ** 3
            gx += -G * m * dx * AU / r3
            gy += -G * m * dy * AU / r3

        cmap = mcolors.LinearSegmentedColormap.from_list("gp", [
            "#0d1117", "#0a1a3a", "#0f2b5c", "#1a4a7a", "#2d7aaa",
            "#4ab0c8", "#80d8e0", "#c0f0f0", "#ffffff"])

        vmax = np.percentile(np.abs(Phi), 97)
        im = ax.pcolormesh(X, Y, np.clip(Phi, -vmax, 0),
                           cmap=cmap, shading="gouraud")
        cb = self.sim_canvas.fig.colorbar(im, ax=ax, shrink=0.75, pad=0.02)
        cb.set_label("Gravitational Potential (J/kg)", color="#8b949e", fontsize=9)
        cb.ax.tick_params(colors="#6e7681", labelsize=8)

        try:
            ax.streamplot(x, y, gx, gy, color="#58a6ff", density=1.5,
                          linewidth=0.6, arrowsize=0.8, alpha=0.3)
        except Exception:
            pass

        for mx, my, m in self.sim_masses:
            sz = max(50, min(250, m / M_SUN * 70))
            draw_glow(ax, mx, my, "#ffd700",
                      ext * 0.05 * (m / M_SUN) ** 0.3, 12)
            ax.scatter([mx], [my], color="#ffd700", s=sz, zorder=10,
                       edgecolors="white", linewidths=1.5)
            ax.annotate(f"{m / M_SUN:.1f} M☉", (mx, my),
                        textcoords="offset points", xytext=(10, 10),
                        color="white", fontsize=9, fontweight="bold",
                        bbox=dict(boxstyle="round,pad=0.2", fc="#161b22",
                                  ec="#30363d", alpha=0.9))

        ax.set_xlim(-ext, ext)
        ax.set_ylim(-ext, ext)
        ax.set_xlabel("x (AU)")
        ax.set_ylabel("y (AU)")
        ax.set_title(f"Gravitational Potential & Field — "
                     f"{len(self.sim_masses)} mass(es)")
        self.sim_canvas.fig.tight_layout()
        self.sim_canvas.draw()

        tm = sum(m for _, _, m in self.sim_masses)
        self.sim_info.setText(
            f"Masses: {len(self.sim_masses)}  |  Total: {tm / M_SUN:.2f} M☉  |  "
            f"Click to add, Clear to reset")


# ═══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════
def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = GravityEducationApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()