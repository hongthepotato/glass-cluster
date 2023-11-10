import os
import random
import shutil
from pathlib import Path
from typing import List, Optional

import numpy as np
from dpdata import System
from pymatgen.core.periodic_table import Element
from pymatgen.core.structure import Structure


def structure_to_sys(pmg_structure: Structure) -> System:
    r"""Convert dpdata.System object into pymatgen.Structure object

    Parameters
    ----------
    pmg_structure : (`Structure`) structure information contained in `Pymatgen.core.Structure`

    Returns
    -------
    dp_system : (`System`) structure information contained in `dpdata.System`

    """
    seen = set()
    atom_names = [str(site.specie) for site in pmg_structure \
                  if not (str(site.specie) in seen or seen.add(str(site.specie)))]
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
) -> List[int]:
    r"""Substitute `n` atoms of specified specie around a certain atom within
    certain radius. if there are not enough `n` atoms within radius, the sphere
    would be enlarged 

    Parameters
    ----------
    structure : (`Structure`) structure to be doped
    first_index : (`int`) index of certain atom around which atoms would be replaced
    element_to_replace : (`str`) dopant type of element
    radius : (`float`) within this radius, atoms would be replaced
    n : (`int`) number of atoms to be replaced

    Returns
    -------
    remove_indices : (`List[int]`) the index of atoms to be replaced
    """
    neighbors = structure.get_neighbors(structure[first_index], radius)
    dis_indices_combine = [(i.index, structure.get_distance(first_index, i.index)) \
                           for i in neighbors if i.species_string == element_to_replace]
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
    compen_ratio: Optional[float] = 0.0,
    compen_type: Optional[str] = None
) -> Structure:
    r"""Generate doped structure in two different ways: 1.randomly; 2.around a certain atom

    Parameters
    ----------
    structure : (`Structure`) structure to be doped
    method : (`str`) generating method, choose from either `random` or `clustering`
    ratio : (`float`) the ratio certain type of atoms to be removed
    remove_type : (`str`) type of atoms to be removed
    dopant_type : (`str`) dopant type
    compen_ratio : (`float`)
    compen_type : (`str`)
    """
    random.seed(42)
    remove_indices = [i for i, site in enumerate(structure) if site.species_string == remove_type]
    num_remove = int(len(remove_indices) * ratio)
    if method == 'random':
        remove_indices_to_replace = random.sample(remove_indices, num_remove)
    elif method == 'clustering':
        indices_to_remove = []
        for i, site in enumerate(structure):
            if site.species_string == remove_type:
                indices_to_remove.append(i)
        if num_remove > len(indices_to_remove):
            raise ValueError(f"Cannot replace {num_remove} atoms, \
                             only {len(indices_to_remove)} available")
        first_index = random.sample(indices_to_remove)
        structure.replace(first_index, dopant_type)
        remove_indices_to_replace = substitute_atoms(
            structure,
            first_index,
            remove_type,
            10,
            num_remove
        )
    else:
        raise NotImplementedError('Only random and clustering supported for now.')
    for index in remove_indices_to_replace:
        structure.replace(index, dopant_type)
    num_compen_remove = int(num_remove * compen_ratio)
    compen_indices = [i for i, site in enumerate(structure) if site.species_string == compen_type]
    compen_indices_remove = random.sample(compen_indices, num_compen_remove)
    structure.remove_sites(compen_indices_remove)
    # structure.to('POSCAR-modified', 'poscar')
    return structure

def convert_to_lmp_data(
        structure: Structure,
        type_map: dict,
        mass_map: dict,
        work_dir: Path
    ):
    r"""write a pymatgen structure object to a file
    can be used for lammps calculation

    Parameters
    ----------
    structure : (`Structure`) structure
    type_map : (`dict`) {"0": H}
    mass_map : (`dict`) atomic mass of chemical element {"H": 1}
    """
    struc = structure_to_sys(structure)
    temp_file = os.path.join(work_dir, "lmp_temp.data")
    struc.to('lmp', temp_file)
    with open(temp_file, 'r', encoding='utf-8') as fp:
        lines = fp.readlines()
        new_lines = lines[0:8]
        new_lines.append('Masses\n')
        new_lines.append('\n')
        for ele_type in type_map.keys():
            new_lines.append(f'{int(ele_type[-1]) + 1} {mass_map[type_map[ele_type]]}\n')
        new_lines.append('\n')
        new_lines += lines[8:]
    with open(Path(work_dir) / 'lmp.data', 'w') as f:
        f.writelines(new_lines)
    os.remove(temp_file)
    file_path = Path(work_dir) / 'lmp.data'
    return file_path

def add_md_process(
    param: list,
    param_dict: dict,
    fix_id: int
):
    """_summary_

    Args:
        param (list): _description_
        param_dict (dict): _description_
        fix_id (int): _description_

    Raises:
        NotImplementedError: _description_

    Returns:
        _type_: _description_
    """    
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
    """_summary_

    Args:
        param (list): _description_
        e_tol (float, optional): _description_. Defaults to 1e-10.
        f_tol (float, optional): _description_. Defaults to 1e-8.

    Returns:
        _type_: _description_
    """    
    param.append(f'minimize        {e_tol} {f_tol} 10000 100000')
    return param

def build_in_lmp(
    processes: dict,
    # param: list,
    model_name: str,
    struc_file: str,
    work_dir: Path
) -> None:
    """_summary_

    Args:
        config (dict): _description_
        param (list): _description_
        model_name (str): _description_
        struc_file (str): _description_

    Raises:
        NotImplementedError: _description_

    Returns:
        _type_: _description_
    """    
    param = []
    param.append('units           metal\n')
    param.append('\n')
    param.append('atom_style      atomic\n')
    param.append('atom_modify     map array\n')
    param.append('boundary        p p p\n')
    param.append('atom_modify     sort 0 0.0\n')
    param.append(f'read_data       {struc_file}\n')
    param.append(f'pair_style      deepmd {model_name}\n')
    param.append('pair_coeff      * *\n')
    if processes:
        for sub_dict in processes:
            if sub_dict.get('process') == 'minimize':
                param = add_minimize(param)
            elif sub_dict.get('process') == 'md_run':
                param = add_md_process(param, sub_dict["params"], sub_dict["_idx"])
            else:
                raise NotImplementedError('only minimize and md_run supported for now.')
    with open(Path(work_dir) / 'in.lmp', 'w') as file:
        file.writelines(param)
    return None

def grasp_strucs_from_traj(
        traj_name: str,
        every_n_frame: int,
        type_map: dict,
        mass_map: dict,
    ) -> List[Path]:
    """This function is used to grasp single structures from a lammps trajectory

    Args:
        traj_name (str): filaname of the traj
        every_n_frame (int): select frame from the traj every n frames
        type_map (dict): type map
        mass_map (dict): mass map
    """
    total_strucs = System(traj_name, 'lammps/dump')
    selected_strucs = total_strucs[::every_n_frame]
    list_path = []
    for i, frame in enumerate(selected_strucs):
        frame.to('lmp', f'lmp-{i}.data')
        with open(f'lmp-{i}.data', 'r') as fp:
            lines = fp.readlines()
            new_lines = lines[0:8]
            new_lines.append('\n')
            new_lines.append('Masses\n')
            new_lines.append('\n')
            for ele_type in type_map.keys():
                new_lines.append(f'{int(ele_type[-1]) + 1} {mass_map[type_map[ele_type]]}\n')
            new_lines.append('\n')
            new_lines += lines[8:]
        with open(f'lmp-{i}.data', 'w') as f:
            f.writelines(new_lines)
        os.makedirs(f'lmp-{i}', exist_ok=True)
        shutil.copy(f'lmp-{i}.data', Path(f'lmp-{i}') / 'lmp.data')
        list_path.append(Path(f'lmp-{i}'))
        return list_path
