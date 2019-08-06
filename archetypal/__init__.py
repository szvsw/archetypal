################################################################################
# Module: __init__.py
# Description: Archetypal: Retrieve, construct and analyse building archetypes
# License: MIT, see full license in LICENSE.txt
# Web: https://github.com/samuelduchesne/archetypal
################################################################################

# Version of the package
__version__ = "1.2.6"
# Latest version of EnergyPlus compatible with archetypal
ep_version = "8-9-0"

# warn if a newer version of archetypal is available
from outdated import warn_if_outdated

warn_if_outdated("archetypal", __version__)

from .utils import *
from .simple_glazing import *
from .idfclass import *
from .energyseries import EnergySeries
from .energydataframe import EnergyDataFrame
from .reportdata import ReportData
from .tabulardata import TabularData
from .schedule import Schedule
from .dataportal import *
from .plot import *
from .trnsys import *
from .template import *
from .core import *
from .building import *
from .umi_template import *
from .cli import *
