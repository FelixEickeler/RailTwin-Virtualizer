# 11.05.22----------------------------------------------------------------------------------------------------------------------
#  created by: Felix Eickeler 
#              felix.eickeler@tum.de       
# ----------------------------------------------------------------------------------------------------------------
#
#
from pathlib import Path

from PIL import Image
import numpy as np


def augment_texture(texture_path: Path, number_of_augmentations):
    texture = Image.open(texture_path)
    factor = np.ceil(number_of_augmentations ** (1. / 2.)).astype(np.int32)
    last_factor = np.ceil(number_of_augmentations / factor).astype(np.int32)

    # Tiling
    tiling_factor = 3
    tiled_texture = Image.new('L', (texture.width * tiling_factor, texture.width * tiling_factor))
    for w in range(tiling_factor):
        for h in range(tiling_factor):
            tiled_texture.paste(texture, (texture.width * w, texture.height * h))

    # prepare the stuff
    # max is 45 degrees with 0.5 so 1.41
    # scales = np.random.normal(1, 0.1, factor)
    # UPDATE: scale is defined by crops
    scales = np.array([1])
    # rotate = np.random.normal(0, 90, last_factor)
    rotate = np.linspace(0, 90, last_factor)
    lower_bounds = np.random.rand(factor, 2) * np.array([texture.width, texture.height])
    upper_bounds = np.array([texture.width, texture.height]) + lower_bounds
    crop_boxes = np.concatenate((lower_bounds, upper_bounds), axis=1)
    scaled_crop_boxes = (crop_boxes[:, :, None] * scales[None, None, :]).reshape((-1, 4), order="C")

    collector = []
    for angle in rotate:
        img_rot = tiled_texture.rotate(angle)
        for scb in scaled_crop_boxes:
            cropped = img_rot.crop(scb)
            collector.append(cropped.resize((texture.width, texture.height)))
    return collector[:number_of_augmentations]


def create_augmentations(texture_path: Path, folder: Path, number_of_augmentations):
    start = 0
    if folder.exists() and folder.is_dir():
        existing = list(folder.glob(f"{texture_path.stem}_*"))
        start += len(existing)
        number_of_augmentations -= start
    else:
        folder.mkdir(parents=True, exist_ok=True)

    if number_of_augmentations > 0:
        for i, tex in enumerate(augment_texture(texture_path, number_of_augmentations)):
            dst = folder / f"{texture_path.stem}_{i}{texture_path.suffix}"
            tex.save(dst)

    return folder
