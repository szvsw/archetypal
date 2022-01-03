"""archetypal ConstructionBase and LayeredConstruction.

Notes:
    Thank you to `honeybee-energy` for implementing heat transfer coefficient
    formulas from ISO. Those where adapted to the structure of the
    archetypal.template module.
"""

import math
from typing import List, Union

from pydantic import BaseModel, Field, validator
from validator_collection import validators

from archetypal.template.materials import GasMaterial
from archetypal.template.materials.gas_layer import GasLayer
from archetypal.template.materials.material_layer import MaterialLayer
from archetypal.template.umi_base import UmiBase


class ConstructionBase(UmiBase):
    """A class used to store data linked to Life Cycle aspects.

    For more information on the Life Cycle Analysis performed in UMI, see:
    https://umidocs.readthedocs.io/en/latest/docs/life-cycle-introduction.html#life-cycle-impact
    """

    AssemblyCarbon: float = Field(0, description="assembly carbon [kgCO2/m2]")
    AssemblyCost: float = Field(0, description="assembly carbon [$/m2]")
    AssemblyEnergy: float = Field(0, description="assembly energy [MJ/m2]")
    DisassemblyCarbon: float = Field(0, description="disassembly carbon [kgCO2/m2]")
    DisassemblyEnergy: float = Field(0, description="disassembly energy [MJ/m2]")

    def duplicate(self):
        """Get copy of self."""
        return self.__copy__()

    def __key__(self):
        """Get a tuple of attributes. Useful for hashing and comparing."""
        return (
            self.AssemblyCarbon,
            self.AssemblyCost,
            self.AssemblyEnergy,
            self.DisassemblyCarbon,
            self.DisassemblyEnergy,
        )

    def __eq__(self, other):
        """Assert self is equivalent to other."""
        return isinstance(other, ConstructionBase) and self.__key__() == other.__key__()

    def __copy__(self):
        """Create a copy of self."""
        return self.__class__(
            self.Name,
            self.AssemblyCarbon,
            self.AssemblyCost,
            self.AssemblyEnergy,
            self.DisassemblyCarbon,
            self.DisassemblyEnergy,
        )


class LayeredConstruction(ConstructionBase):
    """Defines the layers of an :class:`OpaqueConstruction`.

    Attributes:
        Layers (list of archetypal.MaterialLayer): List of MaterialLayer objects from
            outside to inside.
    """

    Layers: List[Union[MaterialLayer, GasLayer]] = Field(
        ...,
        min_items=1,
        max_items=10,
        description="A list of :class:`MaterialLayer` or :class:`GasLayer` objects.",
    )

    @validator("Layers")
    def valid_layer(cls, value):
        assert isinstance(
            value[0], MaterialLayer
        ), "The outside layer cannot be a GasLayer"
        assert isinstance(
            value[-1], MaterialLayer
        ), "The inside layer cannot be a GasLayer"
        return value

    @property
    def r_value(self):
        """Get or set the thermal resistance [K⋅m2/W] (excluding air films)."""
        return sum([layer.r_value for layer in self.Layers])

    @property
    def u_value(self):
        """Get the heat transfer coefficient [W/m2⋅K] (excluding air films)."""
        return 1 / self.r_value

    @property
    def r_factor(self):
        """Get the R-factor [m2-K/W] (including air films)."""
        return 1 / self.out_h_simple() + self.r_value + 1 / self.in_h_simple()

    def out_h_simple(self):
        """Get the simple outdoor heat transfer coefficient according to ISO 10292.

        This is used for all opaque R-factor calculations.
        """
        return 23

    def in_h_simple(self):
        """Get the simple indoor heat transfer coefficient according to ISO 10292.

        This is used for all opaque R-factor calculations.
        """
        return 3.6 + (4.4 * self.inside_emissivity / 0.84)

    def out_h(self, wind_speed=6.7, t_kelvin=273.15):
        """Get the detailed outdoor heat transfer coefficient according to ISO 15099.

        This is used for window U-factor calculations and all of the
        temperature_profile calculations.

        Args:
            wind_speed (float): The average outdoor wind speed [m/s]. This affects the
                convective heat transfer coefficient. Default is 6.7 m/s.
            t_kelvin (float): The average between the outdoor temperature and the
                exterior surface temperature. This can affect the radiative heat
                transfer. Default is 273.15K (0C).
        """
        _conv_h = 4 + (4 * wind_speed)
        _rad_h = 4 * 5.6697e-8 * self.outside_emissivity * (t_kelvin ** 3)
        return _conv_h + _rad_h

    def in_h(self, t_kelvin=293.15, delta_t=15, height=1.0, angle=90, pressure=101325):
        """Get the detailed indoor heat transfer coefficient according to ISO 15099.

        This is used for window U-factor calculations and all of the
        temperature_profile calculations.

        Args:
            t_kelvin (float): The average between the indoor temperature and the
                interior surface temperature. Default is 293.15K (20C).
            delta_t (float): The temperature difference between the indoor temperature
                and the interior surface temperature [C]. Default is 15C.
            height (float): An optional height for the surface in meters. Default is
                1.0 m, which is consistent with NFRC standards.
            angle (float): An angle in degrees between 0 and 180.
                0 = A horizontal surface with downward heat flow through the layer.
                90 = A vertical surface
                180 = A horizontal surface with upward heat flow through the layer.
            pressure (float): The average pressure in Pa.
                Default is 101325 Pa for standard pressure at sea level.
        """
        _conv_h = self.in_h_c(t_kelvin, delta_t, height, angle, pressure)
        _rad_h = 4 * 5.6697e-8 * self.inside_emissivity * (t_kelvin ** 3)
        return _conv_h + _rad_h

    def in_h_c(
        self, t_kelvin=293.15, delta_t=15, height=1.0, angle=90, pressure=101325
    ):
        """Get detailed indoor convective heat transfer coef. according to ISO 15099.

        This is used for window U-factor calculations and all of the
        temperature_profile calculations.

        Args:
            t_kelvin (float): The average between the indoor temperature and the
                interior surface temperature. Default is 293.15K (20C).
            delta_t (float): The temperature difference between the indoor temperature
                and the interior surface temperature [C]. Default is 15C.
            height (float): An optional height for the surface in meters. Default is
                1.0 m, which is consistent with NFRC standards.
            angle (float): An angle in degrees between 0 and 180.
                0 = A horizontal surface with downward heat flow through the layer.
                90 = A vertical surface
                180 = A horizontal surface with upward heat flow through the layer.
            pressure (float): The average pressure in Pa.
                Default is 101325 Pa for standard pressure at sea level.
        """
        gas_material = GasMaterial("AIR")
        _ray_numerator = (
            (gas_material.density_at_temperature(t_kelvin, pressure) ** 2)
            * (height ** 3)
            * 9.81
            * gas_material.specific_heat_at_temperature(t_kelvin, pressure)
            * delta_t
        )
        _ray_denominator = (
            t_kelvin
            * gas_material.viscosity_at_temperature(t_kelvin, pressure)
            * gas_material.conductivity_at_temperature(t_kelvin, pressure)
        )
        _rayleigh_h = abs(_ray_numerator / _ray_denominator)
        if angle < 15:
            nusselt = 0.13 * (_rayleigh_h ** (1 / 3))
        elif angle <= 90:
            _sin_a = math.sin(math.radians(angle))
            _rayleigh_c = 2.5e5 * ((math.exp(0.72 * angle) / _sin_a) ** (1 / 5))
            if _rayleigh_h < _rayleigh_c:
                nusselt = 0.56 * ((_rayleigh_h * _sin_a) ** (1 / 4))
            else:
                nu_1 = 0.56 * ((_rayleigh_c * _sin_a) ** (1 / 4))
                nu_2 = 0.13 * ((_rayleigh_h ** (1 / 3)) - (_rayleigh_c ** (1 / 3)))
                nusselt = nu_1 + nu_2
        elif angle <= 179:
            _sin_a = math.sin(math.radians(angle))
            nusselt = 0.56 * ((_rayleigh_h * _sin_a) ** (1 / 4))
        else:
            nusselt = 0.58 * (_rayleigh_h ** (1 / 5))
        _conv_h = nusselt * (
            gas_material.conductivity_at_temperature(t_kelvin, pressure) / height
        )
        return _conv_h

    @property
    def outside_emissivity(self):
        """Get the hemispherical emissivity of the outside face of the construction."""
        return self.Layers[0].Material.ThermalEmittance

    @property
    def inside_emissivity(self):
        """Get the emissivity of the inside face of the construction [-]."""
        return self.Layers[-1].Material.ThermalEmittance

    @property
    def u_factor(self):
        """Get the overall heat transfer coefficient (including air films) W/(m2⋅K)."""
        return 1 / self.r_factor

    def __copy__(self):
        """Create a copy of self."""
        return self.__class__(Name=self.Name, Layers=self.Layers)

    def __eq__(self, other):
        """Assert self is equivalent to other."""
        return isinstance(other, LayeredConstruction) and all(
            [self.Layers == other.Layers]
        )
