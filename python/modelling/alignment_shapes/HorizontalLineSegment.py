#  31.01.2023 ----------------------------------------------------------------------------------------------------------------------
#  created by: Felix Eickeler
#              felix.eickeler@tum.de
# ----------------------------------------------------------------------------------------------------------------------------------

import numpy as np

class HorizontalLineSegment:

    @staticmethod
    def from_ifc(obj):
        _param = {
            "segment_length": obj.SegmentLength,
            "initial_direction": obj.StartDirection,
            "start_point": np.array(obj.StartPoint.Coordinates)
        }
        return HorizontalLineSegment(**_param)

    def __init__(self, segment_length, initial_direction, start_point: np.array):
        self.segment_length = segment_length
        self.initial_direction = initial_direction
        self.start_point = start_point
        #self.opening_angle = self.arc_length / self.radius

    def sample(self, linspace=1, is_end=False):
        distances = np.arange(0, self.segment_length, linspace)
        if is_end:
            distances = np.append(distances, self.segment_length)
            
        m = np.array([
            np.cos(self.initial_direction),
            np.sin(self.initial_direction)
            ])

        samples = np.outer(m, distances)
        samples += self.start_point[:, None]

        #* distances
      
        return distances, samples

    def plot(self, _plt, linspace=1, is_end=False, color="dodgerblue"):
        _, points = self.sample(linspace, is_end)
        _plt.plot(points[0], points[1], lw=3, color=color)
        _plt.plot(points[0, 0], points[1, 0], "o")
        if is_end:
            _plt.plot(points[0, -1], points[1, -1], "o")

        # _plt.plot(self.center[0], self.center[1], "xr")


if __name__ == "__main__":
    from matplotlib import pyplot as plt

    obj = type('IfcLineSegment2D', (object,), {})()
    #obj.Radius = 7
    obj.SegmentLength = 16
    obj.StartDirection = 1/4* np.pi
    obj.StartPoint = type('IfcCartesianPoint', (object,), {})()
    obj.StartPoint.Coordinates = [0, 0]

    ca = HorizontalLineSegement.from_ifc(obj)
    plt.xlabel('x (m)')
    plt.ylabel('y (m)')
    plt.title('An awesome Line !')
    plt.rc('grid', linestyle="-", color='black')
    plt.grid(True)
    ca.plot(plt, is_end=True)
    plt.gca().set_aspect('equal', adjustable='box')
    #plt.show()
    plt.savefig("testline.svg")
