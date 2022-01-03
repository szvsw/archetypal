"""archetypal OpaqueMaterial."""

import collections
from typing import Optional

from eppy.bunch_subclass import EpBunch
from pydantic import Field, validator
from validator_collection import validators

from archetypal.template.materials import GasMaterial
from archetypal.template.materials.material_base import MaterialBase, ROUGHNESS
from archetypal.utils import log


class OpaqueMaterial(MaterialBase):
    """Use this component to create a custom opaque material.

    .. image:: ../images/template/materials-opaque.png
    """

    Conductivity: float = Field(..., description="")
    Density: float = Field(..., description="")
    Roughness: ROUGHNESS = Field(
        ROUGHNESS.Rough,
        description="A text value that indicated the roughness of your material. This "
        "can be either 'VeryRough', 'Rough', 'MediumRough', 'MediumSmooth', "
        "'Smooth', and 'VerySmooth'. The default is set to 'Rough'.",
    )
    SolarAbsorptance: float = Field(
        ...,
        description="An number between 0 and 1 that represents the absorptance of "
        "solar radiation by the material. The default is set to 0.7, "
        "which is common "
        "for most non-metallic materials.",
        ge=0,
        le=1,
    )
    SpecificHeat: float = Field(
        ...,
        description="A number representing the specific heat capacity of the material "
        "in J/kg-K. This is essentially the number of joules needed to raise one kg "
        "of the material by 1 degree Kelvin. Only values of specific heat of 100 or "
        "larger are allowed. Typical ranges are from 800 to 2000 J/(kg-K).",
        ge=100,
    )
    ThermalEmittance: float = Field(
        ...,
        description="An number between 0 and 1 that represents the thermal "
        "absorptance of the material. The default is set to 0.9, which is "
        "common for "
        "most non-metallic materials. For long wavelength radiant "
        "exchange, thermal "
        "emissivity and thermal emittance are equal to thermal "
        "absorptance.",
        ge=0,
        le=1,
    )
    VisibleAbsorptance: Optional[float] = Field(
        0.7,
        description="An number between 0 and 1 that represents the absorptance of "
        "visible light by the material. The default is set to 0.7, "
        "which is common "
        "for most non-metallic materials.",
        ge=0,
        le=1,
    )
    MoistureDiffusionResistance: float = Field(
        ...,
        description="The factor by which the vapor diffusion in the material is "
        "impeded, as compared to diffusion in stagnant air [%].",
        ge=0,
    )

    @validator("SolarAbsorptance")
    def validate_solar_absorptance(cls, value):
        if value == "":
            value = 0.7
        return value

    @validator("ThermalEmittance")
    def validate_thermal_emittance(cls, value):
        if value == "":
            value = 0.9
        return value

    @validator("VisibleAbsorptance")
    def validate_visible_absorptance(cls, value):
        if value == "":
            value = 0.7
        return value

    @classmethod
    def generic(cls, **kwargs):
        """Return a generic material based on properties of plaster board.

        Args:
            **kwargs: keywords passed to UmiBase constructor.
        """
        return cls(
            Conductivity=0.16,
            SpecificHeat=1090,
            Density=800,
            Name="GP01 GYPSUM",
            Roughness="Smooth",
            SolarAbsorptance=0.7,
            ThermalEmittance=0.9,
            VisibleAbsorptance=0.5,
            DataSource="ASHRAE 90.1-2007",
            MoistureDiffusionResistance=8.3,
            **kwargs,
        )

    def combine(self, other, weights=None, allow_duplicates=False):
        """Combine two OpaqueMaterial objects.

        Args:
            weights (list-like, optional): A list-like object of len 2. If None,
                the density of the OpaqueMaterial of each objects is used as
                a weighting factor.
            other (OpaqueMaterial): The other OpaqueMaterial object the
                combine with.

        Returns:
            OpaqueMaterial: A new combined object made of self + other.
        """
        # Check if other is the same type as self
        if not isinstance(other, self.__class__):
            msg = "Cannot combine %s with %s" % (
                self.__class__.__name__,
                other.__class__.__name__,
            )
            raise NotImplementedError(msg)

        # Check if other is not the same as self
        if self == other:
            return self

        if not weights:
            log(
                'using OpaqueMaterial density as weighting factor in "{}" '
                "combine.".format(self.__class__.__name__)
            )
            weights = [self.Density, other.Density]

        meta = self._get_predecessors_meta(other)
        new_obj = OpaqueMaterial(
            **meta,
            Conductivity=self.float_mean(other, "Conductivity", weights),
            Roughness=self._str_mean(other, attr="Roughness", append=False),
            SolarAbsorptance=self.float_mean(other, "SolarAbsorptance", weights),
            SpecificHeat=self.float_mean(other, "SpecificHeat"),
            ThermalEmittance=self.float_mean(other, "ThermalEmittance", weights),
            VisibleAbsorptance=self.float_mean(other, "VisibleAbsorptance", weights),
            TransportCarbon=self.float_mean(other, "TransportCarbon", weights),
            TransportDistance=self.float_mean(other, "TransportDistance", weights),
            TransportEnergy=self.float_mean(other, "TransportEnergy", weights),
            SubstitutionRatePattern=self.float_mean(
                other, "SubstitutionRatePattern", weights=None
            ),
            SubstitutionTimestep=self.float_mean(
                other, "SubstitutionTimestep", weights
            ),
            Cost=self.float_mean(other, "Cost", weights),
            Density=self.float_mean(other, "Density", weights),
            EmbodiedCarbon=self.float_mean(other, "EmbodiedCarbon", weights),
            EmbodiedEnergy=self.float_mean(other, "EmbodiedEnergy", weights),
            MoistureDiffusionResistance=self.float_mean(
                other, "MoistureDiffusionResistance", weights
            ),
        )
        new_obj.predecessors.update(self.predecessors + other.predecessors)
        return new_obj

    def to_ref(self):
        """Return a ref pointer to self."""
        pass

    def to_dict(self):
        """Return OpaqueMaterial dictionary representation."""
        self.validate()  # Validate object before trying to get json format

        data_dict = collections.OrderedDict()

        data_dict["$id"] = str(self.id)
        data_dict["MoistureDiffusionResistance"] = self.MoistureDiffusionResistance
        data_dict["Roughness"] = self.Roughness
        data_dict["SolarAbsorptance"] = self.SolarAbsorptance
        data_dict["SpecificHeat"] = self.SpecificHeat
        data_dict["ThermalEmittance"] = self.ThermalEmittance
        data_dict["VisibleAbsorptance"] = self.VisibleAbsorptance
        data_dict["Conductivity"] = self.Conductivity
        data_dict["Cost"] = self.Cost
        data_dict["Density"] = self.Density
        data_dict["EmbodiedCarbon"] = self.EmbodiedCarbon
        data_dict["EmbodiedEnergy"] = self.EmbodiedEnergy
        data_dict["SubstitutionRatePattern"] = self.SubstitutionRatePattern
        data_dict["SubstitutionTimestep"] = self.SubstitutionTimestep
        data_dict["TransportCarbon"] = self.TransportCarbon
        data_dict["TransportDistance"] = self.TransportDistance
        data_dict["TransportEnergy"] = self.TransportEnergy
        data_dict["Category"] = self.Category
        data_dict["Comments"] = validators.string(self.Comments, allow_empty=True)
        data_dict["DataSource"] = self.DataSource
        data_dict["Name"] = self.Name

        return data_dict

    @classmethod
    def from_dict(cls, data, **kwargs):
        """Create an OpaqueMaterial from a dictionary.

        Args:
            data (dict): The python dictionary.
            **kwargs: keywords passed to MaterialBase constructor.

        .. code-block:: python

            {
                "$id": "1",
                "MoistureDiffusionResistance": 50.0,
                "Roughness": "Rough",
                "SolarAbsorptance": 0.7,
                "SpecificHeat": 920.0,
                "ThermalEmittance": 0.9,
                "VisibleAbsorptance": 0.7,
                "Conductivity": 0.85,
                "Cost": 0.0,
                "Density": 2000,
                "EmbodiedCarbon": 0.45,
                "EmbodiedEnergy": 0.0,
                "SubstitutionRatePattern": [
                 1.0
                ],
                "SubstitutionTimestep": 20.0,
                "TransportCarbon": 0.0,
                "TransportDistance": 0.0,
                "TransportEnergy": 0.0,
                "Category": "Uncategorized",
                "Comments": "",
                "DataSource": null,
                "Name": "Concrete"
            }
        """
        _id = data.pop("$id")
        return cls(id=_id, **data, **kwargs)

    @classmethod
    def from_epbunch(cls, epbunch, **kwargs):
        """Create an OpaqueMaterial from an EpBunch.

        Note that "Material", "Material:NoMAss" and "Material:AirGap" objects are
        supported.

        Hint:
            (From EnergyPlus Manual): When a user enters such a “no mass”
            material into EnergyPlus, internally the properties of this layer
            are converted to approximate the properties of air (density,
            specific heat, and conductivity) with the thickness adjusted to
            maintain the user’s desired R-Value. This allowed such layers to be
            handled internally in the same way as other layers without any
            additional changes to the code. This solution was deemed accurate
            enough as air has very little thermal mass and it made the coding of
            the state space method simpler.

            For Material:AirGap, a similar strategy is used, with the
            exception that solar properties (solar and visible absorptance and
            emittance) are assumed null.

        Args:
            epbunch (EpBunch): EP-Construction object
            **kwargs:
        """
        if epbunch.key.upper() == "MATERIAL":
            return cls(
                Conductivity=epbunch.Conductivity,
                Density=epbunch.Density,
                Roughness=epbunch.Roughness,
                SolarAbsorptance=epbunch.Solar_Absorptance,
                SpecificHeat=epbunch.Specific_Heat,
                ThermalEmittance=epbunch.Thermal_Absorptance,
                VisibleAbsorptance=epbunch.Visible_Absorptance,
                Name=epbunch.Name,
                **kwargs,
            )
        elif epbunch.key.upper() == "MATERIAL:NOMASS":
            # Assume properties of air.
            return cls(
                Conductivity=0.02436,  # W/mK, dry air at 0 °C and 100 kPa
                Density=1.2754,  # dry air at 0 °C and 100 kPa.
                Roughness=epbunch.Roughness,
                SolarAbsorptance=epbunch.Solar_Absorptance,
                SpecificHeat=100.5,  # J/kg-K, dry air at 0 °C and 100 kPa
                ThermalEmittance=epbunch.Thermal_Absorptance,
                VisibleAbsorptance=epbunch.Visible_Absorptance,
                Name=epbunch.Name,
                **kwargs,
            )
        elif epbunch.key.upper() == "MATERIAL:AIRGAP":
            gas_prop = {
                obj.Name.upper(): obj.mapping()
                for obj in [GasMaterial(gas_name) for gas_name in GasMaterial._GASTYPES]
            }
            for gasname, properties in gas_prop.items():
                if gasname.lower() in epbunch.Name.lower():
                    thickness = properties["Conductivity"] * epbunch.Thermal_Resistance
                    properties.pop("Name")
                    return cls(
                        Name=epbunch.Name,
                        Thickness=thickness,
                        SpecificHeat=100.5,
                        **properties,
                    )
                else:
                    thickness = (
                        gas_prop["AIR"]["Conductivity"] * epbunch.Thermal_Resistance
                    )
                    properties.pop("Name")
                    return cls(
                        Name=epbunch.Name,
                        Thickness=thickness,
                        SpecificHeat=100.5,
                        **gas_prop["AIR"],
                    )
        else:
            raise NotImplementedError(
                "Material '{}' of type '{}' is not yet "
                "supported. Please contact package "
                "authors".format(epbunch.Name, epbunch.key)
            )

    def to_epbunch(self, idf, thickness) -> EpBunch:
        """Convert self to an EpBunch given an idf model and a thickness.

        Args:
            idf (IDF): An IDF model.
            thickness (float): the thickness of the material.

        .. code-block:: python

            MATERIAL,
                ,                         !- Name
                ,                         !- Roughness
                ,                         !- Thickness
                ,                         !- Conductivity
                ,                         !- Density
                ,                         !- Specific Heat
                0.9,                      !- Thermal Absorptance
                0.7,                      !- Solar Absorptance
                0.7;                      !- Visible Absorptance

        Returns:
            EpBunch: The EpBunch object added to the idf model.
        """
        return idf.newidfobject(
            "MATERIAL",
            Name=self.Name,
            Roughness=self.Roughness,
            Thickness=thickness,
            Conductivity=self.Conductivity,
            Density=self.Density,
            Specific_Heat=self.SpecificHeat,
            Thermal_Absorptance=self.ThermalEmittance,
            Solar_Absorptance=self.SolarAbsorptance,
            Visible_Absorptance=self.VisibleAbsorptance,
        )

    def mapping(self, validate=True):
        """Get a dict based on the object properties, useful for dict repr.

        Args:
            validate (bool): If True, try to validate object before returning the
                mapping.
        """
        if validate:
            self.validate()

        return dict(
            MoistureDiffusionResistance=self.MoistureDiffusionResistance,
            Roughness=self.Roughness,
            SolarAbsorptance=self.SolarAbsorptance,
            SpecificHeat=self.SpecificHeat,
            ThermalEmittance=self.ThermalEmittance,
            VisibleAbsorptance=self.VisibleAbsorptance,
            Conductivity=self.Conductivity,
            Cost=self.Cost,
            Density=self.Density,
            EmbodiedCarbon=self.EmbodiedCarbon,
            EmbodiedEnergy=self.EmbodiedEnergy,
            SubstitutionRatePattern=self.SubstitutionRatePattern,
            SubstitutionTimestep=self.SubstitutionTimestep,
            TransportCarbon=self.TransportCarbon,
            TransportDistance=self.TransportDistance,
            TransportEnergy=self.TransportEnergy,
            Category=self.Category,
            Comments=self.Comments,
            DataSource=self.DataSource,
            Name=self.Name,
        )

    def duplicate(self):
        """Get copy of self."""
        return self.__copy__()

    def __add__(self, other):
        """Overload + to implement self.combine.

        Args:
            other (OpaqueMaterial):
        """
        return self.combine(other)

    def __hash__(self):
        """Return the hash value of self."""
        return hash(
            (
                self.__class__.__name__,
                getattr(self, "Name", None),
            )
        )

    def __eq__(self, other):
        """Assert self is equivalent to other."""
        if not isinstance(other, OpaqueMaterial):
            return NotImplemented
        else:
            return self.__key__() == other.__key__()

    def __key__(self):
        """Get a tuple of attributes. Useful for hashing and comparing."""
        return (
            self.Conductivity,
            self.SpecificHeat,
            self.SolarAbsorptance,
            self.ThermalEmittance,
            self.VisibleAbsorptance,
            self.Roughness,
            self.Cost,
            self.Density,
            self.MoistureDiffusionResistance,
            self.EmbodiedCarbon,
            self.EmbodiedEnergy,
            self.TransportCarbon,
            self.TransportDistance,
            self.TransportEnergy,
            self.SubstitutionRatePattern,
            self.SubstitutionTimestep,
        )

    def __copy__(self):
        """Create a copy of self."""
        new_om = self.__class__(**self.mapping())
        return new_om
