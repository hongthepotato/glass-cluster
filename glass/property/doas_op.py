import glob
import os
import shutil
from pathlib import Path
from typing import List

from dflow.python import OP, OPIO, Artifact, OPIOSign, Parameter

from glass.io.input import grasp_strucs_from_traj
from glass.property.doas import generate_doas_mini_input, plot_doas


class GraspSnapShotOP(OP):
    """_summary_

    Args:
        OP (_type_): _description_
    """

    @classmethod
    def get_input_sign(cls) -> OPIOSign:
        return OPIOSign({
            "md_run": Artifact(Path),
            "traj_file_name": Parameter(str),
            # "minimize_input": Artifact(Path),
            "model": Artifact(Path),
            "energy_n_frame": Parameter(int),
            "type_map": Parameter(dict),
            "mass_map": Parameter(dict)
        })

    @classmethod
    def get_output_sign(cls) -> OPIOSign:
        return OPIOSign({
            "minimize_dirs": Artifact(List[Path]),
            "num_minimize": Parameter(int)
        })

    @OP.exec_sign_check
    def execute(self, op_in: OPIO) -> OPIO:
        traj_file_name = op_in["traj_file_name"] + '.lammpstrj'
        # minimize_input = op_in["minimize"]
        model = op_in["model"]
        energy_n_frame = op_in["energy_n_frame"]
        type_map = op_in["type_map"]
        mass_map = op_in["mass_map"]
        os.chdir(op_in["md_run"])
        minimize_dirs = grasp_strucs_from_traj(
            traj_file_name,
            energy_n_frame,
            type_map,
            mass_map
        )
        for mini_dir in minimize_dirs:
            generate_doas_mini_input(model.name, mini_dir)
            # shutil.copy(minimize_input, mini_dir)
            shutil.copy(model, mini_dir)
        op_out = {
            "minimize_dirs": minimize_dirs,
            "num_minimize": len(minimize_dirs)
        }
        return op_out

class PlotDoas(OP):
    """_summary_

    Args:
        OP (_type_): _description_
    """

    @classmethod
    def get_input_sign(cls) -> OPIOSign:
        return OPIOSign({
            "minimize_dirs": Artifact(List[Path]),
            "target_element": Parameter(str),
            "bins": Parameter(int),
            "type_map": Parameter(dict)
        })

    @classmethod
    def get_output_sign(cls) -> OPIOSign:
        return OPIOSign({
            "doas_fig": Artifact(Path)
        })

    @OP.exec_sign_check
    def execute(self, op_in: OPIO) -> OPIO:
        target_element = op_in["target_element"]
        bins = op_in["bins"]
        type_map = op_in["type_map"]
        target_folders = [folder for folder in glob.glob('lmp*') if os.path.isdir(folder)]
        fig_path = plot_doas(target_folders, target_element, bins, type_map)
        op_out = {
            "doas_fig": fig_path
        }
        return op_out
