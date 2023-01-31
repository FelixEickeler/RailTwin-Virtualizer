#  31.01.2023 ----------------------------------------------------------------------------------------------------------------------
#  created by: Felix Eickeler
#              felix.eickeler@tum.de       
# ----------------------------------------------------------------------------------------------------------------------------------

from abc import abstractmethod, ABC
import numpy as np


class VerticalSegment(ABC):

    def __init__(self):
        self.start_distance_horizontal = 0
        # self.segment_length = 0
        self.horizontal_length = 0
        self.start_height = 0
        self.start_gradient = 0

    @abstractmethod
    def parse(self, ifc_object):
        self.start_distance_horizontal = ifc_object.StartDistAlong
        self.horizontal_length = ifc_object.HorizontalLength
        self.start_height = ifc_object.StartHeight
        self.start_gradient = ifc_object.StartGradient

    @classmethod
    def from_ifc(cls, ifc_object):
        vs = cls()
        vs.parse(ifc_object)
        return vs

    @property
    def m_angle(self):
        return np.arctan2(self.start_gradient, 1)

    @abstractmethod
    def sample(self, linspace=1, is_end=False):
        pass

    @abstractmethod
    def at_horizontal(self, horizonal_pos):
        pass

    @abstractmethod
    def draw(self):
        pass
