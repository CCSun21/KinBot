import os
import re
import numpy as np
import copy

"""
Functions to read QChem output files.
"""


def read_geom(outfile, dummy=False):
    """Read the final geometry from a QChem output file  file.
    """
    from collections import Iterable
    from ase import Atoms, Atom
    read_coords = False
    mol = Atoms()
    with open(outfile) as f:
        for line in f:
            if 'OPTIMIZATION CONVERGED' in line:
                read_coords = True
            elif not read_coords or len(line) < 2:
                continue
            elif line.split()[0].isdecimal():
                mol.append(Atom(symbol=line.split()[1],
                                position=line.split()[2:5]))
            elif 'Z-matrix' in line:
                read_coords = False
            else:
                continue
        if isinstance(dummy, Iterable):  # TODO Check
            for i, d in enumerate(dummy):
                mol.positions[-(i + 1)] = d[0:3]
    return mol


def read_zpe(outfile):
    """
    Read the zpe
    """

    with open(outfile) as f:
        for line in f:
            if 'Zero point vibrational energy:' in line:
                zpe = line.split()[4]

    try:
        return float(zpe)
    except ValueError:
        pass
    raise ValueError(f'Zero-Point energy has non-numeric value: {zpe}')



def read_freq(outfile, atoms):  # TODO
    """
    Read the frequencies
    """
    freqs = []
    natom = len([at for at in atoms if at != 'X'])  # filter out the dummy atoms

    with open(outfile) as f:
        for line in f:
            if 'Frequency:' in line:
                if natom == 2:
                    return [float(line.split()[1])]
                freqs.extend([float(fr) for fr in line.split()[1:]])
    return freqs


def read_convergence(outfile):
    """
    Check for the four YES.
    0: did not converge
    1: forces and displacements converged
    2: forces converged
    """

    with open(outfile) as f:
        lines = f.readlines()

    for n, line in enumerate(lines):
        if 'Item               Value     Threshold  Converged?' in line:
            if 'YES' in lines[n + 1]:
                if 'YES' in lines[n + 2]:
                    if 'YES' in lines[n + 3]:
                        if 'YES' in lines[n + 4]:
                            return 1
                    else:
                        return 2

    return 0  # will look through the whole file


def constraint(mol, fix, change):
    """
    Convert constraints into PCBFGS constraints.
    """

    bonds = []
    angles = []
    dihedrals = []
    for fi in fix:
        if len(fi) == 2:
            # careful: atom indices in the fix lists start at 1
            bondlength = mol.get_distance(fi[0] - 1, fi[1] - 1)
            bonds.append([bondlength, [fi[0] - 1, fi[1] - 1]])
        if len(fi) == 3:
            # careful: atom indices in the fix lists start at 1
            angle = mol.get_angle(fi[0] - 1, fi[1] - 1,
                                  fi[2] - 1) * np.pi / 180.
            angles.append([angle, [fi[0] - 1, fi[1] - 1, fi[2] - 1]])
        if len(fi) == 4:
            # careful: atom indices in the fix lists start at 1
            dihed = mol.get_dihedral(fi[0] - 1, fi[1] - 1, fi[2] - 1,
                                     fi[3] - 1) * np.pi / 180.
            dihedrals.append(
                [dihed, [fi[0] - 1, fi[1] - 1, fi[2] - 1, fi[3] - 1]])
    for ci in change:
        if len(ci) == 3:
            # careful: atom indices in the fix lists start at 1
            bondlength = ci[2]
            bonds.append([bondlength, [ci[0] - 1, ci[1] - 1]])
        if len(ci) == 4:
            # careful: atom indices in the fix lists start at 1
            angle = ci[3] * np.pi / 180.
            angles.append([angle, [ci[0] - 1, ci[1] - 1, ci[2] - 1]])
        if len(ci) == 5:
            # careful: atom indices in the fix lists start at 1
            dihed = ci[4] * np.pi / 180.
            dihedrals.append(
                [dihed, [ci[0] - 1, ci[1] - 1, ci[2] - 1, ci[3] - 1]])

    return bonds, angles, dihedrals


def read_hess(job, natom):
    """
    Read the hessian of a QChem chk file
    """

    # initialize Hessian
    hess = np.zeros((3 * natom, 3 * natom))

    fchk = str(job) + '.fchk'
    chk = str(job) + '.chk'
    if os.path.exists(chk):
        # create the fchk file using formchk
        os.system('formchk ' + job + '.chk > /dev/null')

    with open(fchk) as f:
        lines = f.read().split('\n')

    nvals = 3 * natom * (3 * natom + 1) / 2

    for index, line in enumerate(reversed(lines)):
        if re.search('Cartesian Force Constants', line) != None:
            hess_flat = []
            n = 0
            while len(hess_flat) < nvals:
                hess_flat.extend(
                    [float(val) for val in lines[-index + n].split()])
                n += 1
            n = 0
            for i in range(3 * natom):
                for j in range(i + 1):
                    hess[i][j] = hess_flat[n]
                    hess[j][i] = hess_flat[n]
                    n += 1
            break
    return hess


def read_imag_mode(job, natom):
    """
    Read the imaginary normal mode displacements from a log file.
    Only for saddle points! It will read the firs normal mode
    for a well, but that's not very useful.
    """

    nmode = np.zeros([natom, 3])
    joblog = '{}.log'.format(job)
    with open(joblog) as f:
        lines = f.read().split('\n')

    for l, line in enumerate(lines):
        if line[:10] == '  Atom  AN':
            for n in range(natom):
                mm = lines[l + n + 1].split()
                nmode[n][0] = float(mm[2])
                nmode[n][1] = float(mm[3])
                nmode[n][2] = float(mm[4])
            break

    return (nmode)


def read_all_irc_geoms(outfile):
    """
    Read the IRC geometries from a QChem 16 log file.
    Used in sampler code.
    """

    with open(outfile) as f:
        lines = f.readlines()

    start = True
    all_geoms = None
    atom = None
    for index, line in enumerate(lines):
        if 'Charge = ' in line:
            charge = line.split()[2]
            mult = line.split()[5]
        if 'CURRENT STRUCTURE' in line:
            geom = np.array([])
            atom = np.array([])
            natom = 0
            while True:
                current_line = lines[index + 6 + natom]
                if '-------' in current_line:
                    geom = np.reshape(geom, (-1, 3))
                    if start:
                        all_geoms = np.array([copy.deepcopy(geom)])
                        start = False
                    else:
                        all_geoms = np.vstack((all_geoms, geom[None]))
                    break
                atom = np.append(atom, int(current_line.split()[1]))
                g = np.array(current_line.split()[2:5]).astype(float)
                geom = np.append(geom, g)
                natom += 1
    return atom, all_geoms, charge, mult


def write_constraints(inp_file):
    pass
