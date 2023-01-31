# 14.06.22----------------------------------------------------------------------------------------------------------------------
#  created by: Felix Eickeler 
#              felix.eickeler@tum.de       
# ----------------------------------------------------------------------------------------------------------------
#
#
import itertools
from pathlib import Path
import pandas

from python.evaluation.base_evaluation import BaseEvaluation
import matplotlib.pyplot as plt
import numpy as np


# def plotly_confusion_matrix(cm, labels):
#     z = cm
#     z = z[::-1]
#     x = labels
#     y = x[::-1].copy()  # invert idx values of x
#
#     z_text = [[str(y) for y in x] for x in z]
#
#     # set up figure
#     fig = ff.create_annotated_heatmap(z, x=x, y=y, annotation_text=z_text, colorscale='Viridis')
#
#     # add title
#     fig.update_layout(title_text='<i><b>Confusion matrix</b></i>',
#                       # xaxis = dict(title='x'),
#                       # yaxis = dict(title='x')
#                       )
#
#     # add custom xaxis title
#     fig.add_annotation(dict(font=dict(color="black", size=14),
#                             x=0.5,
#                             y=-0.15,
#                             showarrow=False,
#                             text="Predicted value",
#                             xref="paper",
#                             yref="paper"))
#
#     # add custom yaxis title
#     fig.add_annotation(dict(font=dict(color="black", size=14),
#                             x=-0.35,
#                             y=0.5,
#                             showarrow=False,
#                             text="Real value",
#                             textangle=-90,
#                             xref="paper",
#                             yref="paper"))
#
#     # adjust margins to make room for yaxis title
#     fig.update_layout(margin=dict(t=50, l=200))
#
#     # add colorbar
#     fig['data'][0]['showscale'] = True
#     fig.show()


def matplotlib_confusion_matrix(cm, class_names):
    """
  Returns a matplotlib figure containing the plotted confusion matrix.

  Args:
    cm (array, shape = [n, n]): a confusion matrix of integer classes
    class_names (array, shape = [n]): String names of the integer classes
  """
    figure = plt.figure(figsize=(18, 18))
    plt.imshow(cm, interpolation='nearest', cmap=plt.cm.Greens)
    plt.title("Confusion matrix")
    plt.colorbar()
    tick_marks = np.arange(len(class_names))
    plt.xticks(tick_marks, class_names, rotation=45)
    plt.yticks(tick_marks, class_names)

    # Compute the labels from the normalized confusion matrix.
    labels = np.around(cm.astype('float') / (cm.sum(axis=-1) + 1e-6)[:, np.newaxis], decimals=2)
    # labels = cm.astype('float')

    # Use white text if squares are dark; otherwise black.
    threshold = cm.max() / 2.
    for i, j in itertools.product(range(cm.shape[0]), range(cm.shape[1])):
        color = "white" if cm[i, j] > threshold else "black"
        plt.text(j, i, labels[i, j], horizontalalignment="center", color=color)

    plt.tight_layout(pad=1.15)
    plt.ylabel('True label')
    plt.xlabel('Predicted label')
    return figure


def get_overview(confusions, labels):
    # IoUs = IoU_from_confusions(C)
    TP_plus_FN = np.sum(confusions, axis=-1)
    TP_plus_FP = np.sum(confusions, axis=-2)
    TP = np.diagonal(confusions, axis1=-2, axis2=-1)
    FN = TP_plus_FP - TP
    FP = TP_plus_FN - TP
    TN = TP + confusions.sum() - TP_plus_FP - TP_plus_FN

    recall = TP / TP_plus_FN
    selectivity = TN / (TN + FP)
    balanced_acc = (recall + selectivity) / 2
    precision = TP / TP_plus_FP
    npv = TN / (TN + FN)
    err_rate = FP + FN / (TP + FN + FN)

    mask = TP_plus_FN < 1e-3
    IoU = TP / (TP + FP + FN + 1e-6)
    counts = np.sum(1 - mask, axis=-1, keepdims=True)
    mIoU = np.sum(IoU, axis=-1, keepdims=True) / (counts + 1e-6)
    prelabel = [f"#{i+1}" for i in range(len(labels))]
    summary = pandas.DataFrame({
                            # "index" : prelabel,
                            "category": labels,
                            "precision": precision,
                            "recall": recall,
                            # "selectivity": selectivity,
                            "IoU": IoU,
                            # "balanced_acc": balanced_acc,"balanced_acc",
                            # "npv": npv, #  "npv"
                            # "err_rate": err_rate, "err_rate"
                            "labels[%]": TP_plus_FN / TP_plus_FN.sum(),
                            "labels": TP_plus_FN,
                            "predicted": TP_plus_FP,
                            "correct": TP
                            },
                           columns=["category", "precision", "recall", "IoU", "labels[%]", "labels", "predicted", "correct"])

    # if config save stuff
    # figure = plt.figure(figsize=(8, 8))
    fig, ax = plt.subplots()
    fig.set_figheight(len(labels) / 2)
    fig.set_figwidth(16)
    fig.set_dpi(200)
    fig.patch.set_visible(False)
    ax.axis('off')
    ax.axis('tight')
    summary.update(summary[["IoU", "precision", "recall", "labels[%]"]].applymap('{:,.2f}'.format, na_action="ignore"))
    thmap = lambda t: "$" + format(int(t), ',d').replace(',', '\,') + "$"
    summary.update(summary[["predicted", "correct", "labels"]].applymap(thmap, na_action="ignore"))
    rcolors = np.full(len(summary.category), "#CCD9C7")
    ccolors = np.full(len(summary.columns), "#CCD9C7")
    tab = ax.table(cellText=summary.values[:, summary.columns != 'category'],
                   rowLabels=summary["category"], rowColours=rcolors,
                   colLabels=summary.columns[summary.columns != 'category'], colColours=ccolors, loc='center')
    tab.auto_set_font_size(False)
    tab.auto_set_column_width(col=list(range(len(summary.columns))))
    tab.scale(1, 1.3)

    iou_col = np.argmax(summary.columns == "IoU")
    for i in range(1, len(summary["IoU"]) + 1):
        the_cell = tab[i, iou_col - 1]
        the_cell.set_facecolor("#AD688E")
    fig.tight_layout()
    return fig


class CloudSegmentationEvaluation(BaseEvaluation):

    def __int__(self):
        pass

    def eval(self, pc: pandas.DataFrame):
        if hasattr(pc, "preds_system") and hasattr(pc, "system"):
            labels = [""] * len(pc.metadata["system_labels"])
            for lab, i in pc.metadata["system_labels"].items():
                labels[i] = lab

            confusion_matrix = pandas.crosstab( pc['system'], pc['preds_system'], dropna=False)  # .sort_index(axis=0).sort_index(axis=1)
            # cm = np.zeros(len(labels)-1,len(labels)-1)
            # for x in range(len(labels)-1):
            #     for y in range(len(labels)-1):
            for c in range(len(labels)):
                if c not in confusion_matrix.columns:
                    confusion_matrix[c] = 0
            confusion_matrix = confusion_matrix.reindex(sorted(confusion_matrix.columns), axis=1)

            # confusion_matrix = confusion_matrix.reindex(range(len(labels)), axis=0, fill_value=0)  # all columns
            # confusion_matrix = confusion_matrix.reindex(list(range(confusion_matrix.index.min(), confusion_matrix.index.max()+1), fill_value=0))  # all rows
            confusion_matrix = confusion_matrix.reindex(list(range(confusion_matrix.index.min(), int(confusion_matrix.index.max() + 1))), fill_value=0)

            # matplotlib_confusion_matrix(confusion_matrix.to_numpy(), labels[1:])
            # plt.show()
            return {"confusion_matrix": confusion_matrix, "labels": labels}
        if hasattr(pc, "component_preds") and hasattr(pc, "components"):
            pass

    def save(self, path: Path):
        pass

    def plot(self, path: Path):
        pass
