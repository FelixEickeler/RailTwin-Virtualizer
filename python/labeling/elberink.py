# 05.04.22----------------------------------------------------------------------------------------------------------------------
#  created by: Felix Eickeler & Alicia Knauer
#              felix.eickeler@tum.de       
# -----------------------------------------------------------------------------------------------------------------------------
#
#
import pandas
import numpy as np

from python.common.shared.algorithms.quadindex import QuadIndex
# I herby question 6.5m
from python.common.shared.utils.plot.plot3d import plot3d


class ElberinkDtmDefinitions:
    definitions = ["To_Be_Processed",
                   "Terrain",
                   "Rail",
                   "Space",
                   "TopSpace",
                   "Catenary",
                   "Contact_Wire",
                   "Messenger_Wire",
                   "Above"]

    # gtsc are the first 4 initial groups
    @classmethod
    def gtsc_defintions(cls, dtm_height):
        # above given is a bin
        # ground_span = -1e32
        terrain_span = dtm_height + 0.5
        space_span = dtm_height + 4.5  # but what inbetween 4.5 and 5.5 ? TopSpace !
        topspace_span = dtm_height + 5.5
        catenary_span = dtm_height + 8
        above = 1e32

        gtsc_bins = [terrain_span, space_span, topspace_span, catenary_span, above]
        gtsc_labels = np.array([cls.Terrain, cls.Space, cls.TopSpace, cls.Catenary, cls.Above])
        return gtsc_bins, gtsc_labels


for i, d in enumerate(ElberinkDtmDefinitions.definitions):
    setattr(ElberinkDtmDefinitions, d, i)

EDD = ElberinkDtmDefinitions


def dtm_analysis(point_cloud: pandas.DataFrame, inplace=False, debug=False):
    if not inplace:
        point_cloud = point_cloud.copy()

    # initialize new data fields
    point_cloud["DTMAnalysis"] = 0
    qi = QuadIndex.create_quadindex(point_cloud, distance=1, debug=debug)

    # color_index = 0
    # point_cloud["colors"] = 0
    # colors = np.arange(0, qi.cells)
    # np.random.shuffle(colors)

    # This is not ok, but warning thrown now is wrong. Remove if problems occur:
    pandas.options.mode.chained_assignment = None
    point_cloud["above_ground"] = 0
    for begin, end, idx_slice in qi:
        if (idx_slice.stop - idx_slice.start) == 0: continue
        point_cloud.iloc[idx_slice], dtm_height = DTMAnalysis.analyze_cell(point_cloud.iloc[idx_slice])
        point_cloud.loc[idx_slice, "above_ground"] = point_cloud.loc[idx_slice, "z"] - dtm_height
        # point_cloud["colors"][slice] = colors[color_index]
        # color_index += 1#
    pandas.options.mode.chained_assignment = 'warn'
    return point_cloud


class DTMAnalysis:
    def __init__(self, dtm_height, index, points):  # <= add the needed parameters
        # TODO write all the things you can find out from the given "1x1 cell"
        self.dtm_height = dtm_height
        self.index = index
        self.points = points

    # analyzing all points of one cell
    @staticmethod
    def analyze_cell(points_in_area):
        if len(points_in_area) == 0:
            return points_in_area, 0
        # -------------------------------------------------------------------- From Paper: Starting point is the determination of DTM height per grid cell.
        # As an initial guess the 10%-ile height of all points within the grid cell. If there are less than 10 % of the points within 0.5 and 4.5 m above DTM
        # height, there may be rail and or wire points. For roughly detecting points on wires the assumption is that points on wires are between 5.5 and 6.5
        # m above terrain level, only the lowest 5 cm of those points are taken as potential contact wire points.

        # All points within 0.5 meter above DTM height (called “the terrain points”) are further analyzed for rail point detection, see figure 2. If the
        # difference between the 98%-ile height of the terrain points and the 10%-ile point is larger than 10 cm, there may be a rail track inside the grid
        # cell. All points within 10 cm of the 98%-ile point are potentially rail track points, but only if this is not the majority within the grid cell,
        # see figure 2. --------------------------------------------------------------------

        # This will move everything to 0->n, later needs to be shifted back i guess ?
        points_in_area.sort_values(by='z', inplace=True, ignore_index=True)
        # points_in_area = points_in_area.copy()  # just to supress warnings
        val = points_in_area.shape[0]

        # 1. Get DTM height
        # Elberink: As an initial guess the 10%-ile height of all points within the grid cell.
        dtm_point = np.floor(val / 10)
        dtm_height = points_in_area["z"][dtm_point]

        # return points_in_area.to_numpy(), dtm_height

        # 2. Split by height above dtm height
        # Elberink: Uses initial 4 classes.
        # In paper ground is not named but implicitly given so everything below 0.5 is terrain, also span between cateneray and space is not named
        # Here they are now called gorund, and tops pace.
        # We use gtsc as naming for the 4+2 definitions.
        gtsc_bins, gtsc_labels = ElberinkDtmDefinitions.gtsc_defintions(dtm_height)  #
        # points_in_area["DTMAnalysis"] = pandas.cut(points_in_area["z"], bins=gtsc_bins, labels=gtsc_labels,
        #                                            include_lowest=True,
        #                                            right=True)
        things = np.digitize(points_in_area["z"], bins=gtsc_bins)
        points_in_area["DTMAnalysis"] = gtsc_labels[things]

        # 3. Extract wire points from catenary points e.g. refinement
        catenary_points = points_in_area[points_in_area["DTMAnalysis"] == ElberinkDtmDefinitions.Catenary]
        if len(catenary_points) > 0:
            wire_catenary_split = np.min(catenary_points["z"]) + 0.05
            messenger_catenary_split = np.max(catenary_points["z"]) - 0.05

            points_in_area.loc[(points_in_area["DTMAnalysis"] == ElberinkDtmDefinitions.Catenary) & (
                    points_in_area["z"] < wire_catenary_split), "DTMAnalysis"] = ElberinkDtmDefinitions.Contact_Wire
            points_in_area.loc[(points_in_area["DTMAnalysis"] == ElberinkDtmDefinitions.Catenary) & (
                    points_in_area["z"] > messenger_catenary_split), "DTMAnalysis"] = ElberinkDtmDefinitions.Messenger_Wire

        # 4. Railpoints
        ile_98 = int(np.floor(len(points_in_area[points_in_area["DTMAnalysis"] == ElberinkDtmDefinitions.Terrain]) * 0.99))
        rail_shoulder_height = points_in_area[points_in_area["DTMAnalysis"] == ElberinkDtmDefinitions.Terrain].iloc[ile_98]["z"]
        rail_root_height = rail_shoulder_height - 0.1
        if rail_root_height > dtm_height:
            rail_points = points_in_area.loc[(points_in_area["DTMAnalysis"] == ElberinkDtmDefinitions.Terrain) &
                                             (points_in_area["z"] >= rail_root_height) & (points_in_area["z"] <= rail_shoulder_height)]
            if (len(rail_points) / len(points_in_area)) < 0.5:
                points_in_area.loc[(points_in_area["DTMAnalysis"] == ElberinkDtmDefinitions.Terrain) &
                                   (points_in_area["z"] >= rail_root_height) & (
                                           points_in_area["z"] <= rail_shoulder_height), "DTMAnalysis"] = ElberinkDtmDefinitions.Rail

        # 5. do we have something for crossings ?

        # move again to correct index
        # points_in_area.set_index(points_in_area.index + index_saver)
        return points_in_area, dtm_height
