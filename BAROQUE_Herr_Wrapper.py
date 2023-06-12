"""
BAROQUE - Blueprint for Assembling Runtime Operations for QUantum Experiments

Author - Harrison Barnes
College - Rochester Institute of Technology, Kate Gleason College of Engineering
Email - hjjbarnes@gmail.com

BAROQUE_Herr_Wrapper.py acts as a wrapper for interfacing IBM Qiskit with High Error Rate Routing (HERR). Utilizes the
original Herr.py file and wraps prep work for routing so the HERR user does not need to perform steps unique to routing
and transpiling HERR.
"""
from qiskit import transpile
from qiskit.converters import dag_to_circuit, circuit_to_dag
from qiskit import Aer
import networkx as nx
import BAROQUE_Common_Constants as CommConst
import HERR


def routeUsingHerr(circuit, coupling_list, coupling_map, cx_error_map):
    """
    Function - routeUsingHerr
    Inputs:
        circuit - QuantumCircuit to be routed using HERR
        coupling_list, coupling_map, cx_error_map - Similarly named field in BAROQUE container object

    Outputs: QuantumCircuit routed using HERR
    """
    circuit_dag = circuit_to_dag(circuit)
    herr_noise_graph = nx.from_edgelist(coupling_list)
    for edge in coupling_list:
        herr_noise_graph.edges[edge[0], edge[1]]["weight"] = \
            cx_error_map[coupling_list.index(edge)]
    herr = HERR.HERR(coupling_map, herr_noise_graph)
    # Run HERR to update dag, convert form dag to circuit, return circuit
    herr_res = herr.run(circuit_dag)
    return dag_to_circuit(herr_res)


def transpileUsingHerr(circuit, coupling_list, coupling_map, cx_error_map, basis_gates):
    """
    Function - transpileUsingHerr
    Inputs:
        circuit - QuantumCircuit to be routed using HERR
        coupling_list, coupling_map, cx_error_map - Similarly named field in BAROQUE container object

    Outputs: QuantumCircuit routed using HERR
    """
    circuit_dag = circuit_to_dag(circuit)
    herr_noise_graph = nx.from_edgelist(coupling_list)
    for edge in coupling_list:
        herr_noise_graph.edges[edge[0], edge[1]]["weight"] = \
            cx_error_map[coupling_list.index(edge)]
    herr = HERR.HERR(coupling_map, herr_noise_graph)
    # Run HERR
    herr_res = herr.run(circuit_dag)
    updated_circ = dag_to_circuit(herr_res)

    # Transpile HERR and return transpiled circuit
    return transpile(updated_circ, Aer.get_backend(CommConst.AER_QASM_SIM),
                     coupling_map=coupling_map,
                     basis_gates=basis_gates,
                     routing_method='basic',
                     layout_method='trivial')
