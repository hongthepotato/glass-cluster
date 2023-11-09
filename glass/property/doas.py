from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from tqdm import tqdm


def get_type_index(type_map, target_element):
    """_summary_

    Args:
        type_map (_type_): _description_
        target_element (_type_): _description_
    """    
    for key, value in type_map.items():
        if value == target_element:
            type_index = int(key[-1]) + 1
    return type_index

def parse_single(filename: str, target_element: str, type_map: dict):
    """This function is used to grasp atomic energy of a minimization
    task of lammps

    Args:
        filename (str): filename of the output of minimization
        target_element (str): target_element
        type_map (dict): type map
    """    
    data = []
    type_index = get_type_index(type_map, target_element)
    with open(filename, 'r', encoding='utf-8') as file:
        lines = file.readlines()
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith("ITEM:"):
                i += 9
                continue
            else:
                item = line.split()
                if int(item[1]) == int(type_index):
                    data.append(item)
            i += 1
    length = len(data)
    n = length // 2
    second_half_data = data[n::]
    return second_half_data

def plot_doas(target_folders: list, target_element: str, bins: int, type_map: dict):
    """_summary_

    Args:
        target_folders (list): _description_
        target_element (str): _description_
        bins (int): _description_
        type_map (dict): _description_
    """    
    filename = 'dump.atom_energy'
    data = []
    # target_energy = []
    folders = tqdm(target_folders)
    head = [["index", "atom_types", "energy"],]
    for folder in folders:
        data = parse_single(Path(folder) / filename, target_element, type_map)
        head = np.concatenate((head, data), axis=0)
    plot_data = list(head[1:,2])
    plot_data = [float(data) for data in plot_data]
    x_min = float(min(plot_data))
    x_max = float(max(plot_data))
    plt.hist(plot_data, bins)
    xticks = np.linspace(x_min, x_max, 5)
    xticks_labels = ['{:.3f}'.format(x) for x in xticks]
    plt.xticks(xticks, xticks_labels)
    plt.savefig('doas.png', dpi=300)
    plt.show()
    return None
