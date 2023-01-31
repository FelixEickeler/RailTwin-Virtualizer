#  31.01.2023 ----------------------------------------------------------------------------------------------------------------------
#  created by: Felix Eickeler
#              felix.eickeler@tum.de       
# ----------------------------------------------------------------------------------------------------------------------------------

from .VerticalCircularArcSegment import VerticalCircularArcSegment
from .VerticalLineSegment import VerticalLineSegment
from .VerticalParabolicArcSegment import VerticalParabolicArcSegment
from .HorizontalLineSegment import HorizontalLineSegment
from .CircularArcSegment import *
from .TransitionCurveSegment import TransitionCurveSegment


class Dispatcher:
    m_registered_types = {
        "IfcCircularArcSegment2D": lambda obj: CircularArc.from_ifc(obj),
        "IfcTransitionCurveSegment2D": lambda obj: TransitionCurveSegment.from_ifc(obj),
        "IfcLineSegment2D" : lambda obj: HorizontalLineSegment.from_ifc(obj),
        "IfcAlignment2DVerSegLine": lambda obj: VerticalLineSegment.from_ifc(obj),
        "IfcAlignment2DVerSegParabolicArc":  lambda obj: VerticalParabolicArcSegment.from_ifc(obj),

        "IfcAlignment2DVerSegCircularArc": lambda obj: VerticalCircularArcSegment.from_ifc(obj),
    }

    @classmethod
    def transform(cls, geom):
        ctype = geom.__dict__["type"]
        if ctype == "IfcAlignment2DHorizontalSegment":
            return cls.transform(geom.CurveGeometry)
        if ctype in cls.m_registered_types:
            return cls.m_registered_types[ctype](geom)
        else:
            raise NotImplementedError("{} was not yet implemented !".format(ctype))
