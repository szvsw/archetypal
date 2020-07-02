import pytest
from path import Path

from archetypal import (
    IDF,
    parallel_process,
    get_eplus_dirs,
    settings,
    EnergyPlusVersionError,
    EnergyPlusProcessError,
)


class TestIDF:
    @pytest.fixture()
    def idf_model(self, config):
        """An IDF model. Yields both the idf and the sql"""
        file = r"tests\input_data\necb\NECB 2011-SmallOffice-NECB HDD Method-CAN_PQ_Montreal.Intl.AP.716270_CWEC.epw.idf"
        w = "tests/input_data/CAN_PQ_Montreal.Intl.AP.716270_CWEC.epw"
        yield IDF(file, epw=w)

    @pytest.fixture()
    def shoebox_model(self, config):
        """An IDF model. Yields both the idf and the sql"""
        file = r"tests\input_data\umi_samples\B_Off_0.idf"
        w = "tests/input_data/CAN_PQ_Montreal.Intl.AP.716270_CWEC.epw"
        yield IDF(file, epw=w)

    def test_parallel_process(self, config):
        w = "tests/input_data/CAN_PQ_Montreal.Intl.AP.716270_CWEC.epw"
        files = {
            i: {"idfname": file.expand(), "epw": w}
            for i, file in enumerate(Path("tests/input_data/necb").files("*.idf")[0:3])
        }
        idfs = parallel_process(files, IDF, use_kwargs=True)

        assert not any(isinstance(a, Exception) for a in idfs.values())

    def test_processed_results(self, idf_model):
        assert idf_model.processed_results

    def test_processed_results_fail(self, shoebox_model):
        assert len(shoebox_model.processed_results) == 1

    def test_partition_ratio(self, idf_model):
        assert idf_model.partition_ratio

    def test_space_cooling_profile(self, idf_model):
        assert not idf_model.space_cooling_profile().empty

    def test_space_heating_profile(self, idf_model):
        assert not idf_model.space_heating_profile().empty

    def test_dhw_profile(self, idf_model):
        assert not idf_model.service_water_heating_profile().empty

    def test_wwr(self, idf_model):
        assert not idf_model.wwr(round_to=10).empty

    @pytest.fixture()
    def natvent(self):
        """An old file that needs upgrade"""
        w = "tests/input_data/CAN_PQ_Montreal.Intl.AP.716270_CWEC.epw"
        yield IDF(
            "tests/input_data/problematic/nat_ventilation_SAMPLE0.idf",
            epw=w,
            ep_version="9-2-0",
        )

    @pytest.fixture()
    def FiveZoneNightVent1(self):
        """An old file that needs upgrade"""
        w = "tests/input_data/CAN_PQ_Montreal.Intl.AP.716270_CWEC.epw"
        idfname = (
            get_eplus_dirs(settings.ep_version) / "ExampleFiles" / "5ZoneNightVent1.idf"
        )
        yield IDF(idfname, epw=w)

    @pytest.fixture()
    def natvent_v9_1_0(self):
        """An old file that needs upgrade"""
        w = "tests/input_data/CAN_PQ_Montreal.Intl.AP.716270_CWEC.epw"
        yield IDF(
            "tests/input_data/problematic/nat_ventilation_SAMPLE0.idf",
            epw=w,
            ep_version="9-1-0",
        )

    @pytest.fixture()
    def wont_transition_correctly(self):
        file = (
            "tests/input_data/problematic/RefBldgLargeOfficeNew2004_v1.4_7"
            ".2_5A_USA_IL_CHICAGO-OHARE.idf"
        )
        wf = "tests/input_data/CAN_PQ_Montreal.Intl.AP.716270_CWEC.epw"
        yield IDF(file, epw=wf, ep_version="8.9.0")

    def test_wrong_epversion(self, config):
        file = (
            "tests/input_data/problematic/RefBldgLargeOfficeNew2004_v1.4_7"
            ".2_5A_USA_IL_CHICAGO-OHARE.idf"
        )
        wf = "tests/input_data/CAN_PQ_Montreal.Intl.AP.716270_CWEC.epw"
        with pytest.raises(ValueError):
            IDF(file, epw=wf, ep_version="7-3-0")

    def test_transition_error(self, config, wont_transition_correctly):
        with pytest.raises(EnergyPlusProcessError):
            assert wont_transition_correctly.simulate(ep_version="8.9.0")

    def test_specific_version(self, config, natvent_v9_1_0):
        assert natvent_v9_1_0.idd_version == (9, 1, 0)

    def test_specific_version_error_simulate(self, config, natvent_v9_1_0):
        with pytest.raises(EnergyPlusVersionError):
            natvent_v9_1_0.simulate()

    def test_load_old(self, config, natvent, FiveZoneNightVent1):
        assert natvent.idd_version == (9, 2, 0)
        assert FiveZoneNightVent1.idd_version == (9, 2, 0)

    def test_five(self, config, FiveZoneNightVent1):
        assert FiveZoneNightVent1

    def test_natvent(self, config, natvent):
        assert natvent

    @pytest.mark.parametrize(
        "archetype, area",
        [
            ("FullServiceRestaurant", 511),
            pytest.param(
                "Hospital",
                22422,
                marks=pytest.mark.xfail(reason="Difference cannot be explained"),
            ),
            ("LargeHotel", 11345),
            ("LargeOffice", 46320),
            ("MediumOffice", 4982),
            ("MidriseApartment", 3135),
            ("Outpatient", 3804),
            ("PrimarySchool", 6871),
            ("QuickServiceRestaurant", 232),
            ("SecondarySchool", 19592),
            ("SmallHotel", 4013),
            ("SmallOffice", 511),
            pytest.param(
                "RetailStandalone",
                2319,
                marks=pytest.mark.xfail(reason="Difference cannot be explained"),
            ),
            ("RetailStripmall", 2090),
            pytest.param(
                "Supermarket",
                4181,
                marks=pytest.mark.skip(
                    "Supermarket " "missing from " "BTAP " "database"
                ),
            ),
            ("Warehouse", 4835),
        ],
    )
    def test_area(self, archetype, area, config):
        """Test the conditioned_area property against published values
        desired values taken from https://github.com/canmet-energy/btap"""
        import numpy as np

        idf_file = Path("tests/input_data/necb").files(f"*{archetype}*.idf")[0]
        w = "tests/input_data/CAN_PQ_Montreal.Intl.AP.716270_CWEC.epw"
        idf = IDF(idf_file, epw=w, prep_outputs=False)

        np.testing.assert_almost_equal(
            actual=idf.area_conditioned, desired=area, decimal=0
        )
