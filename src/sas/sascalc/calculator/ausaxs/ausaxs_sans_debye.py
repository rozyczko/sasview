import ctypes as ct
import numpy as np
import logging
from enum import Enum
import importlib.resources as resources

# we need to be able to differentiate between being uninitialized and failing to load
class lib_state(Enum):
    UNINITIALIZED = 0
    FAILED = 1
    READY = 2

ausaxs_state = lib_state.UNINITIALIZED
ausaxs = None

def attach_hooks():
    global ausaxs_state
    global ausaxs

    from sas.sascalc.calculator.ausaxs.architecture import OS, Arch, determine_os, determine_cpu_support
    sys = determine_os()
    arch = determine_cpu_support()

    # as_file extracts the dll if it is in a zip file and probably deletes it afterwards,
    # so we have to do all operations on the dll inside the with statement
    with resources.as_file(resources.files("sas.sascalc.calculator.ausaxs.lib")) as loc:
        if sys is OS.WIN and arch is Arch.AVX:
            path = loc.joinpath("libausaxs.dll")
        elif sys is OS.LINUX and arch is Arch.AVX:
            path = loc.joinpath("libausaxs.so")
        elif sys is OS.MAC:
            path = loc.joinpath("libausaxs.dylib")
        else:
            ausaxs_state = lib_state.FAILED
            logging.log("AUSAXS: Unsupported OS or CPU architecture. Using default Debye implementation.")
            return

        ausaxs_state = lib_state.READY
        try:
            # evaluate_sans_debye func
            ausaxs = ct.CDLL(str(path))
            ausaxs.evaluate_sans_debye.argtypes = [
                ct.POINTER(ct.c_double), # q vector
                ct.POINTER(ct.c_double), # x vector
                ct.POINTER(ct.c_double), # y vector
                ct.POINTER(ct.c_double), # z vector
                ct.POINTER(ct.c_double), # w vector
                ct.c_int,                # nq (number of points in q)
                ct.c_int,                # nc (number of points in x, y, z, w)
                ct.POINTER(ct.c_int),    # status (0 = success, 1 = q range error, 2 = other error)
                ct.POINTER(ct.c_double)  # Iq vector for return value
            ]
            ausaxs.evaluate_sans_debye.restype = None # don't expect a return value
            ausaxs_state = lib_state.READY
        except Exception as e:
            ausaxs_state = lib_state.FAILED
            logging.warning("Failed to hook into AUSAXS library, using default Debye implementation")
            print(e)

def ausaxs_available():
    """
    Check if the AUSAXS library is available.
    """
    if ausaxs_state is lib_state.UNINITIALIZED:
        attach_hooks()
    return ausaxs_state is lib_state.READY

def evaluate_sans_debye(q, coords, w):
    """
    Compute I(q) for a set of points using Debye sums.
    This uses AUSAXS if available, otherwise it uses the default implementation.
    *q* is the q values for the calculation.
    *coords* are the sample points.
    *w* is the weight associated with each point.
    """
    if ausaxs_state is lib_state.UNINITIALIZED:
        attach_hooks()
    if ausaxs_state is lib_state.FAILED:
        from sas.sascalc.calculator.ausaxs.sasview_sans_debye import sasview_sans_debye
        return sasview_sans_debye(q, coords, w)

    _Iq = (ct.c_double * len(q))()
    _nq = ct.c_int(len(q))
    _nc = ct.c_int(len(w))
    _q = q.ctypes.data_as(ct.POINTER(ct.c_double))
    _x = coords[0:, :].ctypes.data_as(ct.POINTER(ct.c_double))
    _y = coords[1:, :].ctypes.data_as(ct.POINTER(ct.c_double))
    _z = coords[2:, :].ctypes.data_as(ct.POINTER(ct.c_double))
    _w = w.ctypes.data_as(ct.POINTER(ct.c_double))
    _status = ct.c_int()

    # do the call
    ausaxs.evaluate_sans_debye(_q, _x, _y, _z, _w, _nq, _nc, ct.byref(_status), _Iq)

    # check for errors
    if _status.value != 0:
        logging.error("AUSAXS calculator terminated unexpectedly. Using default Debye implementation instead.")
        from sas.sascalc.calculator.ausaxs.sasview_sans_debye import sasview_sans_debye
        return sasview_sans_debye(q, coords, w)

    return np.array(_Iq)