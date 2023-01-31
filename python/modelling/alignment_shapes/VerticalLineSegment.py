#  31.01.2023 ----------------------------------------------------------------------------------------------------------------------
#  created by: Felix Eickeler
#              felix.eickeler@tum.de       
# ----------------------------------------------------------------------------------------------------------------------------------

from .VerticalSegment import VerticalSegment
import numpy as np


class VerticalLineSegment(VerticalSegment):

    def __init__(self):
        super().__init__()

    def parse(self, ifc_object):
        super().parse(ifc_object)

    def sample(self, linspace=1, is_end=False):
        sample = np.arange(0, self.horizontal_length, self.horizontal_length / linspace)
        m_cos = np.cos(self.m_angle)
        values = np.zeros((len(sample), 2))
        for i in range(len(sample)):
            x = sample[i] * m_cos
            y = self.at_horizontal(x)
            values[i] = np.array([x, y])
        return values

    def at_horizontal(self, horizonal_pos):
        return self.m_angle * horizonal_pos + self.start_height

    def draw(self):
        pass
