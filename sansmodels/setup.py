"""
 Installation script for SANS models

  - To compile and install:
      python setup.py install
  - To create distribution:
      python setup.py bdist_wininst
  - To create odb files:
      python setup.py odb

"""
import sys
import os

    
from numpy.distutils.misc_util import get_numpy_include_dirs
numpy_incl_path = os.path.join(get_numpy_include_dirs()[0], "numpy")

def createODBcontent(class_name):
    """
        Return the content of the Pyre odb file for a given class
        @param class_name: Name of the class to write an odb file for [string]
        @return: content of the file [string]
    """
    content  = "\"\"\"\n"
    content += "  Facility for SANS model\n\n"
    content += "  WARNING: THIS FILE WAS AUTOGENERATED AT INSTALL TIME\n"
    content += "           DO NOT MODIFY\n\n"
    content += "  This code was written as part of the DANSE project\n"
    content += "  http://danse.us/trac/sans/\n"
    content += "  @copyright 2007:"
    content += "  SANS/DANSE Group (University of Tennessee), for the DANSE project\n\n"
    content += "\"\"\"\n"
    content += "def model():\n"
    content += "    from ScatteringIntensityFactory import ScatteringIntensityFactory\n"
    content += "    from sans.models.%s import %s\n" % (class_name, class_name)
    content += "    return ScatteringIntensityFactory(%s)('%s')\n"\
                 % (class_name, class_name)

    return content

def createODBfiles():
    """
       Create odb files for all available models
    """
    from sans.models.ModelFactory import ModelFactory
    
    class_list = ModelFactory().getAllModels()
    for name in class_list:
        odb = open("src/sans/models/pyre/%s.odb" % name, 'w')
        odb.write(createODBcontent(name))
        odb.close()
        print "src/sans/models/pyre/%s.odb created" % name
        
#
# Proceed with installation
#

# First, create the odb files
if len(sys.argv) > 1 and sys.argv[1].lower() == 'odb':
    print "Creating odb files"
    try:
        createODBfiles()
    except:    
        print "ERROR: could not create odb files"
        print sys.exc_value
    sys.exit()

# Then build and install the modules
from distutils.core import Extension, setup
#from setuptools import setup#, find_packages

# Build the module name
srcdir  = os.path.join("src", "sans", "models", "c_extensions")
igordir = os.path.join("src","sans", "models", "libigor")
c_model_dir = os.path.join("src", "sans", "models", "c_models")
smear_dir  = os.path.join("src", "sans", "models", "c_smearer")
print "Installing SANS models"


IGNORED_FILES = ["a.exe",
                 "__init__.py"
                 ".svn",
                   "lineparser.py",
                   "run.py",
                   "CGaussian.cpp",
                   "CLogNormal.cpp",
                   "CLorentzian.cpp",
                   "CSchulz.cpp",
                   "WrapperGenerator.py",
                   "wrapping.py",
                   "winFuncs.c"]
EXTENSIONS = [".c", ".cpp"]

def append_file(file_list, dir_path):
    """
    Add sources file to sources
    """
    for f in os.listdir(dir_path):
        if os.path.isfile(os.path.join(dir_path, f)):
            _, ext = os.path.splitext(f)
            if ext.lower() in EXTENSIONS and f not in IGNORED_FILES:
                file_list.append(os.path.join(dir_path, f)) 
        elif os.path.isdir(os.path.join(dir_path, f)) and \
                not f.startswith("."):
            sub_dir = os.path.join(dir_path, f)
            for new_f in os.listdir(sub_dir):
                if os.path.isfile(os.path.join(sub_dir, new_f)):
                    _, ext = os.path.splitext(new_f)
                    if ext.lower() in EXTENSIONS and\
                         new_f not in IGNORED_FILES:
                        file_list.append(os.path.join(sub_dir, new_f)) 
        
model_sources = []
append_file(file_list=model_sources, dir_path=srcdir)
append_file(file_list=model_sources, dir_path=igordir)
append_file(file_list=model_sources, dir_path=c_model_dir)
smear_sources = []
append_file(file_list=smear_sources, dir_path=smear_dir)


dist = setup(
    name="sans.models",
    version = "0.9.1",
    description = "Python module for SANS scattering models",
    author = "SANS/DANSE",
    author_email = "sansdanse@gmail.gov",
    url = "http://danse.us/trac/sans",
    
    # Place this module under the sans package
    #ext_package = "sans",
    
    # Use the pure python modules
    package_dir = {"sans":os.path.join("src", "sans"),
                   "sans.models":os.path.join("src", "sans", "models"),
                   "sans.models.sans_extension":srcdir,
                  },
    package_data={'sans.models': [os.path.join('media', "*")]},
    packages = ["sans","sans.models",
                "sans.models.sans_extension","sans.models.pyre",],
    
    ext_modules = [ Extension("sans.models.sans_extension.c_models",
             sources=model_sources,                 
      
        include_dirs=[igordir, srcdir, c_model_dir, numpy_incl_path]),       
        # Smearer extension
        Extension("sans.models.sans_extension.smearer",
                   sources = [os.path.join(smear_dir, 
                                          "smearer.cpp"),
                             os.path.join(smear_dir, "smearer_module.cpp"),],
        include_dirs=[smear_dir, numpy_incl_path]),
        Extension("sans.models.sans_extension.smearer2d_helper",
                  sources = [os.path.join(smear_dir, 
                                          "smearer2d_helper_module.cpp"),
                             os.path.join(smear_dir, "smearer2d_helper.cpp"),],
        include_dirs=[smear_dir,numpy_incl_path]
        )
        ]
    )
        
