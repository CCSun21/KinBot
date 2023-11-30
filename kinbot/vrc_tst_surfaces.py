import numpy as np
from kinbot import constants

class VRC_TST_Surface:
    def __init__(self, fragments, pp_dist):
        self.centers = {}
        for frag in fragments:

            self.centers[f"{frag.frag_number}"] = np.ndarray.tolist(np.asarray(frag.pivot_points)/ constants.BOHRtoANGSTROM)

        self.distances = []
        for index, element in enumerate(pp_dist):
            self.distances.append(list(element/ constants.BOHRtoANGSTROM))

    def __repr__(self):
        return f"Surface(pivotpoints={self.centers},\n          distances={self.distances}),"\
            .replace("[[", "np.array([[")\
            .replace("]]","]])")\
            .replace("]]),","]]),\n                    ")\
            .replace("])),","])),\n\n")
