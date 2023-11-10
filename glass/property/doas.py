from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from tqdm import tqdm

def generate_doas_mini_input(model: str, work_dir: Path) -> Path:
    """_summary_

    Args:
        work_dir (Path): _description_
    """   
    ret = [] 
    ret.append("units           metal\n")
    ret.append("\n")
    ret.append("atom_style      atomic\n")
    ret.append("atom_modify     map array\n")
    ret.append("boundary        p p p\n")
    ret.append("atom_modify     sort 0 0.0\n")
    ret.append("\n")
    ret.append("read_data       lmp.data\n")
    ret.append("\n")
    ret.append(f"pair_style      deepmd {model}\n")
    ret.append("pair_coeff      * * \n")
    ret.append("\n")
    ret.append("compute peratom_energy all pe/atom\n")
    ret.append("dump peratom_dump all custom 100 dump.atom_energy id type c_peratom_energy\n")
    ret.append("minimize 1.0e-6 1.0e-8 10000 100000\n")
    with open(Path(work_dir) / "in.lmp", 'w', encoding="utf=8") as f:
        f.writelines(ret)
    file_path = Path(work_dir) / 'in.lmp'
    return file_path

def get_type_index(type_map, target_element):
    """get the index of target element

    Args:
        type_map (_type_): type map start from zero {"0": H}
        target_element (_type_): element like "H"
    """    
    type_index = None
    for key, value in type_map.items():
        if value == target_element:
            type_index = int(key[-1]) + 1
            break
    if type_index is None:
        raise ValueError(f"Target element '{target_element}' not found in type_map")
    
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

def plot_doas(
    target_folders: list,
    target_element: str,
    bins: int,
    type_map: dict
):
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
    fig_path = Path('doas.png')
    return fig_path
