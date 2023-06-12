"""
BAROQUE - Blueprint for Assembling Runtime Operations for QUantum Experiments

Author - Harrison Barnes
College - Rochester Institute of Technology, Kate Gleason College of Engineering
Email - hjjbarnes@gmail.com

BAROQUE provides a basic structure for researchers, scientists, and engineers to add a quantum assembly file, generate
a QISKIT circuit, fetch a specific IBMQ API backend for a device, transpiles it, and runs it. Allows room for users to
edit and tailor it to their needs
"""

# Qiskit Imports
import networkx as nx
from qiskit import QuantumCircuit, Aer
from qiskit.converters import circuit_to_dag, dag_to_circuit
from qiskit.compiler import transpile
import HERR

# Python Imports
import sys
import getopt

# BAROQUE Imports
import BAROQUE_Metrics as Metrics
import BAROQUE_IBM_Interface as IbmInterface
import BAROQUE_Common_Constants as CommConst
import BAROQUE_Herr_Wrapper as HerrWrap


def main(argv):
    """
    Start of main function. Declare and assign necessary variables. Not all may be used, some programs may need more too
    """
    ibmq_api_key = ""  # REQUIRED to sign into IBM Quantum API. Check your IBM Quantum Dashboard for the key string
    input_file = ""  # Circuit .qasm file if used
    output_file = ""  # Output filename if used
    # NOTE as of now, backend string cannot be a simulator. WIP
    backend_str = CommConst.OSLO_SYS_STR  # String designating the desire IBM backend. Defaults to IBM Oslo.
    routing_algorithm = CommConst.ROUTING_BASIC  # String designating desired routing algorithm. Defaults to basic swap

    """
    OPTIONAL - GETOPT SECTION
    
    If Scripting is desired, put getopt (or other scripting package code) at start of file.
    
    Recommendations:
        IBM backend
        input file (circuit .qasm)
        output file (.txt or other)
    
    Honorable Mentions:
        Routing algorithm
    """

    # YOUR GETOPT CODE HERE

    """
    IBM API Access Section
    
    Log in to IBM and obtain backend dating using BAROQUE's IbmqInterfaceContainer class
    """

    quantum_container = IbmInterface.IbmqInterfaceContainer(ibmq_api_key, backend_str)

    """
    Circuit Creation Section
    
    Construct a Qiskit QuantumCircuit object or convert one from a .qasm file
    """

    # Creates QuantumCircuit from .qasm file specified by the user
    circuit = QuantumCircuit.from_qasm_file(input_file)

    # Some routing algorithms require a DAG. Generate this here
    circuit_DAG = circuit_to_dag(circuit)

    """
    OPTIONAL - Text file output section
    
    If using an output file, prep that here
    """
    # Open output file in append mode
    # out_file = open(output_file, "w")

    # Add header information for the test's output data
    # out_file.write("\nTest File: " + input_file)
    # out_file.write("Device: " + backend_str)


    """
    Transpile & Sim Section
    
    Transpile the circuit prior to simulating the circuit. Perform optimization, routing, decomposition, etc.
    Create a simulation object to perform metrics and evaluation
    """

    # Transpile the circuit using qiskit transpile().
    if routing_algorithm == CommConst.ROUTING_HERR:  # Transpile HERR using BAROQUE wrapper
        transpiled_circuit = HerrWrap.transpileUsingHerr(circuit, quantum_container.coupling_list,
                                                         quantum_container.coupling_map,
                                                         quantum_container.cx_error_map,
                                                         quantum_container.basis_gates)
    else:  # Transpile non-Herr routing algorithms normally
        transpiled_circuit = transpile(circuit, Aer.get_backend(CommConst.AER_QASM_SIM),
                                       coupling_map=quantum_container.coupling_map,
                                       basis_gates=quantum_container.basis_gates,
                                       routing_method=routing_algorithm,
                                       layout_method=CommConst.LAYOUT_TRIVIAL)

    # Retrieve the backend simulator information from Aer
    simulation = Aer.get_backend(CommConst.AER_QASM_SIM)

    """
    Analysis Section
    
    Add metrics here from BAROQUE_Metrics.py
    Raw results are generated here as an example.
    """

    # Simulates raw results using 1028 shots.
    results = Metrics.metricRawResults(1028, circuit, quantum_container.noise_model, simulation)

    # Close output file if used
    # out_file.close()


"""
Function - checkRequiredOptions
Inputs:
    put required inputs here if using getopt

Outputs: True if all valid, False otherwise

checkRequiredOptions performs validation on the getopt arguments to ensure that they are:
    1. present
    2. correct format
Note that not all issues are checked here, only getopt-input related ones

If getopt is not used, this function can be removed
"""
def checkRequiredOptions():
    return True


"""
Function - usage

Prints the usage string for the BAROQUE getopt terminal format
If getopt is not used, this function can be removed
"""
def usage():
    print("Put usage string for getopt here. Remove function if not used...\n")


"""
Function - exitBAROQUE
Inputs: cause_code - code denoting the cause of the exit condition
Outputs: none, exits program
    
Prints the relevant error message and exits with the cause_code
If no exit codes are needed, this function can be removed
"""
def exitBAROQUE(cause_code):
    print("Sample function. Put exit codes here if wanted...\n")
    print("Exiting BAROQUE code...\n")
    sys.exit(cause_code)


if __name__ == "__main__":
    main(sys.argv[1:])
