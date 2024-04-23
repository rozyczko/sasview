import requests
from sas.sascalc.calculator.ausaxs.architecture import OS, determine_os

def get_ausaxs():
    _os = determine_os()
    url = "https://github.com/SasView/AUSAXS/releases/latest/download/"
    libs = None
    if _os == OS.WIN:
        lib = ["libausaxs.dll"]
    elif _os == OS.LINUX:
        lib = ["libausaxs.so"]
    elif _os == OS.MAC:
        lib = ["libausaxs.dylib"]
    if libs is not None:
        # we have to use a relative path since the package is not installed yet
        base_loc = "src/sas/sascalc/calculator/ausaxs/lib/"
        for lib in libs:
            response = requests.get(url+lib)

            # disable macos for now by renaming the local file
            if _os is OS.MAC:
                lib = "libausaxs.dylib.disabled"

            with open(base_loc+lib, "wb") as f:
                f.write(response.content)

def fetch_external_dependencies(): 
    #surround with try/except to avoid breaking the build if the download fails
    try:
        get_ausaxs()
    except Exception as e:
        print("Download of external dependencies failed.", e)
    return