# 21.07.22----------------------------------------------------------------------------------------------------------------------
#  created by: Felix Eickeler 
#              felix.eickeler@tum.de       
# ----------------------------------------------------------------------------------------------------------------
#
#
import json

import numpy as np
from python.modelling.alignment_shapes.CircularArcSegment import CircularArc
from python.modelling.alignment_shapes.HorizontalLineSegment import HorizontalLineSegment
from python.modelling.alignment_shapes.TransitionCurveSegment import TransitionCurveSegment
from python.modelling.alignment_shapes.VerticalCircularArcSegment import VerticalCircularArcSegment
from python.modelling.alignment_shapes.VerticalLineSegment import VerticalLineSegment
from python.modelling.alignment_shapes.VerticalParabolicArcSegment import VerticalParabolicArcSegment
from python.modelling.alignment_shapes.VerticalSegment import VerticalSegment


class AlignmentEncoder(json.JSONEncoder):
    def default(self, o):
        # if isinstance(o, CircularArc):
        #     return o.__dict__
        # elif isinstance(o, HorizontalLineSegment):
        #     return o.__dict__
        # elif isinstance(o, TransitionCurveSegment):
        #     return o.__dict__
        # elif isinstance(o, VerticalCircularArcSegment):
        #     return o.__dict__
        # elif isinstance(o, VerticalLineSegment):
        #     return o.__dict__
        # elif isinstance(o, VerticalParabolicArcSegment):
        #     return o.__dict__
        # elif isinstance(o, VerticalSegment):
        #     return o.__dict__
        if type(o) in [CircularArc, HorizontalLineSegment, TransitionCurveSegment,
                       VerticalCircularArcSegment, VerticalLineSegment, VerticalParabolicArcSegment,
                       VerticalSegment]:
            data = o.__dict__.copy()
            data["type"] = str(type(o).__name__)
            return data
        elif isinstance(o, np.ndarray):
            return o.tolist()

        return json.JSONEncoder.default(self, o)
