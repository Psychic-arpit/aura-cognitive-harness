"""
core/motion_engine.py - Mathematically Rigorous Dual Locomotion Engine
Mode 1: Mach Speed (Inhuman 30-60ms Snap Vectors)
Mode 2: Biomimetic Mode (Fitts's Law + Arc-Length Bézier + Dual-Harmonic Tremor + Zero Endpoint Jitter)
"""

import math
import random
import time
from dataclasses import dataclass
from typing import Callable, Optional
from core.win32_fast import fast_mouse_move_abs
from core.failsafe import FAILSAFE

@dataclass
class TrajectoryPoint:
    x: float
    y: float
    timestamp_s: float
    velocity_px_s: float

class MotionEngine:
    def __init__(self, a_fitts: float = 0.080, b_fitts: float = 0.125):
        self.a = a_fitts
        self.b = b_fitts

    def calculate_fitts_duration(self, distance_px: float, target_width_px: float = 32.0) -> float:
        """Calculates human movement duration using Shannon formulation of Fitts's Law."""
        id_bits = math.log2(1.0 + max(distance_px, 1.0) / max(target_width_px, 1.0))
        duration = self.a + self.b * id_bits
        return max(0.120, min(0.850, duration))

    @staticmethod
    def _beta_progress(u: float) -> float:
        """
        Normalized incomplete beta polynomial I_u(2, 3) = 6u^2 - 8u^3 + 3u^4.
        Guarantees s(0) = 0, s(1) = 1, peak velocity at u = 0.333, and zero landing jerk.
        """
        u = max(0.0, min(1.0, u))
        return 6.0 * (u ** 2) - 8.0 * (u ** 3) + 3.0 * (u ** 4)

    @staticmethod
    def _bezier_point(p0, p1, p2, p3, u: float) -> tuple[float, float]:
        """Evaluates cubic Bézier curve at parameter u."""
        omt = 1.0 - u
        omt2 = omt * omt
        omt3 = omt2 * omt
        u2 = u * u
        u3 = u2 * u

        x = omt3 * p0[0] + 3.0 * omt2 * u * p1[0] + 3.0 * omt * u2 * p2[0] + u3 * p3[0]
        y = omt3 * p0[1] + 3.0 * omt2 * u * p1[1] + 3.0 * omt * u2 * p2[1] + u3 * p3[1]
        return x, y

    def _build_arc_length_lut(self, p0, p1, p2, p3, samples: int = 32):
        """Constructs Look-Up Table mapping normalized arc length to parameter u."""
        lut = [(0.0, 0.0)]
        total_len = 0.0
        prev_pt = p0

        for i in range(1, samples + 1):
            u = i / float(samples)
            curr_pt = self._bezier_point(p0, p1, p2, p3, u)
            dist = math.hypot(curr_pt[0] - prev_pt[0], curr_pt[1] - prev_pt[1])
            total_len += dist
            lut.append((u, total_len))
            prev_pt = curr_pt

        return lut, total_len

    @staticmethod
    def _lut_arc_to_u(lut: list[tuple[float, float]], total_len: float, s: float) -> float:
        """Inverts normalized arc length s in [0, 1] to parameter u via binary search interpolation."""
        target_dist = s * total_len
        low, high = 0, len(lut) - 1

        while low <= high:
            mid = (low + high) // 2
            if lut[mid][1] < target_dist:
                low = mid + 1
            else:
                high = mid - 1

        idx = max(1, min(len(lut) - 1, low))
        u0, d0 = lut[idx - 1]
        u1, d1 = lut[idx]

        if d1 == d0:
            return u0
        fraction = (target_dist - d0) / (d1 - d0)
        return u0 + fraction * (u1 - u0)

    def generate_biomimetic_path(
        self,
        start_pt: tuple[float, float],
        target_pt: tuple[float, float],
        target_width_px: float = 32.0,
        framerate: float = 60.0
    ) -> list[TrajectoryPoint]:
        """Generates authentic human trajectory with wrist bow, tremor, and exact landing."""
        dx = target_pt[0] - start_pt[0]
        dy = target_pt[1] - start_pt[1]
        dist = math.hypot(dx, dy)

        if dist < 1.0:
            return [TrajectoryPoint(target_pt[0], target_pt[1], 0.0, 0.0)]

        tau = self.calculate_fitts_duration(dist, target_width_px)
        total_frames = max(6, int(math.ceil(tau * framerate)))

        # Biomechanical lateral bow
        nx = -dy / dist
        ny = dx / dist
        bow_dir = random.choice([-1.0, 1.0])
        bow_amp = dist * random.uniform(0.04, 0.10) * bow_dir

        p0 = start_pt
        p1 = (
            start_pt[0] + dx * random.uniform(0.25, 0.35) + nx * bow_amp * 0.8,
            start_pt[1] + dy * random.uniform(0.25, 0.35) + ny * bow_amp * 0.8,
        )
        p2 = (
            start_pt[0] + dx * random.uniform(0.65, 0.80) + nx * bow_amp * 0.4,
            start_pt[1] + dy * random.uniform(0.65, 0.80) + ny * bow_amp * 0.4,
        )
        p3 = target_pt

        lut, total_arc_len = self._build_arc_length_lut(p0, p1, p2, p3, samples=32)

        # Dual harmonic tremor frequencies
        f1 = random.uniform(8.8, 10.2)
        f2 = random.uniform(10.8, 12.4)
        phi1 = random.uniform(0, 2 * math.pi)
        phi2 = random.uniform(0, 2 * math.pi)
        amp_tremor = random.uniform(1.2, 2.2)

        trajectory = []
        dt = tau / float(total_frames)

        for frame_idx in range(total_frames + 1):
            t = frame_idx * dt
            norm_t = min(1.0, t / tau)

            # A. Closed-form Beta progress
            s = self._beta_progress(norm_t)

            # B. Arc-length inversion to u
            u = self._lut_arc_to_u(lut, total_arc_len, s)
            bx, by = self._bezier_point(p0, p1, p2, p3, u)

            # C. Envelope: Zero at t=0 and t=tau
            envelope = math.pow(4.0 * norm_t * (1.0 - norm_t), 1.2) if (0.0 < norm_t < 1.0) else 0.0

            # D. Dual-Harmonic Tremor
            tremor_x = amp_tremor * (
                math.sin(2.0 * math.pi * f1 * t + phi1) +
                0.35 * math.sin(2.0 * math.pi * f2 * t + phi2)
            ) * envelope

            tremor_y = amp_tremor * (
                math.cos(2.0 * math.pi * f1 * t + phi1 + math.pi * 0.25) +
                0.35 * math.cos(2.0 * math.pi * f2 * t + phi2)
            ) * envelope

            final_x = bx + tremor_x
            final_y = by + tremor_y

            v = 0.0
            if trajectory:
                step_d = math.hypot(final_x - trajectory[-1].x, final_y - trajectory[-1].y)
                v = step_d / dt

            trajectory.append(TrajectoryPoint(x=final_x, y=final_y, timestamp_s=t, velocity_px_s=v))

        # Absolute guarantee: endpoint is exact target pixel
        trajectory[-1].x = target_pt[0]
        trajectory[-1].y = target_pt[1]
        trajectory[-1].velocity_px_s = 0.0
        return trajectory

    def generate_mach_path(
        self,
        start_pt: tuple[float, float],
        target_pt: tuple[float, float],
        duration_ms: float = 40.0,
        framerate: float = 120.0
    ) -> list[TrajectoryPoint]:
        """Generates near-instant warp vector (30-50ms) with motion blur samples."""
        dx = target_pt[0] - start_pt[0]
        dy = target_pt[1] - start_pt[1]
        dist = math.hypot(dx, dy)

        tau = duration_ms / 1000.0
        total_frames = max(4, int(math.ceil(tau * framerate)))
        dt = tau / float(total_frames)

        trajectory = []
        for i in range(total_frames + 1):
            norm_t = i / float(total_frames)
            # Quadratic ease-out warp
            s = 1.0 - (1.0 - norm_t) ** 2
            x = start_pt[0] + dx * s
            y = start_pt[1] + dy * s
            v = dist / tau
            trajectory.append(TrajectoryPoint(x=x, y=y, timestamp_s=i * dt, velocity_px_s=v))

        trajectory[-1].x = target_pt[0]
        trajectory[-1].y = target_pt[1]
        return trajectory

    def glide_cursor(
        self,
        start_pt: tuple[float, float],
        target_pt: tuple[float, float],
        mode: str = "mach",
        target_width_px: float = 32.0,
        telemetry_cb: Optional[Callable[[float, float], None]] = None
    ) -> bool:
        """
        Executes physical mouse movement while dispatching coordinates to overlay telemetry.
        Returns True on success, False if aborted by Esc panic key.
        """
        FAILSAFE.notify_ai_pos(start_pt[0], start_pt[1])

        if mode == "mach":
            path = self.generate_mach_path(start_pt, target_pt)
        else:
            path = self.generate_biomimetic_path(start_pt, target_pt, target_width_px=target_width_px)

        for i, pt in enumerate(path):
            if FAILSAFE.is_aborted():
                FAILSAFE.notify_ai_finished()
                return False

            fast_mouse_move_abs(pt.x, pt.y)
            FAILSAFE.notify_ai_pos(pt.x, pt.y)

            if telemetry_cb:
                telemetry_cb(pt.x, pt.y)

            # Delay to next point
            if i < len(path) - 1:
                step_dt = path[i + 1].timestamp_s - pt.timestamp_s
                if step_dt > 0:
                    time.sleep(step_dt)

        FAILSAFE.notify_ai_finished()
        return True

# Global motion engine singleton
MOTION = MotionEngine()
