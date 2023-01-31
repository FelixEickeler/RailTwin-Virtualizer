#  31.01.2023 ----------------------------------------------------------------------------------------------------------------------
#  created by: Felix Eickeler
#              felix.eickeler@tum.de       
# ----------------------------------------------------------------------------------------------------------------------------------

from pathlib import Path
import pandas

class Visualize:
    _steps = ["tensorboard_csv"]

    def __init__(self, _project):
        self.project = _project
        self.input_path = self.project.viz_in
        self.output_path = self.project.viz_out
        self.steps = self.project.step

    def run(self):
        if self.steps == "tensorboard_csv":
            if not self.input_path.is_dir():
                raise NotADirectoryError(f"{self.steps} needs directory to merge the fiels")

            collector = {}
            names = []
            for f in self.input_path.glob("**/**/*.csv"):
                group = f.parent.parent
                enitity = f.parent

                if group not in collector:
                    collector[group] = {}
                if enitity not in collector[group]:
                    collector[group][enitity] = []
                collector[group][enitity] += [pandas.read_csv(f)[:-1]]

            TSBOARD_SMOOTHING = 0.3
            data = {}
            for group, entities in collector.items():
                data[group] = {}
                for entity, instances in entities.items():
                    dat = pandas.concat(instances)
                    dat.groupby('Step', group_keys=False).apply(lambda x: x.loc[x["Wall time"].idxmax()])
                    dat.sort_values(inplace=True, ignore_index=True, by="Step")
                    # if dat["Value"].mean() < dat.iloc[0]["Value"]
                    # dat[dat["Value"] < dat.iloc[0]["Value"]] = dat.iloc[0]["Value"]
                    TSBOARD_SMOOTHING = 0.3
                    if group.stem == "test_w5":
                        TSBOARD_SMOOTHING = 0.7
                    data[group][entity] = dat.ewm(alpha=(1 - TSBOARD_SMOOTHING)).mean()

            # #AD688E
            # 'white': '#FFFFFF',
            # 'gray': '#AAA9AD',
            # 'black': '#313639',
            # 'purple': '#AD688E',
            # 'orange': '#D18F77',
            # 'yellow': '#E8E190',
            # 'ltgreen': '#CCD9C7',
            # 'dkgreen': '#96ABA0',
            # 'light_blkue' : '#89b9d4'

            # colors = ['#AD688E', '#D18F77', '#96ABA0', '#89b9d4']
            titles = {
                "train_accuracy": "Train Accuracy",
                "train_loss": "Train Loss",
                "test_w5": "Test w5 IoU",
                "class_iou": "Test Class IoU on 20%"
            }
            order = ["train_accuracy", "train_loss", "test_w5", "class_iou"]

            colors = {
                "16classes_1": "#AD688E",
                "16classes_2": "#D18F77",
                "16classes_3": "#69AD39",
                "contact-wiring": "#FF8801",
                "rail": "#FF5500",
                "noise-barrier": "#6B6B6B",
                "tree": "#D4FF00",
                "dropper": "#AA0000",
            }

            pos = {
                "train_accuracy": 1.0,
                "train_loss": 1.0,
                "test_w5": 0.35,
                "class_iou": 1.0
            }
            ylim = {
                "train_accuracy": 0.0135,
                "train_loss": 0.0195,
                "test_w5": -0.0055,
                "class_iou": 0.0545
            }

            limits = []

            subplot = 0

            from matplotlib import pyplot as plt
            plt.rcParams.update({'font.size': 18})

            fig = plt.figure(figsize=(26, 30))
            for graph, curves in data.items():
                sp = plt.subplot(2, 2, (order.index(graph.name)) + 1)
                # plt.plot(data["Value"], alpha=0.4, color=)
                for curve_name, curve in curves.items():
                    plt.plot(curve["Step"], curve["Value"], color=colors[curve_name.stem], linewidth=5.0)
                plt.title(titles[graph.name], fontsize=34, pad=10)
                plt.yticks(fontsize=24, linespacing=0.1)
                plt.xticks(fontsize=24, linespacing=0.1)
                sp.set_xlim(left=0)
                sp.set_xlim(right=100)
                sp.set_ylim(top=sp.get_ylim()[1] + ylim[graph.name])
                # sp.set_ylim(bottom=0.748)
                plt.grid(alpha=0.3)

                plt.axvspan(0, 9, facecolor='#89b9d4', alpha=0.4)
                plt.axvspan(9, 28, facecolor='#E8E190', alpha=0.4)
                plt.axvspan(28, 49, facecolor='#CCD9C7', alpha=0.4)
                plt.axvspan(49, sp.get_xlim()[1] + 10, facecolor='#96ABA0', alpha=0.4)

                font = {
                    # 'family': 'serif',
                    'color': 'black',
                    'weight': 'bold',
                    'size': 22,
                }

                plt.text(4.57, pos[graph.name], 'softmax', horizontalalignment='center', fontdict=font)
                plt.text(18.0, pos[graph.name], 'head_mlp', horizontalalignment='center', fontdict=font)
                plt.text(38.5, pos[graph.name], 'decoder', horizontalalignment='center', fontdict=font)
                plt.text(75.3, pos[graph.name], 'encoder', horizontalalignment='center', fontdict=font)
                plt.tight_layout(pad=1.59, w_pad=0.4, h_pad=4.8)
                subplot += 1

                extent = sp.get_window_extent().transformed(fig.dpi_scale_trans.inverted())
                fig.savefig(graph / "plot2.pdf", bbox_inches=extent.expanded(1.075, 1.075))

            import matplotlib.patches as mpatches
            red_patch = mpatches.Patch(color='#AD688E', label='16 systems, 20%')
            blue_patch = mpatches.Patch(color='#D18F77', label='16 systems, 40%')
            green_patch = mpatches.Patch(color='#69AD39', label='16 systems, 60%')
            legend1 = plt.legend(handles=[red_patch, blue_patch, green_patch], bbox_to_anchor=(-0.0795, 0.215), loc=1, borderaxespad=0.,
                                 fontsize=28, handleheight=0.9, handlelength=1.6)

            # "contact-wiring": "#FF8801",
            # "rail": "#FF5500",
            # "noise-barrier": "#6B6B6B",
            # "tree": "#D4FF00",
            # "dropper": "#AA0000",

            p1 = mpatches.Patch(color='#FF5500', label='rail')
            p2 = mpatches.Patch(color='#D4FF00', label='tree')
            p3 = mpatches.Patch(color='#6B6B6B', label='noise-barrier')
            p4 = mpatches.Patch(color='#FF8801', label='contact-wiring')
            p5 = mpatches.Patch(color='#AA0000', label='dropper')
            plt.legend(handles=[p3, p2, p1, p4, p5], bbox_to_anchor=(0.752, -0.803), loc=2, borderaxespad=0.,
                       fontsize=28, handleheight=0.9, handlelength=1.6)
            plt.gca().add_artist(legend1)
            plt.show()

    @staticmethod
    def add_parser_options(subparser):
        pmo_parser = subparser.add_parser("visualize")
        pmo_parser.add_argument('--in', dest="viz_in", type=Path, help="IFC file or folder containing multiple ifc files")
        pmo_parser.add_argument('--out', dest="viz_out", type=Path, help="Output path for the obj, mtl and alignment file")
        pmo_parser.add_argument('--step', choices=Visualize._steps, help=f'[{",".join(Visualize._steps)}]',
                                required=False, dest="secondary")
