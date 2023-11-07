import json
from dpdata import System
from pymatgen.core.structure import Structure
from pymatgen.io.vasp.inputs import Poscar
import numpy as np
import random
from pathlib import Path
import os
import shutil

import pandas as pd
from dflow.python import (
    OP,
    OPIO,
    Artifact,
    BigParameter,
    OPIOSign,
    Parameter,
    TransientError,
)
from dflow.python.opio import OPIO, OPIOSign
from dpdata import System

def structure_to_sys(pmg_structure):
    r"""Convert dpdata.System object into pymatgen.Structure object

    Parameters
    ----------
    pmg_structure : (`Structure`) structure information contained in `Pymatgen.core.Structure`

    Returns
    -------
    dp_system : (`System`) structure information contained in `dpdata.System`

    """
    from pymatgen.core.periodic_table import Element
    seen = set()
    atom_names = [str(site.specie) for site in pmg_structure if not (str(site.specie) in seen or seen.add(str(site.specie)))]
    atom_numbs = [int(pmg_structure.composition[Element(name)]) for name in atom_names]
    atom_types = np.array([atom_names.index(str(site.specie)) for site in pmg_structure])
    data = {
        'atom_names': atom_names,
        'atom_numbs': atom_numbs,
        'atom_types': atom_types,
        'cells': np.array([pmg_structure.lattice.matrix.tolist()]),
        'coords': np.array([pmg_structure.cart_coords.tolist()]),
        'orig': np.array([0, 0, 0]),
    }
    dp_system_back = System()
    dp_system_back.data = data
    return dp_system_back

def substitute_atoms(
    structure: Structure,
    first_index: int,
    element_to_replace: str,
    radius: float,
    n: int
):
    r"""
    """
    neighbors = structure.get_neighbors(structure[first_index], radius)
    dis_indices_combine = [(i.index, structure.get_distance(first_index, i.index)) for i in neighbors if i.species_string == element_to_replace]
    sorted_list = sorted(dis_indices_combine, key=lambda x: x[1])
    try:
        if n > len(sorted_list):
            raise IndexError("Not enough elements to replace")
        remove_indices = [x[0] for x in sorted_list[:n]]
    except IndexError:
        radius *= 1.1
        remove_indices = substitute_atoms(structure, first_index, element_to_replace, radius, n)
    return remove_indices

def get_dope(
    structure: Structure,
    method: str,
    ratio: float,
    remove_type: str,
    dopant_type: str,
    compen_ratio: float,
    compen_type: str
):
    r"""
    """
    random.seed(42)
    remove_indices = [i for i, site in enumerate(structure) if site.species_string == remove_type]
    num_remove = int(len(remove_indices) * ratio)
    if method == 'random': 
        remove_indices_to_replace = random.sample(remove_indices, num_remove)
    if method == 'clustering':
        indices_to_remove = []
        for i, site in enumerate(structure):
            if site.species_string == remove_type:
                indices_to_remove.append(i)
        if num_remove > len(indices_to_remove):
            raise ValueError(f"Cannot replace {num_remove} atoms, only {len(indices_to_remove)} available")
        first_index = random.sample(indices_to_remove)
        structure.replace(first_index, dopant_type)
        remove_indices_to_replace = substitute_atoms(structure, first_index, remove_type, 10, num_remove)
    for index in remove_indices_to_replace:
        structure.replace(index, dopant_type)
    num_compen_remove = int(num_remove * compen_ratio)
    compen_indices = [i for i, site in enumerate(structure) if site.species_string == compen_type]
    compen_indices_remove = random.sample(compen_indices, num_compen_remove)
    structure.remove_sites(compen_indices_remove)
    # structure.to('POSCAR-modified', 'poscar')
    return structure

def convert_to_lmp_data(structure: Structure, type_map: dict, mass_map: dict):
    r"""
    """
    struc = structure_to_sys(structure)
    struc.to('lmp', 'lmp.data')
    with open('lmp.data', 'r') as fp:
        lines = fp.readlines()
        new_lines = lines[0:8]
        new_lines.append('\n')
        new_lines.append('Masses\n')
        new_lines.append('\n')
        for ele_type in type_map.keys():
            new_lines.append(f'{int(ele_type[-1]) + 1} {mass_map[type_map[ele_type]]}\n')
        new_lines.append('\n')
        new_lines += lines[8:]
    with open('lmp.data', 'w') as f:
        f.writelines(new_lines)
    dir_name = 'lmp'
    os.makedirs('lmp', exist_ok=True)
    dir_path = Path(dir_name)
    shutil.copy('lmp.data', dir_path)
    # shutil.copy(model_name, Path(dir_name))
    # shutil.copy('in.lmp', Path(dir_name))
    return dir_path

def add_md_process(
    param: list,
    param_dict: dict,
    fix_id: int
):
    param.append('thermo_style    custom step temp epair etotal econserve press density pe\n')
    param.append(f'thermo          {param_dict["thermo_steps"]}\n')
    ensemble = param_dict["ensemble"]
    if ensemble == 'npt':
        param.append(f'fix             {fix_id} all {ensemble} temp {param_dict["ini_t"]} \
                     {param_dict["final_t"]} {param_dict["t_damp"]} {param_dict["p_style"]} \
                        {param_dict["ini_p"]} {param_dict["final_p"]} {param_dict["p_damp"]}\n')
    elif ensemble == 'nvt':
        param.append(f'fix             {fix_id} all {ensemble} temp {param_dict["ini_t"]} \
                     {param_dict["final_t"]} {param_dict["t_damp"]}\n')
    else:
        raise NotImplementedError('Only npt and nvt supported for now.')
    param.append(f'timestep        {param_dict["time_step"]}\n')
    param.append('neighbor        1.0 bin\n')
    param.append('neigh_modify    every 2 delay 10 check yes\n')
    param.append(f'dump Dumpstay all custom {param_dict["dump_freq"]} \
                 {param_dict["traj_file_name"]}.lammpstrj id type x y z\n')
    param.append(f'run             {param_dict["n_steps"]}\n')
    param.append(f'unfix           {fix_id}\n')
    return param
    
def add_minimize(param: list, e_tol: float=1e-10, f_tol: float=1e-8):
    param.append(f'minimize        {e_tol} {f_tol} 10000 100000')
    return param

def build_in_lmp(config: dict, param: list, model_name: str, struc_file: str):
    param.append(f'units           metal\n')
    param.append('\n')
    param.append('atom_style      atomic\n')
    param.append('atom_modify     map array\n')
    param.append('boundary        p p p\n')
    param.append('atom_modify     sort 0 0.0\n')
    param.append(f'read_data       {struc_file}\n')
    param.append(f'pair_style      deepmd {model_name}\n')
    param.append('pair_coeff      * *\n')
    if config.get["processes"]:
        processes = config.get["processes"]
        for sub_dict in processes:
            if sub_dict.get('process') == 'minimize':
                param = add_minimize(param)
            elif sub_dict.get('process') == 'md_run':
                param = add_md_process(param, sub_dict["params"], sub_dict["_idx"])
            else:
                raise NotImplementedError('only minimize and md_run supported for now.')
    with open('in.lmp', 'w') as file:
        file.writelines(param)
    return None

def grasp_strucs_from_traj(traj_name: str, every_n_frame: int):
    total_strucs = System(traj_name, 'lammps/dump')
    selected_strucs = total_strucs[::every_n_frame]
    type_map = {'TYPE_0': 'Si','TYPE_1':'O', 'TYPE_2':'Bi'}
    pass