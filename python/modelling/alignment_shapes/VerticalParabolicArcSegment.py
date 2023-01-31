#  31.01.2023 ----------------------------------------------------------------------------------------------------------------------
#  created by: Felix Eickeler
#              felix.eickeler@tum.de       
# ----------------------------------------------------------------------------------------------------------------------------------

from .VerticalSegment import VerticalSegment
import numpy as np


class VerticalParabolicArcSegment(VerticalSegment):

    def __init__(self):
        super().__init__()
        self.parabola_constant = 0.0
        self.is_convex = False

    def parse(self, ifc_object):
        super().parse(ifc_object)
        self.is_convex = ifc_object.IsConvex
        self.parabola_constant = ifc_object.ParabolaConstant

    def sample(self, linspace=1, is_end=False):
        # warning this is not correct ! but it would need to be solved numerically
        sample = np.arange(0, self.horizontal_length, self.horizontal_length / linspace)
        values = np.zeros((len(sample), 2))
        for i in range(len(sample)):
            x = sample[i]
            y = self.at_horizontal(x)
            values[i] = np.array([x, y])
        return values

    def at_horizontal(self, in_seg_horizontal_pos):
        R = -1 * self.parabola_constant if self.is_convex else self.parabola_constant
        gradient = in_seg_horizontal_pos / R + self.start_gradient
        return in_seg_horizontal_pos * (gradient + self.start_gradient)/2 + self.start_height

    def draw(self):
        pass
