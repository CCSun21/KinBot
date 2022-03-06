import re
from math import pi
import numpy as np
import ase
from ase import Atoms
from ase.calculators.gaussian import Gaussian
from ase.db import connect
from kinbot import reader_gauss

db = connect('{working_dir}/kinbot.db')
label = '{label}'
logfile = '{label}.log'

mol = Atoms(symbols={atom}, positions={geom})

kwargs = {kwargs}
Gaussian.command = '{qc_command} < PREFIX.com > PREFIX.log'
calc = Gaussian(**kwargs)
mol.set_calculator(calc)

success = True

try:
    e = mol.get_potential_energy() # use the Gaussian optimizer
    mol.positions = reader_gauss.read_geom(logfile, mol)
    db.write(mol, name=label, data={{'energy': e,'status': 'normal'}})
except:
    mol.positions = reader_gauss.read_geom(logfile, mol)
    if mol.positions is not None:
        db.write(mol, name=label, data={{'status': 'normal'}}) #although there is an error, continue from the final geometry
    else:
        db.write(mol, name=label, data={{'status': 'error'}})
        success = False

with open(logfile, 'a') as f:
    f.write('done\n')

if success:
    label = '{label}_prod'
    logfile = '{label}_prod.log'
    # start the product optimization
    prod_kwargs = {prod_kwargs}
    calc_prod = Gaussian(**prod_kwargs)
    mol_prod = Atoms(symbols={atom}, positions=mol.positions)
    mol_prod.set_calculator(calc_prod)
    try:
        e = mol_prod.get_potential_energy() # use the Gaussian optimizer
        mol_prod.positions = reader_gauss.read_geom(logfile, mol_prod)
        db.write(mol, name=label, data={{'energy': e,'status': 'normal'}})
    except RuntimeError: 
        mol_prod.positions = reader_gauss.read_geom(logfile, mol_prod)
        if mol_prod.positions is not None:
            db.write(mol_prod, name=label, data={{'status': 'normal'}}) 
        else:
            db.write(mol_prod, name=label, data={{'status': 'error'}})

    with open(logifle, 'a') as f:
        f.write('done\n')
