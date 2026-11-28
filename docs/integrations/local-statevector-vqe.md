# Local statevector VQE benchmark

## Purpose

TMRDS includes a deterministic, CPU-only statevector simulation as a software
validation benchmark. It demonstrates that the QRCE research runtime can execute
a small quantum-circuit simulation and compare a variational result with exact
diagonalization. It is not a molecular Hamiltonian, biomedical model, drug
screen, treatment optimizer, clinical decision tool, or evidence of quantum
advantage.

## Mathematical problem

The benchmark uses the synthetic two-qubit Hamiltonian H = -Z0 Z1 - X0 X1.
The parameterized circuit RY(theta) on q0 followed by CNOT(q0 -> q1) prepares
cos(theta/2)|00> + sin(theta/2)|11>.

A bounded deterministic grid search minimizes the expectation value of H over
[0, 2*pi]. The exact reference energy is computed independently from the lowest
eigenvalue of the explicit 4-by-4 Hamiltonian matrix. The exact ground energy
is -2 and is attained at theta = pi/2.

## Run offline

From the repository root, with the pinned runtime dependencies installed:

```bash
python scripts/run_local_vqe_benchmark.py --grid-points 721
```

The JSON receipt includes the simulator identifier, circuit, qubit count,
selected parameter, statevector, norm, variational energy, exact reference
energy, absolute error, and a SHA-256 digest over canonical result fields.
The grid must be an odd integer from 21 through 1001.

## Validation

```bash
python -m pytest -q tests/test_quantum_statevector_vqe.py
```

The tests check the exact ground-state result, state normalization, deterministic
receipt digest, and rejection of invalid grid sizes. The broader CI workflows
also run the repository unit suite, dependency checks, security analysis,
offline-workstation integration checks, and platform packaging checks.

## Execution and privacy boundaries

- numpy_statevector_cpu is a classical CPU simulation of quantum state
  amplitudes; it is not execution on physical quantum hardware.
- No IBM Quantum, Amazon Braket, network service, paid compute, or credentials
  are used by this benchmark.
- No patient, clinical, or other personal data is accepted or required.
- hardware_executed, clinical_claim, and quantum_advantage_claim remain false
  in the receipt.
- This benchmark does not validate biomedical hypotheses or establish
  therapeutic efficacy.
