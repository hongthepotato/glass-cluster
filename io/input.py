import json

def add_keep_process(
    param: list,
    thermo_steps: int,
    traj_file_name: str,
    fix_id: int,
    ensemble: str,
    n_steps: int,
    ini_t: float = 300,
    final_t: float = 300,
    t_damp: float = 0.1,
    t_step: float = 1e-4,
    ini_p: float = 0.1,
    final_p: float = 0.1,
    p_damp: float = 1.0,
    p_style: str = 'iso',
    dump_freq: int = 1000
):
    param.append('thermo_style    custom step temp epair etotal econserve press density pe\n')
    param.append(f'thermo          {thermo_steps}\n')
    param.append(f'fix             {fix_id} all {ensemble} temp {ini_t} {final_t} {t_damp} {p_style} {ini_p} {final_p} {p_damp}\n')
    param.append(f'timestep        {t_step}\n')
    param.append('neighbor        1.0 bin\n')
    param.append('neigh_modify    every 2 delay 10 check yes\n')
    param.append(f'dump Dumpstay all custom {dump_freq} {traj_file_name}.lammpstrj id type x y z\n')
    param.append(f'run             {n_steps}\n')
    param.append(f'unfix           {fix_id}\n')
    return param
    

def add_minimize(param: list, e_tol: float=1e-10, f_tol: float=1e-8):
    param.append(f'minimize        {e_tol} {f_tol} 10000 100000')
    return param

    


class InputParam(object):
    pass