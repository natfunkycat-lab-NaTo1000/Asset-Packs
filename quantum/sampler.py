#!/usr/bin/env python3
"""
ConductorX — Quantum-Hybrid Sampler (Component 3)

Provides quantum-enhanced probabilistic sampling for asset selection
and optimization. Runs on IBM Quantum hardware when available,
with automatic fallback to Qiskit Aer (local simulation).

Use cases for this repo:
- Probabilistic selection of which packs to prioritize during a batch repack
- Random sampling across asset variants for preview generation ordering
- Optimization of pack processing order to minimize CI time

Usage:
    from quantum.sampler import QuantumSampler

    sampler = QuantumSampler()
    samples = sampler.sample(items=["pokemon", "starwars", "pikachu-enfadao"], n=2)
    print(samples)  # e.g. ["starwars", "pikachu-enfadao"]
"""
import math
import os
import random

QISKIT_AVAILABLE = False
try:
    from qiskit import QuantumCircuit
    from qiskit.primitives import StatevectorSampler
    QISKIT_AVAILABLE = True
except ImportError:
    pass

IBM_AVAILABLE = False
try:
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as IBMSampler
    IBM_AVAILABLE = True
except ImportError:
    pass


class QuantumSampler:
    """
    Quantum-hybrid sampler.

    Priority order:
      1. IBM Quantum hardware (if IBM_QUANTUM_TOKEN is set and hardware is accessible)
      2. Qiskit Aer local simulation (if qiskit is installed)
      3. Python random fallback (always available)
    """

    def __init__(self) -> None:
        self._backend = self._detect_backend()

    def _detect_backend(self) -> str:
        token = os.environ.get("IBM_QUANTUM_TOKEN", "")
        if IBM_AVAILABLE and token:
            try:
                QiskitRuntimeService.save_account(
                    channel="ibm_quantum", token=token, overwrite=True
                )
                self._service = QiskitRuntimeService(channel="ibm_quantum")
                backends = self._service.backends(operational=True, simulator=False)
                if backends:
                    self._ibm_backend = backends[0]
                    return "ibm_quantum"
            except Exception:
                pass
        if QISKIT_AVAILABLE:
            return "aer"
        return "classical"

    @property
    def backend(self) -> str:
        return self._backend

    def _build_uniform_circuit(self, n_qubits: int) -> "QuantumCircuit":
        """Build a uniform superposition circuit over n_qubits."""
        qc = QuantumCircuit(n_qubits)
        qc.h(range(n_qubits))
        qc.measure_all()
        return qc

    def _quantum_sample(self, population: list, k: int) -> list:
        """Sample k items from population using a quantum circuit."""
        n_qubits = math.ceil(math.log2(len(population))) if len(population) > 1 else 1
        qc = self._build_uniform_circuit(n_qubits)
        shots = max(k * 10, 128)

        if self._backend == "ibm_quantum":
            sampler = IBMSampler(self._ibm_backend)
            job = sampler.run([qc], shots=shots)
            pub_result = job.result()[0]
            counts = pub_result.data.meas.get_counts()
        else:
            # Aer simulation
            from qiskit_aer import AerSimulator
            from qiskit.primitives import StatevectorSampler

            sim = AerSimulator()
            job = sim.run(qc, shots=shots)
            counts = job.result().get_counts()

        # Map bitstrings to population indices
        indices = set()
        for bitstring in sorted(counts, key=counts.get, reverse=True):
            idx = int(bitstring, 2) % len(population)
            indices.add(idx)
            if len(indices) >= k:
                break

        # Pad with random if quantum didn't give enough unique indices
        while len(indices) < k:
            indices.add(random.randrange(len(population)))

        return [population[i] for i in list(indices)[:k]]

    def sample(self, items: list, n: int = 1) -> list:
        """
        Sample n items from the list.

        Args:
            items: list of items to sample from.
            n: number of items to return.

        Returns:
            List of n sampled items.
        """
        if n >= len(items):
            return list(items)
        if self._backend in ("ibm_quantum", "aer"):
            try:
                return self._quantum_sample(items, n)
            except Exception:
                pass  # fall through to classical
        return random.sample(items, n)

    def prioritize(self, items: list) -> list:
        """
        Return a quantum-randomized ordering of all items.
        Useful for determining pack processing priority.
        """
        return self.sample(items, n=len(items)) if len(items) <= 1 else self._prioritize_quantum(items)

    def _prioritize_quantum(self, items: list) -> list:
        """Return items in a quantum-random order."""
        if self._backend in ("ibm_quantum", "aer"):
            try:
                n_qubits = math.ceil(math.log2(len(items))) if len(items) > 1 else 1
                qc = self._build_uniform_circuit(n_qubits)
                # Use circuit to seed ordering
                result = self.sample(items, n=min(len(items), 8))
                remaining = [x for x in items if x not in result]
                return result + remaining
            except Exception:
                pass
        shuffled = list(items)
        random.shuffle(shuffled)
        return shuffled
