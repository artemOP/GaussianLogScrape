from pprint import pprint
import logging
from dataclasses import dataclass, field
from functools import cached_property


@dataclass()
class Convergence_row:
    value: float
    threshold: float
    converged: bool


@dataclass()
class Convergence:
    maximum_force: Convergence_row
    RMS_force: Convergence_row
    maximum_displacement: Convergence_row
    RMS_displacement: Convergence_row
    predicted_energy_change: float


@dataclass()
class ZeroPointEnergy:
    zero_point_correction: float
    thermal_correction_to_energy: float
    thermal_correction_to_enthalpy: float
    thermal_correction_to_gibbs: float
    sum_of_electronic_and_zero_point_energies: float
    sum_of_electronic_and_thermal_energies: float
    sum_of_electronic_and_thermal_enthalpies: float
    sum_of_electronic_and_thermal_free_energies: float
    electronic_energy: float = field(init=False)

    def __post_init__(self):
        self.electronic_energy = (
            self.sum_of_electronic_and_zero_point_energies - self.zero_point_correction
        )


class BadLogFile(Exception):
    """Raised when log file is bad"""

    def __init__(self, message="Log file is not valid or has errors"):
        self.message = message
        logging.error(self.message)

    def __str__(self):
        return self.message


class NotConverged(BadLogFile):
    """Raised when structure has not fully converged"""

    def __init__(self):
        super().__init__(message="Structure did not fully converge")


class ImaginaryFrequency(BadLogFile):
    """Raised when low_frequencies are below -10 (too low to be correct structure)"""

    def __init__(self):
        super().__init__(message="Low frequency numbers are too low")


def read_file(file: str) -> list[str]:
    with open(file) as f:
        return f.readlines()


class File:
    def __init__(self, file: list[str]):
        self._file = file
        self.VALID = self.verify_file(self.file)
        _ = self.convergence, self.low_frequencies, self.zero_point_energy

    def verify_file(self, file: list[str]) -> bool:
        logging.debug("verification started")
        if "Normal termination" not in file[-1]:
            logging.debug("bad log file")
            raise BadLogFile
        elif not self.convergence:
            logging.debug("not converged")
            raise NotConverged
        elif isinstance(self.low_frequencies, float):
            logging.debug("imaginary frequency")
            try:
                raise ImaginaryFrequency
            except Exception as e:
                e.add_note(f"{self.low_frequencies} is too low")
                raise
        else:
            return True

    @property
    def file(self) -> list[str]:
        return self._file

    @file.setter
    def file(self, new_file):
        self.VALID = self.verify_file(new_file)
        if self.VALID:
            self._file = new_file
        else:
            logging.warning("file not valid")

    @cached_property
    def convergence(self) -> Convergence | None:
        for i, line in enumerate(self.file):
            if "Converged?" not in line:
                continue
            if not all("YES" in line for line in self.file[i + 1 : i + 5]):
                continue

            rows = [item.split() for item in self.file[i + 1 : i + 5]]
            return Convergence(
                *[
                    Convergence_row(
                        value=float(row[-3]),
                        threshold=float(row[-2]),
                        converged=True if row[-1] == "YES" else False,
                    )
                    for row in rows
                ],
                predicted_energy_change=float(
                    self.file[i + 5].split("=")[1].removesuffix("\n").replace("D", "E")
                ),
            )

    @cached_property
    def low_frequencies(self) -> list[float] | float:
        frequencies: list[float] = []
        for i, line in enumerate(self.file):
            if "Low frequencies" not in line:
                continue
            for value in line.split("   ")[1:]:
                value: float = float(value)
                if value < -10:
                    return value
                frequencies.append(value)
        return frequencies

    @cached_property
    def zero_point_energy(self) -> ZeroPointEnergy:
        for i, line in enumerate(self.file):
            if "Zero-point correction" not in line:
                data = None
                continue
            data = [line.split("    ") for line in self.file[i : i + 8]]
            break
        for line in data:
            for index, value in enumerate(line):
                if not value:
                    line.pop(index)
            line[-1] = line[-1].split()[0]
        return ZeroPointEnergy(*[float(item[-1]) for item in data])


def main():
    while True:
        file_path = input("Enter file location")
        try:
            file = read_file(file_path)
        except FileNotFoundError:
            logging.error("please use the full file path when submitting a file")
            continue
        data = File(file)
        pprint(data.convergence)
        print("#".join("#" for i in range(100)))
        pprint(data.low_frequencies)
        print("#".join("#" for i in range(100)))
        pprint(data.zero_point_energy)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
