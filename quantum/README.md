# ConductorX — Quantum-Hybrid Sampler (Component 3)

Optional quantum-enhanced module that provides probabilistic sampling and
prioritization using IBM Quantum hardware, with automatic fallback to
Qiskit Aer simulation and classical Python random.

## Backend Priority

| Priority | Backend | Requirement |
|---|---|---|
| 1 | IBM Quantum hardware | `IBM_QUANTUM_TOKEN` env var + `qiskit-ibm-runtime` |
| 2 | Qiskit Aer (local sim) | `qiskit-aer` installed |
| 3 | Python `random` | always available |

## Setup

```bash
# Minimal (classical fallback only)
# No installation needed

# With Qiskit Aer simulation
pip install -r quantum/requirements.txt

# With IBM Quantum hardware
pip install -r quantum/requirements.txt
export IBM_QUANTUM_TOKEN=your_ibm_quantum_api_token
# Get token from: https://quantum.ibm.com/
```

## Usage

```python
from quantum.sampler import QuantumSampler

sampler = QuantumSampler()
print(f"Using backend: {sampler.backend}")  # ibm_quantum / aer / classical

# Sample 2 packs from a list
packs = ["pokemon", "starwars", "pikachu-enfadao", "gits", "bmo"]
selected = sampler.sample(packs, n=2)
print(selected)  # e.g. ["gits", "bmo"]

# Quantum-randomized processing order
order = sampler.prioritize(packs)
print(order)
```

## Use Cases in This Repo

- **Batch prioritization**: determine which packs to process first in a large batch
- **Random sampling for CI**: run checks on a random subset of packs on each PR
- **Preview selection**: randomly select which packs get preview regeneration
