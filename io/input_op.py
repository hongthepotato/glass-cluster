import json
from dpdata import System
from pymatgen.core.structure import Structure
from pymatgen.io.vasp.inputs import Poscar
import numpy as np
import random
from pathlib import Path
import os
import shutil

from io.input import get_dope, convert_to_lmp_data

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

class StrucPrep(OP):

    @classmethod
    def get_input_sign(cls) -> OPIOSign:
        return OPIOSign({
            "filename": Parameter(str),
            "method": Parameter(str),
            "dopant_ratio": Parameter(float),
            "remove_type": Parameter(str),
            "dopant_type": Parameter(str),
            "compen_ratio": Parameter(float),
            "compen_type": Parameter(str)
        })
    
    @classmethod
    def get_output_sign(cls) -> OPIOSign:
        return OPIOSign({
            "dir_path": Artifact(Path)
        })
    
    @OP.exec_sign_check
    def execute(self, op_in: OPIO) -> OPIO:
        filename = op_in["filename"]
        method = op_in["method"]
        dopant_ratio = op_in["dopant_ratio"]
        remove_type = op_in["remove_type"]
        dopant_type = op_in["dopant_type"]
        compen_ratio = op_in["compen_ratio"]
        compen_type = op_in["compen_type"]
        structure = Structure.from_file(filename)
        new_structure = get_dope(
            structure, method,
            dopant_ratio,
            remove_type,
            dopant_type,
            compen_ratio,
            compen_type
        )
        dir_path = convert_to_lmp_data(new_structure)
        op_out = {
            "dir_path": dir_path
        }
        return op_out