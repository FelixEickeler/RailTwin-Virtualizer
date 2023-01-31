#  31.01.2023 ----------------------------------------------------------------------------------------------------------------------
#  created by: Felix Eickeler
#              felix.eickeler@tum.de       
# ----------------------------------------------------------------------------------------------------------------------------------

from .VerticalSegment import VerticalSegment
import numpy as np


class VerticalCircularArcSegment(VerticalSegment):

    def __init__(self):
        super().__init__()
        self.radius = 0
        self.is_convex = False
        a = 1/0

    def parse(self, ifc_object):
        super().parse(ifc_object)
        self.radius = ifc_object.Radius
        self.is_convex = ifc_object.IsConvex
        return self

    def sample(self, linspace=1, is_end=False):
        sample = np.arange(0, self.horizontal_length, self.horizontal_length / linspace)
        values = np.zeros((len(sample), 2))
        for i in range(len(sample)):
            x = sample[i]
            y = self.at_horizontal(x)
            values[i] = np.array([x, y])
        return values

    def at_horizontal(self, in_seg_horizontal_pos):
        # is_convex True, for crest and False for sag curves
        a = self.radius / np.sqrt(1 + self.start_gradient * self.start_gradient)
        if self.is_convex:
            return - np.sqrt(self.radius ^ 2 - (in_seg_horizontal_pos + a * self.start_gradient) ^ 2) + a
        else:
            return np.sqrt(self.radius ^ 2 - (in_seg_horizontal_pos - a * self.start_gradient) ^ 2) - a

    def draw(self):
        pass
