# This file is part of Pynguin.
#
# Pynguin is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Pynguin is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Pynguin.  If not, see <https://www.gnu.org/licenses/>.
"""Provides a search statistics that collects all the data values reported"""
from __future__ import annotations

import logging
import time
from typing import Optional, Dict, Any, List

import pynguin.configuration as config
import pynguin.ga.chromosome as chrom
import pynguin.testsuite.testsuitechromosome as tsc
from pynguin.utils.statistics.outputvariablefactory import (
    ChromosomeOutputVariableFactory,
    SequenceOutputVariableFactory,
    DirectSequenceOutputVariableFactory,
)
from pynguin.utils.statistics.statistics import RuntimeVariable
from pynguin.utils.statistics.statisticsbackend import (
    AbstractStatisticsBackend,
    ConsoleStatisticsBackend,
    CSVStatisticsBackend,
    OutputVariable,
)


class SearchStatistics:
    """A singleton of SearchStatistics collects all the data values reported"""

    _logger = logging.getLogger(__name__)

    def __init__(self):
        self._backend: Optional[AbstractStatisticsBackend] = self._initialise_backend()
        self._output_variables: Dict[str, OutputVariable] = {}
        self._variable_factories: Dict[str, ChromosomeOutputVariableFactory] = {}
        self._sequence_output_variable_factories: Dict[
            str, SequenceOutputVariableFactory
        ] = {}
        self._init_factories()
        self.set_output_variable_for_runtime_variable(
            RuntimeVariable.Random_Seed, config.INSTANCE.seed
        )
        self._fill_sequence_output_variable_factories()
        self._start_time = time.time_ns()
        self._best_individual: Optional[tsc.TestSuiteChromosome] = None

    @staticmethod
    def _initialise_backend() -> Optional[AbstractStatisticsBackend]:
        backend = config.INSTANCE.statistics_backend
        if backend == config.StatisticsBackend.CONSOLE:
            return ConsoleStatisticsBackend()
        if backend == config.StatisticsBackend.CSV:
            return CSVStatisticsBackend()
        return None

    def _init_factories(self) -> None:
        self._variable_factories[
            RuntimeVariable.Length.name
        ] = self._ChromosomeLengthOutputVariableFactory()
        self._variable_factories[
            RuntimeVariable.Size.name
        ] = self._ChromosomeSizeOutputVariableFactory()
        self._variable_factories[
            RuntimeVariable.Coverage.name
        ] = self._ChromosomeCoverageOutputVariableFactory()
        self._variable_factories[
            RuntimeVariable.Fitness.name
        ] = self._ChromosomeFitnessOutputVariableFactory()

    def _fill_sequence_output_variable_factories(self) -> None:
        self._sequence_output_variable_factories[
            RuntimeVariable.CoverageTimeline.name
        ] = self._CoverageSequenceOutputVariableFactory()
        self._sequence_output_variable_factories[
            RuntimeVariable.SizeTimeline.name
        ] = self._SizeSequenceOutputVariableFactory()
        self._sequence_output_variable_factories[
            RuntimeVariable.LengthTimeline.name
        ] = self._LengthSequenceOutputVariableFactory()
        self._sequence_output_variable_factories[
            RuntimeVariable.TotalExceptionsTimeline.name
        ] = DirectSequenceOutputVariableFactory.get_integer(
            RuntimeVariable.TotalExceptionsTimeline
        )

    def current_individual(self, individual: chrom.Chromosome) -> None:
        """Called when a new individual is sent.

        The individual represents the best individual of the current generation.

        :param individual: The best individual of the current generation
        """
        if not self._backend:
            return

        if not isinstance(individual, tsc.TestSuiteChromosome):
            self._logger.warning("SearchStatistics expected a TestSuiteChromosome")
            return

        self._logger.debug("Received individual")
        for variable_factory in self._variable_factories.values():
            self.set_output_variable(variable_factory.get_variable(individual))
        for seq_variable_factory in self._sequence_output_variable_factories.values():
            seq_variable_factory.update(individual)

    def set_output_variable(self, variable: OutputVariable) -> None:
        """Sets an output variable to a value directly

        :param variable: The variable to be set
        """
        if variable.name in self._sequence_output_variable_factories:
            var = self._sequence_output_variable_factories[variable.name]
            assert isinstance(var, DirectSequenceOutputVariableFactory)
            var.set_value(variable.value)
        else:
            self._output_variables[variable.name] = variable

    def set_output_variable_for_runtime_variable(
        self, variable: RuntimeVariable, value: Any
    ) -> None:
        """Sets an output variable to a value directly

        :param variable: The variable to be set
        :param value: the value to be set
        """
        self.set_output_variable(OutputVariable(name=variable.name, value=value))

    @property
    def output_variables(self) -> Dict[str, OutputVariable]:
        """Provides the output variables"""
        return self._output_variables

    @staticmethod
    def _get_all_output_variable_names() -> List[str]:
        return [
            "TARGET_CLASS",
            "criterion",
            RuntimeVariable.Coverage.name,
        ]

    def _get_output_variable_names(self) -> List[str]:
        variable_names: List[str] = []
        if not config.INSTANCE.output_variables:
            variable_names.extend(self._get_all_output_variable_names())
        else:
            for entry in config.INSTANCE.output_variables.split(","):
                variable_names.append(entry.strip())
        return variable_names

    def _get_output_variables(
        self, individual, skip_missing: bool = False
    ) -> Dict[str, OutputVariable]:
        variables: Dict[str, OutputVariable] = {}

        for variable_name in self._get_output_variable_names():
            if variable_name in self._output_variables:
                # Values directly sent
                variables[variable_name] = self._output_variables[variable_name]
            elif variable_name in self._variable_factories:
                # Values extracted from the individual
                variables[variable_name] = self._variable_factories[
                    variable_name
                ].get_variable(individual)
            elif variable_name in self._sequence_output_variable_factories:
                # Time related values, which will be expanded in a list of values
                # through time
                for var in self._sequence_output_variable_factories[
                    variable_name
                ].get_output_variables():
                    variables[var.name] = var
            elif skip_missing:
                # if variable does not exist, return an empty value instead
                variables[variable_name] = OutputVariable(name=variable_name, value="")
            else:
                self._logger.error(
                    "No obtained value for output variable %s", variable_name
                )
                return {}

        return variables

    def write_statistics(self) -> bool:
        """Write result to disk using selected backend

        :return: True if the writing was successful
        """
        self._logger.info("Writing statistics")
        if not self._backend:
            return False

        self._output_variables[RuntimeVariable.total_time.name] = OutputVariable(
            name=RuntimeVariable.total_time.name,
            value=time.time_ns() - self._start_time,
        )

        if not self._best_individual:
            self._logger.error(
                "No statistics has been saved because Pynguin failed to generate any "
                "test case"
            )
            return False

        individual = self._best_individual
        output_variables = self._get_output_variables(individual)
        self._backend.write_data(output_variables)
        return True

    class _ChromosomeLengthOutputVariableFactory(ChromosomeOutputVariableFactory):
        def __init__(self) -> None:
            super().__init__(RuntimeVariable.Length)

        def get_data(self, individual: tsc.TestSuiteChromosome) -> int:
            return individual.total_length_of_test_cases

    class _ChromosomeSizeOutputVariableFactory(ChromosomeOutputVariableFactory):
        def __init__(self) -> None:
            super().__init__(RuntimeVariable.Size)

        def get_data(self, individual: tsc.TestSuiteChromosome) -> int:
            return individual.size

    class _ChromosomeCoverageOutputVariableFactory(ChromosomeOutputVariableFactory):
        def __init__(self) -> None:
            super().__init__(RuntimeVariable.Coverage)

        def get_data(self, individual: tsc.TestSuiteChromosome) -> float:
            return individual.coverage

    class _ChromosomeFitnessOutputVariableFactory(ChromosomeOutputVariableFactory):
        def __init__(self) -> None:
            super().__init__(RuntimeVariable.Fitness)

        def get_data(self, individual: tsc.TestSuiteChromosome) -> float:
            return individual.fitness

    class _CoverageSequenceOutputVariableFactory(SequenceOutputVariableFactory):
        def __init__(self) -> None:
            super().__init__(RuntimeVariable.CoverageTimeline)

        def get_value(self, individual: tsc.TestSuiteChromosome) -> float:
            return individual.coverage

    class _SizeSequenceOutputVariableFactory(SequenceOutputVariableFactory):
        def __init__(self) -> None:
            super().__init__(RuntimeVariable.SizeTimeline)

        def get_value(self, individual: tsc.TestSuiteChromosome) -> int:
            return individual.size

    class _LengthSequenceOutputVariableFactory(SequenceOutputVariableFactory):
        def __init__(self) -> None:
            super().__init__(RuntimeVariable.LengthTimeline)

        def get_value(self, individual: tsc.TestSuiteChromosome) -> int:
            return individual.total_length_of_test_cases