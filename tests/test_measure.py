"""Test measures module."""
import pytest

from archetypal.template.measures import (
    SetFacadeConstructionThermalResistanceToEnergyStar,
    EnergyStarUpgrade,
)


@pytest.fixture(scope="function")
def umi_library():
    from archetypal import UmiTemplateLibrary

    umi = UmiTemplateLibrary.open(
        "tests/input_data/umi_samples/BostonTemplateLibrary_nodup.json"
    )
    yield umi
    del umi


class TestMeasure:
    def test_apply_measure_to_single_building_template(self, umi_library):
        """Test applying measure only to a specific building template."""
        building_template = umi_library.BuildingTemplates[0]

        assert umi_library.BuildingTemplates[0].Core.Loads.LightingPowerDensity == 12.0

        EnergyStarUpgrade().apply_measure_to_template(building_template)

        assert umi_library.BuildingTemplates[0].Core.Loads.LightingPowerDensity == 8.07
        assert umi_library.BuildingTemplates[1].Core.Loads.LightingPowerDensity == 16.0

    def test_apply_measure_to_whole_library(self, umi_library):
        """Test applying measure to whole template library."""
        assert umi_library.BuildingTemplates[0].Core.Loads.LightingPowerDensity == 12.0

        # apply the measure
        EnergyStarUpgrade().apply_measure_to_whole_library(umi_library)

        # Assert the value has changed for all ZoneLoads objects.
        for zone_loads in umi_library.ZoneLoads:
            assert zone_loads.LightingPowerDensity == 8.07

        SetFacadeConstructionThermalResistanceToEnergyStar().apply_measure_to_whole_library(
            umi_library
        )
