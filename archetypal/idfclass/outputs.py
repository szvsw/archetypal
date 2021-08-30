from typing import Iterable


class Outputs:
    """Handles preparation of EnergyPlus outputs. Different instance methods
    allow to chain methods together and to add predefined bundles of outputs in
    one go.

    Examples:
        >>> from archetypal import IDF
        >>> idf = IDF(prep_outputs=False)  # True be default
        >>> idf.outputs.add_output_control().add_umi_outputs(
        >>> ).add_profile_gas_elect_outputs().apply()
    """

    REPORTING_FREQUENCIES = ("Annual", "Monthly", "Daily", "Hourly", "Timestep")

    def __init__(
        self,
        idf,
        variables=None,
        meters=None,
        outputs=None,
        reporting_frequency="Hourly",
        include_sqlite=True,
        include_html=True,
        unit_conversion=None,
    ):
        """Initialize an outputs object.

        Args:
            idf (IDF): the IDF object for wich this outputs object is created.
        """
        self.idf = idf
        self.output_variables = set(
            a.Variable_Name for a in idf.idfobjects["Output:Variable".upper()]
        )
        self.output_meters = set(
            a.Key_Name for a in idf.idfobjects["Output:Meter".upper()]
        )
        # existing_ouputs = []
        # for key in idf.getiddgroupdict()["Output Reporting"]:
        #     if key not in ["Output:Variable", "Output:Meter"]:
        #         existing_ouputs.extend(idf.idfobjects[key.upper()].to_dict())
        # self.other_outputs = existing_ouputs
        self.other_outputs = outputs

        self.output_variables += tuple(variables or ())
        self.output_meters += tuple(meters or ())
        self.other_outputs += tuple(outputs or ())
        self.reporting_frequency = reporting_frequency
        self.include_sqlite = include_sqlite
        self.include_html = include_html
        self.unit_conversion = unit_conversion

    @property
    def unit_conversion(self):
        return self._unit_conversion

    @unit_conversion.setter
    def unit_conversion(self, value):
        if not value:
            value = "None"
        assert value in ["None", "JtoKWH", "JtoMJ", "JtoGJ", "InchPound"]
        for obj in self.idf.idfobjects["OutputControl:Table:Style".upper()]:
            obj.Unit_Conversion = value
        self._unit_conversion = value

    @property
    def include_sqlite(self):
        """Get or set a boolean for whether a SQLite report should be generated."""
        return self._include_sqlite

    @include_sqlite.setter
    def include_sqlite(self, value):
        value = bool(value)
        if value:
            self.add_sql().apply()
        else:
            # if False, try to remove sql, if exists.
            for obj in self.idf.idfobjects["Output:SQLite".upper()]:
                self.idf.removeidfobject(obj)
        self._include_sqlite = value

    @property
    def include_html(self):
        """Get or set a boolean for whether an HTML report should be generated."""
        return self._include_html

    @include_html.setter
    def include_html(self, value):
        value = bool(value)
        if value:
            self.add_output_control().apply()
        else:
            # if False, try to remove sql, if exists.
            for obj in self.idf.idfobjects["OutputControl:Table:Style".upper()]:
                obj.Column_Separator = "Comma"
        self._include_html = value

    @property
    def output_variables(self) -> tuple:
        """Get or set a tuple of EnergyPlus simulation output variables."""
        return tuple(sorted(self._output_variables))

    @output_variables.setter
    def output_variables(self, value):
        if value is not None:
            assert not isinstance(
                value, (str, bytes)
            ), f"Expected list or tuple. Got {type(value)}."
            values = []
            for output in value:
                values.append(str(output))
            value = set(values)
        else:
            value = set()
        self._output_variables = value

    @property
    def output_meters(self):
        """Get or set a tuple of EnergyPlus simulation output meters."""
        return tuple(sorted(self._output_meters))

    @output_meters.setter
    def output_meters(self, value):
        if value is not None:
            assert not isinstance(
                value, (str, bytes)
            ), f"Expected list or tuple. Got {type(value)}."
            values = []
            for output in value:
                values.append(str(output))
            value = set(values)
        else:
            value = set()
        self._output_meters = value

    @property
    def other_outputs(self):
        """Get or set a list of outputs."""
        return self._other_outputs

    @other_outputs.setter
    def other_outputs(self, value):
        if value is not None:
            assert all(
                isinstance(item, dict) for item in value
            ), f"Expected list of dict. Got {type(value)}."
            values = []
            for output in value:
                values.append(output)
            value = values
        else:
            value = []
        self._other_outputs = value

    @property
    def reporting_frequency(self):
        """Get or set the reporting frequency of outputs.

        Choose from the following:

        * Annual
        * Monthly
        * Daily
        * Hourly
        * Timestep
        """
        return self._reporting_frequency

    @reporting_frequency.setter
    def reporting_frequency(self, value):
        value = value.title()
        assert value in self.REPORTING_FREQUENCIES, (
            f"reporting_frequency {value} is not recognized.\nChoose from the "
            f"following:\n{self.REPORTING_FREQUENCIES}"
        )
        self._reporting_frequency = value

    def add_custom(self, outputs):
        """Add custom-defined outputs as a list of objects.

        Examples:
            >>> outputs = IDF().outputs
            >>> to_add = dict(
            >>>       key= "OUTPUT:METER",
            >>>       Key_Name="Electricity:Facility",
            >>>       Reporting_Frequency="hourly",
            >>> )
            >>> outputs.add_custom([to_add]).apply()

        Args:
            outputs (list, bool): Pass a list of ep-objects defined as dictionary. See
                examples. If a bool, ignored.

        Returns:
            Outputs: self
        """
        assert isinstance(outputs, Iterable), "outputs must be some sort of iterable"
        for output in outputs:
            if "meter" in output["key"].lower():
                self._output_meters.add(output)
            elif "variable" in output["key"].lower():
                self._output_variables.add(output)
            else:
                self._other_outputs.append(output)
        return self

    def add_basics(self):
        """Adds the summary report and the sql file to the idf outputs"""
        return (
            self.add_summary_report()
            .add_output_control()
            .add_schedules()
            .add_meter_variables()
        )

    def add_schedules(self):
        """Adds Schedules object"""
        outputs = [{"key": "Output:Schedules".upper(), **dict(Key_Field="Hourly")}]
        for output in outputs:
            self._other_outputs.append(output)
        return self

    def add_meter_variables(self, format="IDF"):
        """Generate .mdd file at end of simulation. This file (from the
        Output:VariableDictionary, regular; and Output:VariableDictionary,
        IDF; commands) shows all the report meters along with their “availability”
        for the current input file. A user must first run the simulation (at least
        semi-successfully) before the available output meters are known. This output
        file is available in two flavors: regular (listed as they are in the Input
        Output Reference) and IDF (ready to be copied and pasted into your Input File).

        Args:
            format (str): Choices are "IDF" and "regul

        Returns:
            Outputs: self
        """
        outputs = [dict(key="Output:VariableDictionary".upper(), Key_Field=format)]
        for output in outputs:
            self._other_outputs.append(output)
        return self

    def add_summary_report(self, summary="AllSummary"):
        """Adds the Output:Table:SummaryReports object.

        Args:
            summary (str): Choices are AllSummary, AllMonthly,
                AllSummaryAndMonthly, AllSummaryAndSizingPeriod,
                AllSummaryMonthlyAndSizingPeriod,
                AnnualBuildingUtilityPerformanceSummary,
                InputVerificationandResultsSummary,
                SourceEnergyEndUseComponentsSummary, ClimaticDataSummary,
                EnvelopeSummary, SurfaceShadowingSummary, ShadingSummary,
                LightingSummary, EquipmentSummary, HVACSizingSummary,
                ComponentSizingSummary, CoilSizingDetails, OutdoorAirSummary,
                SystemSummary, AdaptiveComfortSummary, SensibleHeatGainSummary,
                Standard62.1Summary, EnergyMeters, InitializationSummary,
                LEEDSummary, TariffReport, EconomicResultSummary,
                ComponentCostEconomicsSummary, LifeCycleCostReport,
                HeatEmissionsSummary,
        Returns:
            Outputs: self
        """
        outputs = [
            {
                "key": "Output:Table:SummaryReports".upper(),
                **dict(Report_1_Name=summary),
            }
        ]
        for output in outputs:
            self._other_outputs.append(output)
        return self

    def add_sql(self, sql_output_style="SimpleAndTabular"):
        """Adds the `Output:SQLite` object. This object will produce an sql file
        that contains the simulation results in a database format. See
        `eplusout.sql
        <https://bigladdersoftware.com/epx/docs/9-2/output-details-and
        -examples/eplusout-sql.html#eplusout.sql>`_ for more details.

        Args:
            sql_output_style (str): The *Simple* option will include all of the
                predefined database tables as well as time series related data.
                Using the *SimpleAndTabular* choice adds database tables related
                to the tabular reports that are already output by EnergyPlus in
                other formats.
        Returns:
            Outputs: self
        """
        outputs = [
            {"key": "Output:SQLite".upper(), **dict(Option_Type=sql_output_style)}
        ]

        for output in outputs:
            self._other_outputs.append(output)
        return self

    def add_output_control(self, output_control_table_style="CommaAndHTML"):
        """Sets the `OutputControl:Table:Style` object.

        Args:
            output_control_table_style (str): Choices are: Comma, Tab, Fixed,
                HTML, XML, CommaAndHTML, TabAndHTML, XMLAndHTML, All
        Returns:
            Outputs: self
        """
        assert output_control_table_style in [
            "Comma",
            "Tab",
            "Fixed",
            "HTML",
            "XML",
            "CommaAndHTML",
            "TabAndHTML",
            "XMLAndHTML",
            "All",
        ]
        outputs = [
            {
                "key": "OutputControl:Table:Style".upper(),
                **dict(Column_Separator=output_control_table_style),
            }
        ]

        for output in outputs:
            self._other_outputs.append(output)
        return self

    def add_umi_template_outputs(self):
        """Adds the necessary outputs in order to create an UMI template."""
        # list the outputs here
        variables = [
            "Air System Outdoor Air Minimum Flow Fraction",
            "Air System Total Cooling Energy",
            "Air System Total Heating Energy",
            "Heat Exchanger Latent Effectiveness",
            "Heat Exchanger Sensible Effectiveness",
            "Heat Exchanger Total Heating Rate",
            "Water Heater Heating Energy",
            "Zone Ideal Loads Zone Total Cooling Energy",
            "Zone Ideal Loads Zone Total Heating Energy",
            "Zone Thermostat Cooling Setpoint Temperature",
            "Zone Thermostat Heating Setpoint Temperature",
        ]
        for output in variables:
            self._output_variables.add(output)

        meters = [
            "Baseboard:EnergyTransfer",
            "Cooling:DistrictCooling",
            "Cooling:Electricity",
            "Cooling:Electricity",
            "Cooling:EnergyTransfer",
            "Cooling:Gas",
            "CoolingCoils:EnergyTransfer",
            "Fans:Electricity",
            "HeatRejection:Electricity",
            "HeatRejection:EnergyTransfer",
            "Heating:DistrictHeating",
            "Heating:Electricity",
            "Heating:EnergyTransfer",
            "Heating:Gas",
            "HeatingCoils:EnergyTransfer",
            "Pumps:Electricity",
            "Refrigeration:Electricity",
            "Refrigeration:EnergyTransfer",
            "WaterSystems:EnergyTransfer",
        ]
        for meter in meters:
            self._output_meters.add(meter)
        return self

    def add_dxf(self):
        outputs = [
            {
                "key": "Output:Surfaces:Drawing".upper(),
                **dict(Report_Type="DXF", Report_Specifications_1="ThickPolyline"),
            }
        ]
        for output in outputs:
            self._other_outputs.append(output)
        return self

    def add_umi_outputs(self):
        """Adds the necessary outputs in order to return the same energy profile
        as in UMI.
        """
        # list the outputs here
        outputs = [
            "Air System Total Heating Energy",
            "Air System Total Cooling Energy",
            "Zone Ideal Loads Zone Total Cooling Energy",
            "Zone Ideal Loads Zone Total Heating Energy",
            "Water Heater Heating Energy",
        ]
        for output in outputs:
            self._output_variables.add(output)
        return self

    def add_profile_gas_elect_outputs(self):
        """Adds the following meters: Electricity:Facility, Gas:Facility,
        WaterSystems:Electricity, Heating:Electricity, Cooling:Electricity
        """
        # list the outputs here
        outputs = [
            "Electricity:Facility",
            "Gas:Facility",
            "WaterSystems:Electricity",
            "Heating:Electricity",
            "Cooling:Electricity",
        ]
        for output in outputs:
            self._output_meters.add(output)
        return self

    def add_hvac_energy_use(self):
        """Add outputs for HVAC energy use when detailed systems are assigned.

        This includes a range of outputs for different pieces of equipment,
        which is meant to catch all energy-consuming parts of a system.
        (eg. chillers, boilers, coils, humidifiers, fans, pumps).
        """
        outputs = [
            "Baseboard Electricity Energy",
            "Boiler NaturalGas Energy",
            "Chiller Electricity Energy",
            "Chiller Heater System Cooling Electricity Energy",
            "Chiller Heater System Heating Electricity Energy",
            "Cooling Coil Electricity Energy",
            "Cooling Tower Fan Electricity Energy",
            "District Cooling Chilled Water Energy",
            "District Heating Hot Water Energy",
            "Evaporative Cooler Electricity Energy",
            "Fan Electricity Energy",
            "Heating Coil Electricity Energy",
            "Heating Coil NaturalGas Energy",
            "Heating Coil Total Heating Energy",
            "Hot_Water_Loop_Central_Air_Source_Heat_Pump Electricity Consumption",
            "Humidifier Electricity Energy",
            "Pump Electricity Energy",
            "VRF Heat Pump Cooling Electricity Energy",
            "VRF Heat Pump Crankcase Heater Electricity Energy",
            "VRF Heat Pump Defrost Electricity Energy",
            "VRF Heat Pump Heating Electricity Energy",
            "Zone VRF Air Terminal Cooling Electricity Energy",
            "Zone VRF Air Terminal Heating Electricity Energy",
        ]
        for output in outputs:
            self._output_variables.add(output)

    def apply(self):
        """Applies the outputs to the idf model. Modifies the model by calling
        :meth:`~archetypal.idfclass.idf.IDF.newidfobject`"""
        for output in self.output_variables:
            self.idf.newidfobject(
                key="Output:Variable".upper(),
                **dict(
                    Variable_Name=output, Reporting_Frequency=self.reporting_frequency
                ),
            )
        for meter in self.output_meters:
            self.idf.newidfobject(
                key="Output:Meter".upper(),
                **dict(Key_Name=meter, Reporting_Frequency=self.reporting_frequency),
            )
        for output in self.other_outputs:
            key = output.pop("key", None)
            if key:
                output["key"] = key.upper()
            self.idf.newidfobject(**output)
        return self

    def __repr__(self):
        variables = "OutputVariables:\n {}".format("\n ".join(self.output_variables))
        meters = "OutputMeters:\n {}".format("\n ".join(self.output_meters))
        outputs = "Outputs:\n {}".format(
            "\n ".join((a["key"] for a in self.other_outputs))
        )
        return "\n".join([variables, meters, outputs])
