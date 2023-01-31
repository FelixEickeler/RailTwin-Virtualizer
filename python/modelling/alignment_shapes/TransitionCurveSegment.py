#  31.01.2023 ----------------------------------------------------------------------------------------------------------------------
#  created by: Felix Eickeler
#              felix.eickeler@tum.de       
# ----------------------------------------------------------------------------------------------------------------------------------

import numpy as np
from numpy import cos, sin, arccos
from scipy.integrate import odeint
from pyclothoids import Clothoid


def clothoid_ode_rhs(state, s, kappa0, kappa1):
    x, y, theta = state[0], state[1], state[2]
    return np.array([np.cos(theta), np.sin(theta), kappa0 + kappa1 * s])


def eval_clothoid(x0, y0, theta0, kappa0, kappa1, s):
    return odeint(clothoid_ode_rhs, np.array([x0, y0, theta0]), s, (kappa0, kappa1))


def parametric_circle(t, xc, yc, R):
    x = xc + R * cos(t)
    y = yc + R * sin(t)
    return x, y


class TransitionCurveSegment:
    @staticmethod
    def from_ifc(ifc_object):
        _param = {
            "segment_length": ifc_object.SegmentLength,
            "initial_direction": ifc_object.StartDirection,
            "start_point": np.array(ifc_object.StartPoint.Coordinates),
            "start_radius": ifc_object.StartRadius,
            "start_radius_ccw": ifc_object.IsStartRadiusCCW,
            "end_radius": ifc_object.EndRadius,
            "end_radius_ccw": ifc_object.IsEndRadiusCCW,
            "curve_type": ifc_object.TransitionCurveType
        }
        return TransitionCurveSegment(**_param)

    def __init__(self, segment_length, initial_direction, start_point, start_radius, start_radius_ccw,
                 end_radius, end_radius_ccw, curve_type):
        self.segment_length = segment_length
        self.initial_direction = initial_direction
        self.start_point = start_point

        self.start_radius = start_radius
        self.start_radius_ccw = start_radius_ccw
        self.end_radius = end_radius
        self.end_radius_ccw = end_radius_ccw
        self.curve_type = curve_type

    def sample(self, linspace=1, is_end=True):
        samples = np.arange(0, self.segment_length, linspace)
        if is_end:
            samples = np.append(samples, self.segment_length)

        if self.curve_type == "CLOTHOIDCURVE":
            k0 = 0 if self.start_radius == 0 else 1 / self.start_radius
            k1 = 0 if self.end_radius == 0 else 1 / self.end_radius
            if not self.start_radius_ccw:
                k0 *= -1
            if not self.end_radius_ccw:
                k1 *= -1

            kd = (k1 - k0) / self.segment_length

            clothoid = Clothoid.StandardParams(self.start_point[0], self.start_point[1], self.initial_direction,
                                               k0, kd, self.segment_length)

            cx = [clothoid.X(i) for i in samples]
            cy = [clothoid.Y(i) for i in samples]
            return samples, np.array([cx, cy])

    def plot(self, _plt, linspace=1, is_end=False, color="purple"):
        _, points = self.sample(linspace, is_end)
        _plt.plot(points[0], points[1], lw=3, color=color)
        _plt.plot(points[0, 0], points[1, 1], "o")
        if is_end:
            _plt.plot(points[0, -1], points[1, -1], "o")


if __name__ == "__main__":
    from matplotlib import pyplot as plt

    obj = type('IfcTransitionCurveSegment', (object,), {})()
    obj.EndRadius = 10
    obj.IsEndRadiusCCW = False
    obj.StartRadius = 0
    obj.IsStartRadiusCCW = False
    obj.SegmentLength = 10
    obj.StartDirection = 0
    obj.StartPoint = type('IfcCartesianPoint', (object,), {})()
    obj.StartPoint.Coordinates = [0, 0]
    obj.TransitionCurveType = "CLOTHOIDCURVE"

    ca = TransitionCurveSegment.from_ifc(obj)
    plt.xlabel('x (m)')
    plt.ylabel('y (m)')
    plt.title('An awesome Circle !')
    plt.rc('grid', linestyle="-", color='black')
    plt.grid(True)
    ca.plot(plt, is_end=True)
    plt.gca().set_aspect('equal', adjustable='box')
    plt.show()
