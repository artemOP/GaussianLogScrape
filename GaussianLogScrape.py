import logging
from collections import namedtuple
import typing
from typing import List

Convergence_row = namedtuple("Convergence_row", {"value", "threshold", "converged"})
Convergence = namedtuple(
    "Convergence",
    {
        "maximum_force",
        "rms_force",
        "maximum_displacement",
        "rms_displacement",
        "predicted_energy_change",
    },
)
Zero_point_energy = namedtuple(
    "Zero_point_energy",
    {
        "zero_point_correction",
        "thermal_correction_to_energy",
        "thermal_correction_to_enthalpy",
        "thermal_correction_to_gibbs",
        "sum_of_electronic_and_zero_point_energies",
        "sum_of_electronic_and_thermal_energies",
        "sum_of_electronic_and_thermal_enthalpies",
        "sum_of_electronic_and_thermal_free_energies",
    },
)


def read_file(file: str) -> typing.List[str]:
    with open(file) as f:
        return f.readlines()


class File:
    def __init__(self, file: List[str]):
        self._file = file
        self.convergence: Convergence = None
        self.frequencies: List[float] = []
        self.zero_point: Zero_point_energy = None
        self.electronic_energy = None
        self.analyse_file()
        self.VALID = self.verify_file(self.file)

    def verify_file(self, file: List[str]) -> bool:
        logging.debug("verification started")
        if "Normal termination" not in file[-1]:
            logging.error("bad log file")
        elif not self.convergence:
            logging.error("structure not converged")
        elif not self.zero_point:
            logging.error("no zero point energy found")
        elif not self.frequencies:
            logging.error("no low-frequencies found")
        else:
            return True
        return False  # return false if any check fails

    @property
    def file(self) -> List[str]:
        return self._file

    @file.setter
    def file(self, new_file):
        self.VALID = self.verify_file(new_file)
        if not self.VALID:
            logging.error("file not valid")
            return
        self._file = new_file
        self.analyse_file()

    @staticmethod
    def convergence_row(row: List[str]) -> Convergence_row:
        return Convergence_row(
            value=float(row[-3]),
            threshold=float(row[-2]),
            converged=True if row[-1] == "YES" else False,
        )

    def analyse_convergence(self, rows: List[List[str]]) -> Convergence:
        return Convergence(
            maximum_force=self.convergence_row(rows[0]),
            rms_force=self.convergence_row(rows[1]),
            maximum_displacement=self.convergence_row(rows[2]),
            rms_displacement=self.convergence_row(rows[3]),
            predicted_energy_change=float(
                rows[-1][-1].split("=")[1].replace("\n", "").replace("D", "E")
            ),
        )

    def analyse_zero_point_energy(self, rows: List[List[str]]) -> Zero_point_energy:
        for line in rows:
            for index, value in enumerate(line):
                if not value:
                    line.pop(index)
            line[-1] = line[-1].split()[0]
        return Zero_point_energy(*[float(item[-1]) for item in rows])

    def analyse_file(self) -> None:
        for i, line in enumerate(self.file):
            if "Converged" in line:
                if not all("YES" in line for line in self.file[i + 1 : i + 5]):
                    continue
                rows = [item.split() for item in self.file[i + 1 : i + 6]]
                self.convergence = self.analyse_convergence(rows)

            elif "Low frequencies" in line:
                for value in line.split("   ")[1:]:
                    value: float = float(value)
                    if value < -10:
                        logging.error(
                            f"One of your low frequencies is imaginary, {value} is too low"
                        )
                    self.frequencies.append(value)

            elif "Zero-point correction" in line:
                rows = [line.split("    ") for line in self.file[i : i + 8]]
                self.zero_point = self.analyse_zero_point_energy(rows)
                self.electronic_energy = (
                    self.zero_point.sum_of_electronic_and_zero_point_energies
                    - self.zero_point.zero_point_correction
                )


def main():
    while True:
        logging.info("Enter file location")
        file_path = input()
        try:
            file = read_file(file_path)
        except FileNotFoundError:
            logging.error("please use the full file path when submitting a file")
            continue
        data = File(file)

        if not data.VALID:
            continue

        convergence = data.convergence._asdict()
        zero_point = data.zero_point._asdict()

        logging.info("\nConvergence Data:")
        for key, value in convergence.items():
            logging.info(f"{key}: {value}")

        logging.info("\nLow Frequency Data")
        logging.info(data.frequencies)

        logging.info("\nZero Point Energy Data")
        for key, value in zero_point.items():
            logging.info(f"{key}: {value}")
        logging.info(f"electronic energy: {data.electronic_energy}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
