#  31.01.2023 ----------------------------------------------------------------------------------------------------------------------
#  created by: Felix Eickeler
#              felix.eickeler@tum.de
# ----------------------------------------------------------------------------------------------------------------------------------

import numpy as np
from numpy import cos, sin
from scipy.integrate import odeint


def clothoid_ode_rhs(state, s, kappa0, kappa1):
    x, y, theta = state[0], state[1], state[2]
    return np.array([np.cos(theta), np.sin(theta), kappa0 + kappa1 * s])


def eval_clothoid(x0, y0, theta0, kappa0, kappa1, s):
    return odeint(clothoid_ode_rhs, np.array([x0, y0, theta0]), s, (kappa0, kappa1))


def parametric_circle(t, xc, yc, R):
    x = xc + R * cos(t)
    y = yc + R * sin(t)
    return x, y


class CircularArc:
    @staticmethod
    def from_ifc(obj):
        _param = {
            "radius": obj.Radius,
            "is_ccw": obj.IsCCW,
            "arc_length": obj.SegmentLength,
            "initial_direction": obj.StartDirection,
            "start_point": np.array(obj.StartPoint.Coordinates)
        }
        return CircularArc(**_param)

    def __init__(self, radius, is_ccw, arc_length, initial_direction, start_point: np.array):
        self.radius = radius
        self.arc_length = arc_length
        self.segment_length = arc_length
        self.initial_direction = initial_direction
        self.is_ccw = is_ccw
        self.start_point = start_point
        self.opening_angle = self.arc_length / self.radius

    @property
    def center(self):
        rvec = np.array([cos(self.initial_direction - np.pi / 2) * self.radius,
                         sin(self.initial_direction - np.pi / 2) * self.radius])
        # rvec must be on the other side ?
        if self.is_ccw:
            return self.start_point - rvec
        return self.start_point + rvec

    @property
    def start_angle(self):
        if self.is_ccw:
            return self.initial_direction - np.pi / 2
        return self.initial_direction + np.pi / 2

    @property
    def end_angle(self):
        start = self.start_angle
        if self.is_ccw:
            return start + self.opening_angle
        return start - self.opening_angle

    def sample(self, linspace=1, is_end=False):
        delta_angle = linspace / self.radius
        if self.start_angle > self.end_angle:
            start = self.end_angle
            end = self.start_angle
            _reverse = True
            if is_end:
                end -= delta_angle
        else:
            start = self.start_angle
            end = self.end_angle
            _reverse = False
            if is_end:
                end += delta_angle

        samples = np.arange(start, end, delta_angle)
        center = self.center
        distances = np.zeros_like(samples)
        for i in range(len(samples)):
            distances[i] = (samples[i]-start) * self.radius
        return np.flipud(distances) if _reverse else distances, np.array(parametric_circle(samples, center[0], center[1], self.radius))

    def plot(self, _plt, linspace=1, is_end=False, color="dodgerblue"):
        _, points = self.sample(linspace, is_end)
        _plt.plot(points[0], points[1], lw=3, color=color)
        _plt.plot(points[0, 0], points[1, 0], "o")
        if is_end:
            _plt.plot(points[0, -1], points[1, -1], "o")

        # _plt.plot(self.center[0], self.center[1], "xr")


if __name__ == "__main__":
    from matplotlib import pyplot as plt

    obj = type('IfcCircularArcSegment2D', (object,), {})()
    obj.Radius = 7
    obj.SegmentLength = 16
    obj.StartDirection = 0
    obj.StartPoint = type('IfcCartesianPoint', (object,), {})()
    obj.StartPoint.Coordinates = [0, 0]

    ca = CircularArc(obj)
    plt.xlabel('x (m)')
    plt.ylabel('y (m)')
    plt.title('An awesome Circle !')
    plt.rc('grid', linestyle="-", color='black')
    plt.grid(True)
    ca.plot(plt, is_end=True)
    plt.gca().set_aspect('equal', adjustable='box')
    plt.show()
