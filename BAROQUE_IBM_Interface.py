"""
BAROQUE - Blueprint for Assembling Runtime Operations for QUantum Experiments

BAROQUE_IBM_Interface.py

Author - Harrison Barnes
College - Rochester Institute of Technology, Kate Gleason College of Engineering
Email - hjjbarnes@gmail.com

BAROQUE_IBM_Interface allows the user to easily interface with IBM's Quantum API through the encapsulation of
IBM functions into simpler ones for the user.
"""

# Qiskit Imports
import networkx as nx
from qiskit.providers import backend
from qiskit.transpiler import CouplingMap
from qiskit import IBMQ
from qiskit.providers.aer.noise import NoiseModel


class IbmqInterfaceContainer:
    """
    CLASS - IbmqInterfaceContainer

    The IBMQ Interface Container is a class whose's objects store the provider, backend, configuration, and pro
    """
    def __init__(self, ibmq_api_key, backend_name):
        self.provider = self.getProviderIBMQ(ibmq_api_key)
        self.backend = self.getBackendIBMQ(backend_name, self.provider)
        self.configuration = self.getConfigurationIBMQ(self.backend)
        self.properties = self.getPropertiesIBMQ(self.backend)
        self.coupling_list = self.getCouplingListIBMQ(self.configuration)
        self.coupling_map = self.getCouplingMapIBMQ(self.configuration)
        self.basis_gates = self.getBasisGatesIBMQ(self.configuration)
        self.cx_error_map = self.extractCxErrorMap(self.configuration, self.properties, self.coupling_list)
        self.noise_model = self.getBackendNoiseModelIBMQ(self.backend)

    @staticmethod
    def getProviderIBMQ(ibm_api_key):
        """
        Function - getProviderIBMQ
        Inputs:
            ibm_api_key - string containing the user's IBM "API token"

        Outputs: The Qiskit Provider object obtained from IBM using the api key
        """
        IBMQ.save_account(ibm_api_key, overwrite=True)
        return IBMQ.load_account()

    @staticmethod
    def getBackendIBMQ(backend_name, provider):
        """
        Function - getBackendIBMQ
        Inputs:
            backend_name - String containing the desired IBM backend device
            provider - Qiskit Provider object

        Outputs: The Qiskit Backend object corresponding to the user specified backend in backend_name
        """
        return provider.get_backend(backend_name)

    @staticmethod
    def getConfigurationIBMQ(target_backend):
        """
        Function - getConfigurationIBMQ
        Inputs:
            target_backend - Qiskit Backend object

        Outputs: The Qiskit configuration information container for the specified backend
        """
        return target_backend.configuration()

    @staticmethod
    def getPropertiesIBMQ(target_backend):
        """
        Function - getPropertiesIBMQ
        Inputs:
            target_backend - Qiskit Backend object

        Outputs: The Qiskit properties information container for the specified backend
        """
        return target_backend.properties()

    @staticmethod
    def getCouplingListIBMQ(configuration):
        """
        Function - getCouplingListIBMQ
        Inputs:
            configuration - Qiskit configuration that contains configuration information for the backend

        Outputs: Python List containing the qubit pairs of the backend
        """
        return configuration.coupling_map

    @staticmethod
    def getCouplingMapIBMQ(configuration):
        """
        Function - getCouplingMapIBMQ
        Inputs:
            configuration - Qiskit configuration that contains configuration information for the backend

        Outputs: Qiskit CouplingMap object
        """
        return CouplingMap(configuration.coupling_map)

    @staticmethod
    def getBasisGatesIBMQ(configuration):
        """
        Function - getBasisGatesIBMQ
        Inputs:
            configuration - Qiskit configuration that contains configuration information for the backend

        Outputs: List of basis gates (native gates) used by the IBM backend. Stored as a Python List
        """
        return configuration.basis_gates

    @staticmethod
    def getBackendNoiseModelIBMQ(target_backend):
        """
        Function - getBackendNoiseModelIBMQ
        Inputs:
            target_backend- IBM backend object

        Outputs: NoiseModel pulled from the backend of the IBM backend object
        """
        return NoiseModel.from_backend(target_backend)

    @staticmethod
    def extractCxErrorMap(config, props, coupling_map):
        """
        Function - extractCxErrorMap
        Inputs:
            config - Backend configuration schema
            props - Backend properties schema
            coupling_map - List of qubit pairs that represent the coupling of the target device

        Outputs: cx_errors, a List of cx link errors where cx_errors[idx] is the error for the link at coupling_map[idx]

        Uses IBM's backend API to extract the cx (CNOT) error rates of the target device
        """
        # Obtain the backend's version number. BackendV1 and BackendV2 have different function calls and properties
        backend_version = config.backend_version
        # Build the CNOT link error mapping.
        if int(backend_version[0]) <= 1:  # BackendV1 version
            # Convert properties to a usable dictionary
            props_dict = props.to_dict()

            # Allocate memory for CNOT error map
            cx_errors = []

            if coupling_map:  # Constructs a list of CNOT errors for each link in the coupling map
                for line in coupling_map:  # For each link in the coupling map, append the link error to the error list
                    for item in props_dict["gates"]:
                        if item["qubits"] == line:
                            cx_errors.append(item["parameters"][0]["value"])
                            break

        else:  # BackendV2 version
            # Declare memory space for the error maps
            two_q_error_map = {}
            cx_errors = []

            for gate, prop_dict in backend.target.items():  # Get two qubit error maps from the backend
                if prop_dict is None or None in prop_dict:
                    continue
                for qargs, inst_props in prop_dict.items():
                    if inst_props is None:
                        continue
                    elif len(qargs) == 2:
                        if inst_props.error is not None:
                            two_q_error_map[qargs] = max(
                                two_q_error_map.get(qargs, 0), inst_props.error
                            )

            if coupling_map:  # Constructs a list of CNOT errors for each link in the coupling map
                for line in coupling_map.get_edges():  # For each link, get the error and add to the error list
                    err = two_q_error_map.get(tuple(line), 0)
                    cx_errors.append(err)
        # Return the link error list
        return cx_errors
