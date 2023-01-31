import json

import pandas

from .aligment_encoder import AlignmentEncoder
from .dispatcher import Dispatcher
import numpy as np
from pathlib import Path
import plotly.express as px
from pandas import DataFrame

class Alignment:
    def __init__(self):
        self.name = ""
        self.horizontal = []
        self.vertical = []
        self.vertical_search = []
        self.cant = []
        self.horizontal_mapping = {}
        self.vertical_mapping = {}

    def parse(self, ifcAlignment4x1):
        if not ifcAlignment4x1.Vertical:
            return False
        self.name = ifcAlignment4x1.Tag
        self.horizontal = [Dispatcher.transform(seg) for seg in ifcAlignment4x1.Horizontal.Segments]
        self.vertical = [Dispatcher.transform(seg) for seg in ifcAlignment4x1.Vertical.Segments]
        self.vertical_search = [vobject.start_distance_horizontal for vobject in self.vertical]
        return True

    def determine_vertical_alignment(self, horz_distance):
        for i in range(len(self.vertical_search)):
            if self.vertical_search[i] > horz_distance:
                return i - 1, horz_distance - self.vertical_search[i - 1], self.vertical[i - 1]
        return i, horz_distance - self.vertical_search[-1], self.vertical[-1]

    def sample(self, linspace=0.1):
        dataframes = []
        distance_until_current_segment = 0
        # self.type_names = {}

        for hs_count, hs in enumerate(self.horizontal):
            [samples, xy] = hs.sample(linspace=linspace, is_end=hs_count == len(self.horizontal) - 1)
            z = np.ones_like(samples) * 101
            vt = np.ones_like(samples)
            vts = []
            samples += distance_until_current_segment
            for mpos, milestone in enumerate(samples):
                [vst_pos, seg_dist, vertical_segment] = self.determine_vertical_alignment(milestone)
                z[mpos] = vertical_segment.at_horizontal(seg_dist)
                vt[mpos] = vst_pos
                vertical_segment_name = type(vertical_segment).__name__
                if vertical_segment_name not in self.vertical_mapping:
                    self.vertical_mapping[vertical_segment_name] = len(self.vertical_mapping)
                vertical_name_id = self.vertical_mapping[vertical_segment_name]
                vts.append(vertical_name_id)

            type_name = type(hs).__name__
            if type_name not in self.horizontal_mapping:
                self.horizontal_mapping[type_name] = len(self.horizontal_mapping)
            tt = self.horizontal_mapping[type_name]

            dataframes.append(DataFrame({"x": xy[0], "y": xy[1], "z": z, "horizontal_distance": samples,
                                         "segment_horizontal": np.ones_like(samples) * hs_count,
                                         "horizontal_type": np.ones_like(samples) * tt,
                                         "segment_vertical": vt, "segment_type": vts}))
            distance_until_current_segment += hs.segment_length

        return pandas.concat(dataframes, ignore_index=True)

    def plot(self, path=Path(""), show=False):
        df = self.sample()
        self.__class__._plot(df, path, show, name=self.name)

    @staticmethod
    def _plot(df : pandas.DataFrame, path, show, name):
        fig = px.line(df, x="x", y="y", color="segment_horizontal", hover_name="horizontal_type",
                      title=f"Horizontal Alignment {name}", line_shape="linear", render_mode="svg",
                      labels=dict(x="x [m]", y="y [m]", horizontal_type="IFC Name"))

        # plot horizontal

        if show:
            fig.show()
        if path:
            hpath = Path(path).parent / "{}_horizontal{}".format(path.stem, path.suffix)
            fig.write_image(hpath)

        # fix holes in vertical plot
        if False:
            df.sort_values(by=["horizontal_distance"], inplace=True)
            vtype_change = df["segment_vertical"].shift() != df["segment_vertical"]
            rows = vtype_change[vtype_change].index.values
            df_addendum = []
            for i in rows:
                if i >= 1:
                    endpoint = df.iloc[i].copy()
                    endpoint["segment_vertical"] = df.iloc[i - 1]["segment_vertical"]
                    df_addendum.append(endpoint)

            df = df.append(df_addendum)
            df.sort_values(by=["horizontal_distance"], ignore_index=True, inplace=True)

        fig = px.line(df, x="horizontal_distance", y="z", color="segment_vertical", hover_name="segment_type",
                      title=f"Vertical Alignment {name}", line_shape="linear", render_mode="svg",
                      labels=dict(horizontal_distance="horizontal distance [m]", z="height [m]",
                                  horizontal_type="IFC Name"))

        # plot vertical
        if show:
            fig.show()
        if path:
            vpath = Path(path).parent / "{}_vertical{}".format(path.stem, path.suffix)
            fig.write_image(vpath)

        # plot 3D
        fig = px.line_3d(df, y="y", x="x", z="z",color="segment_horizontal", title=f"Alignment {name}",
                         labels=dict(x="x [m]", y="y [m]", z="z [m]",  horizontal_type="IFC Name"))
        fig.update_yaxes(scaleanchor="x", scaleratio=1, )
        fig['layout']['scene']['aspectmode'] = "data"
        if show:
            fig.show()
        if path:
            ddd_path = Path(path).parent / "{}_3D{}".format(path.stem, ".html")
            fig.write_html(ddd_path)

    def add_segment_4x1(self, segment):
        axis = segment.Axis
        self.vertical.append(axis.Vertical.Segments if axis.Vertical else [])
        self.horizontal.append(axis.Horizontal.Segments if axis.Horizontal else [])

        # look at segment
        # linspace for line segment 2d

        # circular arc => define midpoint
        # calculate angle
        # place points...

        #  clothoid

    def to_json(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as fp:
            json.dump(self.__dict__, fp, indent=4, sort_keys=True, cls=AlignmentEncoder)


    @staticmethod
    def from_csv(input_path):
        return pandas.read_csv(input_path, usecols=['x', 'y', 'z', 'horizontal_distance', 'segment_horizontal',
                                                'horizontal_type', 'segment_vertical', 'segment_type'],
                               dtype={"x": np.float64,
                                      "y": np.float64,
                                      "z": np.float64,
                                      "horizontal_distance": np.float64,
                                      "segment_horizontal": np.float64,
                                      "horizontal_type": np.float64,
                                      "segment_vertical": np.float64,
                                      "segment_type": str})
