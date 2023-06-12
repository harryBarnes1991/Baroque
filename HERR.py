"""
HERR - High Error Rate Routing

Author - Sean Bonaventure
College - Rochester Institute of Technology, Kate Gleason College of Engineering

High Error Rate Routing - A basic swap based noise aware routing algorithm that seeks to avoid high error links
if pathing around is cheaper than using the link.

HERR.py is not owned by the author of the BaroqueQuantum Python Package. Baroque's MIT license may not apply here.
"""

import logging
from copy import copy
from itertools import cycle
import numpy as np
import networkx as nx

from qiskit.dagcircuit import DAGCircuit
from qiskit.circuit.library.standard_gates import SwapGate
from qiskit.transpiler.basepasses import TransformationPass
from qiskit.transpiler.exceptions import TranspilerError
from qiskit.transpiler.layout import Layout
from qiskit.dagcircuit import DAGNode


class HERR(TransformationPass):

    def __init__(self, couplingMap, qubitAccuracy, initial_layout=None, searchDepth=2):
        super().__init__()
        # This is the constructor that initalizes all the input values
        self.couplingMap = couplingMap
        self.qubitAccuracy = qubitAccuracy
        self.initial_layout = initial_layout
        self.searchDepth = searchDepth

    def run(self, dag):
        # The run function is be be called to run routing. The input is the DAG of the circuit being test,
        # output is dag representing routed circuit
        new_dag = DAGCircuit()
        for qreg in dag.qregs.values():
            new_dag.add_qreg(qreg)
        for creg in dag.cregs.values():
            new_dag.add_creg(creg)
        if len(dag.qubits) > len(self.couplingMap.physical_qubits):
            raise TranspilerError("The layout does not match the amount of qubits in the DAG")

        # Sets up inputs
        canonical_register = dag.qregs['q']
        trivial_layout = Layout.generate_trivial_layout(canonical_register)
        current_layout = trivial_layout.copy()

        # Basically: 1) iterate through each layer
        # 2) Grab arugment qubits for a gate
        # 3) Use search function to see if better edge exists
        # 4) If so, add swaps. If not, default to BasicSwap
        for layer in dag.serial_layers():
            subdag = layer['graph']
            for gate in subdag.two_qubit_ops():
                physQArgs = [current_layout[gate.qargs[0]], current_layout[gate.qargs[1]]]
                # If the two qubits are not attached at the coupling map add swap to connect
                betterEdge = self.find_better_link(physQArgs[0], physQArgs[1], current_layout, self.searchDepth)
                if betterEdge is not None:
                    # Lets insert swap to go to the better edge
                    swap_layer = DAGCircuit()
                    swap_layer.add_qreg(canonical_register)

                    # Find shortest path returns the path of qubits to insert swap gates at
                    swapPath = self.find_shortest_path((physQArgs[0], physQArgs[1]), (betterEdge[0], betterEdge[1]))
                    for i in range(2):
                        if swapPath[i] is not None:
                            for swap in range(0, len(swapPath[i]) - 1, 1):
                                connected_wire_1 = swapPath[i][swap]
                                connected_wire_2 = swapPath[i][swap + 1]

                                qubit_1 = current_layout[connected_wire_1]
                                qubit_2 = current_layout[connected_wire_2]

                                swap_layer.apply_operation_back(SwapGate(),
                                                                qargs=[qubit_1, qubit_2],
                                                                cargs=[])

                    # layer insertion
                    order = current_layout.reorder_bits(new_dag.qubits)
                    new_dag.compose(swap_layer, qubits=order)

                    # update current_layout
                    for i in range(2):
                        if swapPath[i] is not None:
                            for swap in range(0, len(swapPath[i]) - 1, 1):
                                current_layout.swap(swapPath[i][swap], swapPath[i][swap + 1])
                else:
                    if self.couplingMap.distance(physQArgs[0], physQArgs[1]) != 1:
                        # If we can perform no noise based swaps, make sure the qubits are connecting in the coupling map
                        # This routing algorithm is taken form the basic_swap.py module in Qiskit terra
                        # Insert a new layer with the SWAP(s).
                        swap_layer = DAGCircuit()
                        swap_layer.add_qreg(canonical_register)

                        path = self.couplingMap.shortest_undirected_path(physQArgs[0], physQArgs[1])
                        for swap in range(len(path) - 2):
                            connected_wire_1 = path[swap]
                            connected_wire_2 = path[swap + 1]

                            qubit_1 = current_layout[connected_wire_1]
                            qubit_2 = current_layout[connected_wire_2]

                            # create the swap operation
                            swap_layer.apply_operation_back(
                                SwapGate(), qargs=[qubit_1, qubit_2], cargs=[]
                            )

                        # layer insertion
                        order = current_layout.reorder_bits(new_dag.qubits)
                        new_dag.compose(swap_layer, qubits=order)

                        # update current_layout
                        for swap in range(len(path) - 2):
                            current_layout.swap(path[swap], path[swap + 1])

            order = current_layout.reorder_bits(new_dag.qubits)
            new_dag.compose(subdag, qubits=order)

        return new_dag

    def find_better_link(self, qubit1, qubit2, currentLayout, depth):
        """
        Given two qubits that will be used, it finds are more ideal pair given the
        coupling map

        Args:
            qubit1: First physical qubit being used in gate
            qubit2: Second physical qubit being used in gate
        """

        # Gather a list of the edges
        # Annoyingly, the get_edges functions will return 2 times the number of edges
        # ie, it returns [0,1] and [1,0] as two different edges. This confuses the algorithm
        # so we basically remove duplicates by sorting then adding to a set.
        edges = self.couplingMap.get_edges()
        uniqueEdges = set()
        for edge in edges:
            uniqueEdges.add(tuple(sorted(edge)))
        if [qubit1, qubit2] in self.qubitAccuracy.edges():
            bestEdgeAccuracy = self.qubitAccuracy.edges[qubit1, qubit2]['weight']
        else:
            bestEdgeAccuracy = self.calc_shortest_path_accuracy(qubit1, qubit2)

        bestEdge = (qubit1, qubit2)
        foundBetterEdge = False
        for edge in uniqueEdges:
            # First parth of if checks if each qubit is within desired distance to source.
            if (self.couplingMap.distance(qubit1, edge[0]) <= depth and self.couplingMap.distance(qubit1,
                                                                                                  edge[1]) <= depth
                    and self.couplingMap.distance(qubit2, edge[0]) <= depth and self.couplingMap.distance(qubit2, edge[
                        1]) <= depth):

                # This function predicts the accuracy of a new link
                newLinkAccuracy = self.calc_path_accuracy(bestEdge, edge, currentLayout)
                if newLinkAccuracy > bestEdgeAccuracy:
                    bestEdgeAccuracy = newLinkAccuracy
                    bestEdge = edge
                    foundBetterEdge = True
        if foundBetterEdge == False:
            bestEdge = None
        return bestEdge

    def find_path_excluding(self, sourceQubit, destQubit, exQubit):
        # Get a subgraph of coupling map without Ex qubit, find shortest path
        # This function finds the path from one qubit to another. Problem is since we are finding the path for BOTH qubits
        # we encounter a problem if the path one qubit takes goes through the other qubit. So we create a subgraph that exludes the
        # other argument qubit
        if sourceQubit == destQubit:
            return None
        reducedCouplingGraph = nx.Graph()
        subGraphEdges = list()
        couplingMapEdges = self.couplingMap.get_edges()
        for edge in couplingMapEdges:
            if exQubit not in edge:
                subGraphEdges.append(edge)
        reducedCouplingGraph.add_edges_from(subGraphEdges)
        if sourceQubit in reducedCouplingGraph and destQubit in reducedCouplingGraph:
            try:
                shortestPath = nx.shortest_path(reducedCouplingGraph, sourceQubit, destQubit)
            except:
                shortestPath = None
        else:
            shortestPath = None
        return shortestPath

    def find_shortest_path(self, sourceQubits, destQubit):
        """
        This is a gross function, but basically we want to find the path from one set of qubits to another. Its difficult because the ordering of source
        and destination qubits is arbitrary, so we want to make sure we are doing correct swaps. Ie if the source if (1,2) and the destination is (2,3),
        we want to make sure we only insert one swap between 1 and 3, instead of 1 and 2 and 2 and 3.
        """
        qubitPath = [None, None]
        q0Paths = [None, None]
        q1Paths = [None, None]

        # This part is super gross and could definitley be done better, but it is basically finding and comparing the possible paths each qubit could take
        # For instance, Source q0 could swap to either destination q0 or q1, and Source q1 could do that same
        if destQubit[0] != sourceQubits[1]:
            q0Paths[0] = self.find_path_excluding(sourceQubits[0], destQubit[0], sourceQubits[1])
        if destQubit[1] != sourceQubits[1]:
            q0Paths[1] = self.find_path_excluding(sourceQubits[0], destQubit[1], sourceQubits[1])

        if destQubit[0] != sourceQubits[0]:
            q1Paths[0] = self.find_path_excluding(sourceQubits[1], destQubit[0], sourceQubits[0])
        if destQubit[1] != sourceQubits[0]:
            q1Paths[1] = self.find_path_excluding(sourceQubits[1], destQubit[1], sourceQubits[0])

        # This is the part of that function that does the comparisons
        if sourceQubits[0] not in destQubit and sourceQubits[1] not in destQubit:

            if len(q0Paths[0]) <= len(q1Paths[0]):
                qubitPath[0] = q0Paths[0]
                qubitPath[1] = q1Paths[1]
            else:
                qubitPath[0] = q0Paths[1]
                qubitPath[1] = q1Paths[0]

            if len(q0Paths[1]) < len(q0Paths[0]) and len(q0Paths[1]) < len(q1Paths[1]):
                qubitPath[0] = q0Paths[1]
            else:
                qubitPath[0] = q0Paths[0]

            if len(q1Paths[1]) < len(q1Paths[0]) and len(q1Paths[1]) < len(q0Paths[1]):
                qubitPath[1] = q1Paths[1]
            else:
                qubitPath[1] = q1Paths[0]
        elif sourceQubits[0] not in destQubit:
            # If only qubit 0 is not in destination, we only need to swap to whatever isn't the other qubit
            # ie, if we need to go from [1, 0] to [2, 0], we only need to swap from qubits 1 to 2
            if sourceQubits[1] is not destQubit[0]:
                qubitPath[0] = q0Paths[1]
            else:
                qubitPath[0] = q0Paths[0]
        elif sourceQubits[1] not in destQubit:
            # If only qubit 1 is not in destination, we only need to swap to whatever isn't the other qubit
            # ie, if we need to go from [0, 1] to [0, 2], we only need to swap from qubits 1 to 2
            if sourceQubits[0] is not destQubit[0]:
                qubitPath[1] = q1Paths[0]
            else:
                qubitPath[1] = q1Paths[1]
        return qubitPath

    def calc_shortest_path_accuracy(self, qubit1, qubit2):
        path = self.couplingMap.shortest_undirected_path(qubit1, qubit2)
        accuracy = 1.0

        for swap in range(len(path) - 2):
            connected_wire_1 = path[swap]
            connected_wire_2 = path[swap + 1]
            linkAccuracy = self.qubitAccuracy.edges[connected_wire_1, connected_wire_2]['weight']
            accuracy = accuracy * (linkAccuracy ** 3)

        return accuracy

    def calc_path_accuracy(self, sourceQubits, destQubit, current_layout):
        # Determines accuracy of a path from an old link to a new link
        # Error rate of new link: = (EnewLink)*(Error of Path for qubit 0^3)*(Error of Path for qubit 1^3)
        # Cube is used for paths since each swap is 3 CNOT gates

        # represents the paths needed for source qubits 0 and 1
        qubitPath = self.find_shortest_path(sourceQubits, destQubit)

        if qubitPath[0] is None and qubitPath[1] is None:
            return 0

        qubitPathAccuracy = [1.0, 1.0]

        for i in range(2):
            if qubitPath[i] is not None:
                for swap in range(0, len(qubitPath[i]) - 1, 1):
                    # Basically find the source and destination qubits of the swap
                    connected_wire_1 = qubitPath[i][swap]
                    connected_wire_2 = qubitPath[i][swap + 1]

                    # Reference the noise map to find the error rate
                    linkAccuracy = self.qubitAccuracy.edges[connected_wire_1, connected_wire_2]['weight']
                    # Link accuracy ^3 because each swap decomposes into 3 CNOTs
                    qubitPathAccuracy[i] = qubitPathAccuracy[i] * (linkAccuracy ** 3)

        opAccuracy = self.qubitAccuracy.edges[destQubit[0], destQubit[1]]['weight']
        return opAccuracy * qubitPathAccuracy[0] * qubitPathAccuracy[1]


