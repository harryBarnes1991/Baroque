"""
BAROQUE - Blueprint for Assembling Runtime Operations for QUantum Experiments

BAROQUE_Metrics.py

Author - Harrison Barnes
College - Rochester Institute of Technology, Kate Gleason College of Engineering
Email - hjjbarnes@gmail.com

BAROQUE_Metrics.py offers a range of functions that encapsulate common metrics used when testing quantum circuits,
algorithms, optimizations, and more. There are three goals of BAROQUE_Metrics.py:
    1 - Create callable functions for common metrics
    2 - Encapsulate Qiskit functions into an easier to use function
    3 - Provide readable source code that allows users to create their own metrics by tweaking existing functions
        and utilizing additional Qiskit methods.
"""

# Python Library Imports
import time
import math
from numpy.linalg import norm
from numpy import dot
from scipy.spatial.distance import cityblock

# BAROQUE Imports
import BAROQUE_Common_Constants as CommConst
import BAROQUE_Herr_Wrapper as herr_wrap

# Qiskit Imports
import HERR
from qiskit import Aer
from qiskit.transpiler import CouplingMap
from qiskit.converters import circuit_to_dag, dag_to_circuit
from qiskit.compiler import transpile
from qiskit.transpiler.passes.routing import *


def metricDiffCNOT(circuit_a, circuit_b):
    """
    Function - metricDiffCNOT
    Inputs:
        circuit_a, circuit_b - Qiskit QuantumCircuits being compared

    Outputs: Difference in CNOT count between circuit_a and circuit_b
    """
    # Get CNOT counts for both circuits and returns how many more CNOTs exist in circuit_b than circuit_a
    return metricCountCNOT(circuit_b) - metricCountCNOT(circuit_a)


def metricDiffGate(circuit_a, circuit_b, gate_string):
    """
    Function - metricDiffCNOT
    Inputs:
        circuit_a, circuit_b - Qiskit QuantumCircuits being compared
        gate_string - a string representation of the gate provided by Qiskit. EX: CNOT = "cx"

    Outputs: Difference in gate count between circuit_a and circuit_b
    """
    # Get gate counts for both circuits and return how many more gates exist in circuit_b than circuit_a
    return metricCountGate(circuit_b, gate_string) - metricCountGate(circuit_a, gate_string)


def metricCountCNOT(circuit):
    """
    Function - metricCountCNOT
    Inputs:
        circuit - Qiskit QuantumCircuit

    Outputs: The number of CNOT gates in the provided circuit
    """
    # Returns the CNOT count of the circuit
    return metricCountGate(circuit, CommConst.CONTROL_NOT_GATE)


def metricCountGate(circuit, gate_string):
    """
    Function - metricCountGate
    Inputs:
        circuit - Qiskit QuantumCircuit
        gate_string - a string representation of the gate provided by Qiskit. EX: CNOT = "cx"

    Outputs: The number of specified gates in the provided circuit
    """
    # Returns the number of gates in the circuit specified by the gate_string parameter
    if gate_string in circuit.count_ops().keys():
        return circuit.count_ops()[gate_string]
    return 0  # Return zero if no gates exist


def metricDiffDepth(circuit_a, circuit_b, basis_gates_a=None, basis_gates_b=None):
    """
    Function - metricCountCNOT
    Inputs:
        circuit_a, circuit_b - Qiskit QuantumCircuits whose depth is being compared
        basis_gates_a, basis_gates_b - The set of basis gates for the circuit. Defaults to None

    Outputs: The difference in depth from circuit_a and circuit_b

    In order for depth comparisons to be sensible, the circuits must be at the same level of decomposition. That is, if
    one circuit has been transpiled to a native gate set, and the other has not, depth count will not be accurate. Thus,
    the basis_gates_x parameters handle this. If not specified, the circuit will be left untouched during depth calculation.
    If a basis gate set is provided, that circuit will be transpiled into the basis gates so that the two circuits may be
    correctly evaluated if needed by the program.
    """
    # Returns the difference in depth between circuit_a and circuit_b
    return metricCircuitDepth(circuit_b, basis_gates=basis_gates_b) - \
           metricCircuitDepth(circuit_a, basis_gates=basis_gates_a)


def metricCircuitDepth(circuit, basis_gates=None):
    """
    Function - metricCircuitDepth
    Inputs:
        circuit - Qiskit QuantumCircuit whose depth is being calculated
        basis_gates - The set of basis gates for the circuit. Defaults to None

    Outputs: The depth of circuit_a

    If basis_gates is not None, the circuit will be transpiled to the basis gates. No other operations are performed
    during transpilation except the basis decomposition.
    """
    if basis_gates is not None:  # Basis is specified, decompose to basis gate set and return the depth
        return transpile(circuit, basis_gates=basis_gates).depth()
    # Basis not specified, return the depth of the circuit as is
    return circuit.depth()


def metricAccuracy(iterations, circuit, correct_results, noise_model, simulation):
    """
    Function - metricAccuracy
    Inputs:
        iterations - Number of simulations runs to perform. More runs result in a more realistic accuracy value
        circuit - Qiskit QuantumCircuit to be simulated
        correct_results - List of circuits results that are considered an answer in the probability distribution.
        noise_model - Noise model used by the simulator
        simulation - Simulator object used to run the simulation of the circuit

    Outputs: The approximated accuracy of the circuit - % of answers that are correct
    """
    num_correct = 0
    num_qubits = circuit.num_qubits
    # Run simulation and get the counts dictionary from the simulation results
    result = metricRawResults(iterations, circuit, noise_model, simulation)
    counts = result.get_counts(circuit)
    # Iterate through the answers and add up their counts
    print(counts)
    print(num_qubits)
    translate = {}
    for k, v in counts.items():
        new_key = k
        if k.rfind(" ") != -1:
            new_key = k[0:k.rfind(" ")]
        translate[k] = new_key

    for old, new in translate.items():
        counts[new] = counts.pop(old)
    print(counts)
    for answer in correct_results:
        if answer in counts.keys():  # This line prevents KeyErrors if the answer is not generated
            num_correct += counts[answer]
    # Return the ratio of correct to total runs
    return num_correct / iterations


def metricStatevectorNorm(iterations, circuit, expected_statevector, statevector_length, noise_model, simulation):
    """
    Function - metricStatevector
    Inputs:
        iterations - Number of simulations runs to perform. More runs result in a more realistic precision value
        circuit - Qiskit QuantumCircuit to be simulated
        expected_statevector - Expected values for all possible values in the statevector
        statevector_length - Length of statevector
        noise_model - Noise model used by the simulator
        simulation - Simulator object used to run the simulation of the circuit

    Outputs: The approximated precision of the circuit - how close the statevector is to the expected
    Returns three values: Euclidean distance, Manhattan Distance. and cosine similarity
    between the resultant and expected state vector
    """
    num_correct = 0
    num_qubits = circuit.num_qubits
    # Run simulation and get the counts dictionary from the simulation results
    result = metricRawResults(iterations, circuit, noise_model, simulation)
    counts = result.get_counts(circuit)
    statevector = [0.0 for state in range(statevector_length)]
    # Iterate through the answers and add up their counts
    translate = {}
    for k, v in counts.items():
        new_key = k
        if k.rfind(" ") != -1:
            new_key = k[0:k.rfind(" ")]
        translate[k] = new_key

    for old, new in translate.items():
        counts[new] = counts.pop(old)
    for key in counts.keys():
        value = counts[key] / iterations
        statevector[int(key, 2)] = math.sqrt(value)
    # Return the ratio of correct to total runs
    for index in range(len(statevector)):
        statevector[index] = statevector[index] - float(expected_statevector[index])

    # Calculate the metric
    euclidean_distance = math.dist(statevector, expected_statevector)
    manhattan_distance = cityblock(statevector, expected_statevector)
    cosine_similarity = dot(statevector, expected_statevector) / (norm(expected_statevector) * norm(statevector))

    # WIP metrics
    l_half = 0.0
    l_tenth = 0.0
    diff = 0.0

    for index in range(len(statevector)):
        diff = statevector[index] - expected_statevector[index]
        l_half += pow(diff, 1.0 / 0.5)
        l_tenth += pow(diff, 1.0 / 0.1)

    l_half = pow(l_half, 0.5)
    l_tenth = pow(l_tenth, 0.1)

    # Return metrics as a tuple
    return euclidean_distance, manhattan_distance, cosine_similarity, l_half, l_tenth


def metricRawResults(shots, circuit, noise_model, simulation):
    """
    Function - metricRawResults
    Inputs:
        shots - Number of simulations runs to perform. More runs result in a more realistic accuracy value
        circuit - Qiskit QuantumCircuit to be simulated
        noise_model - Noise model used by the simulator
        simulation - Simulator object used to run the simulation of the circuit

    Outputs: Dictionary containing the result and the counts obtained from the simulation
    """
    return simulation.run(circuit, noise_model=noise_model, shots=shots).result()


def metricExpectedStatevector(circuit, simulation, shots=8192):
    """
    Function - metricExpectedStatevector
    Inputs:
        circuit - Qiskit QuantumCircuit to be simulated
        simulation - Simulator object used to run the simulation of the circuit
        shots  - Number of simulations runs to perform.
                 More runs result in a more accurate statevector. Defaults to 8192

    Outputs: Expected statevector for the circuit ran without noise
    """
    num_qubits = circuit.num_qubits
    statevector_length = 2 ** num_qubits
    counts = simulation.run(circuit, shots=shots).result().get_counts()
    statevector = [0.0 for state in range(statevector_length)]
    # Iterate through the answers and add up their counts
    translate = {}
    for k, v in counts.items():
        new_key = k
        if k.rfind(" ") != -1:
            new_key = k[0:k.rfind(" ")]
        translate[k] = new_key

    for old, new in translate.items():
        counts[new] = counts.pop(old)
    for key in counts.keys():
        value = counts[key] / shots
        statevector[int(key, 2)] = math.sqrt(value)

    return statevector


def metricRoutingTime(routing_method, coupling_map, coupling_list, circuit_dag, cx_error_map=None):
    """
    Function - metricRoutingTime
    Inputs:
        routing_method - Qiskit string representation of a routing method. See function for options
        coupling_map - Qiskit CouplingMap object for the target hardware used during routing
        coupling_list - Coupling list for the target hardware. Required for HERR
        circuit_dag - Qiskit CircuitDag to be routed onto the target hardware
        cx_error_map - The CX gate error mapping of the target hardware. Required for HERR

    Outputs: The time (seconds) of the circuit routing method performed on the provided circuit given a specific
    coupling map
    """
    if routing_method == "basic":  # Route with Basic Swap
        routing_algorithm = BasicSwap(coupling_map)
    elif routing_method == "sabre":  # Route with SABRE
        routing_algorithm = SabreSwap(coupling_map)
    elif routing_method == "stochastic":  # Route with Stochastic Swap
        routing_algorithm = StochasticSwap(coupling_map)
    elif routing_method == "lookahead":  # Route with Lookahead Swap
        routing_algorithm = LookaheadSwap(coupling_map)
    elif routing_method == "herr" and cx_error_map is not None:
        base_time = time.perf_counter()
        herr_wrap.routeUsingHerr(dag_to_circuit(circuit_dag), coupling_list, coupling_map, cx_error_map)
        return time.perf_counter() - base_time
    else:  # Routing method string does not match a routing option, throw error and return None
        print("Function metricRoutingTime invalid routing_method parameter.",
              "\nOptions:\tbasic\tsabre\tstochastic\tlookahead\therr\n")
        print("If using HERR, supply cx_error_map.\n")
        return None

    # Routing method selection encountered no issues, route the circuit dag, time the routing, and return the time
    base_time = time.perf_counter()
    routing_algorithm.run(circuit_dag)
    return time.perf_counter() - base_time


def metricTranspilationTime(circuit, coupling_map, coupling_list, basis_gates, routing_algorithm='basic',
                            layout_method='trivial', cx_error_map=None):
    """
    Function - metricTranspilationTime
    Inputs:
        circuit - Qiskit QuantumCircuit to be transpiled with the Qiskit transpiler
        coupling_map - Coupling map of the target hardware.
        coupling_list - Coupling list of the target hardware. Required for HERR
        basis_gates - List of basis gates used by the target hardware
        routing_algorithm - Routing algorithm to be used during transpilation. Defaults to Basic Swap
        layout_method - Layout method for transpilation process. Defaults to trivial layout
        cx_error_map - The CX gate error mapping of the target hardware. Required for HERR

    Outputs: The time (seconds) of the entire transpilation process for the given circuit and parameters
    """
    if routing_algorithm != CommConst.ROUTING_HERR:  # If not HERR, transpile normally
        base_time = time.perf_counter()
        transpile(circuit, Aer.get_backend('qasm_simulator'), coupling_map=coupling_map, basis_gates=basis_gates,
                  routing_method=routing_algorithm, layout_method=layout_method)
        return time.perf_counter() - base_time
    else:  # Run HERR, convert back to QuantumCircuit.
        if cx_error_map is None:
            print("Transpiling HERR requires a cx_error_map.\n")
            return 0.0
        base_time = time.perf_counter()
        herr_wrap.transpileUsingHerr(circuit, coupling_list, coupling_map, cx_error_map, basis_gates)
        # Time the transpilation process and return the elapsed time
        return time.perf_counter() - base_time
