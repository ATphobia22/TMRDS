"""TMRDS FieldLab desktop — offline, no server, no login, local-only.

The GUI never writes patient results or invokes internet services. All clinical
decisions remain with qualified local professionals; this is research-only.
"""
from __future__ import annotations

import json
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engines.fieldlab_local import (
    FieldLabError, inspect_local_file, molecular_descriptors,
    runtime_capabilities,
)
from engines.fieldlab_cube_bridge import create_offline_review_plan


def start() -> None:
    root = tk.Tk()
    root.title("TMRDS FieldLab — Offline Research Inspector")
    root.geometry("850x650")
    root.minsize(620, 460)
    root.configure(background="#132335")

    header = ttk.Frame(root, padding=14)
    header.pack(fill="x")
    ttk.Label(header, text="TMRDS FieldLab", font=("Segoe UI", 18, "bold")).pack(anchor="w")
    ttk.Label(
        header,
        text="Offline files · research methods · no uploads · human clinical review required",
    ).pack(anchor="w")
    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True, padx=12, pady=(0, 12))
    inspect = ttk.Frame(notebook, padding=14)
    chemistry = ttk.Frame(notebook, padding=14)
    deps = ttk.Frame(notebook, padding=14)
    notebook.add(inspect, text="Imaging / genomics / labs")
    notebook.add(chemistry, text="Molecular chemistry")
    notebook.add(deps, text="Installed libraries")

    selected_path = tk.StringVar(value="")
    ttk.Label(inspect, text="Local file: DICOM (.dcm), NIfTI (.nii/.nii.gz), DNA FASTA/FASTQ, or code/value/unit CSV").pack(anchor="w")
    controls = ttk.Frame(inspect)
    controls.pack(fill="x", pady=5)
    path_label = ttk.Label(controls, textvariable=selected_path, wraplength=560)
    path_label.pack(side="left", fill="x", expand=True)

    def browse() -> None:
        path = filedialog.askopenfilename(
            parent=root, title="Select a local clinical research file (no automatic upload)",
            filetypes=[("Supported field research files", "*.dcm *.dicom *.nii *.gz *.fa *.fasta *.fna *.fastq *.fq *.csv"),
                       ("All files", "*.*")]
        )
        if path:
            selected_path.set(path)

    ttk.Button(controls, text="Choose local file", command=browse).pack(side="right", padx=5)
    pixel_flag = tk.BooleanVar(value=False)
    ttk.Checkbutton(
        inspect, variable=pixel_flag,
        text="Decode and summarize DICOM pixels (memory-bounded; requires compatible codec)",
    ).pack(anchor="w", pady=4)
    ttk.Label(
        inspect,
        text="Only open material you are authorized to access. Values are not classified, diagnosed, or sent to a service.",
        wraplength=790,
    ).pack(anchor="w")

    def output_area(parent: ttk.Frame) -> tk.Text:
        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True, pady=10)
        box = tk.Text(frame, height=16, wrap="word", font=("Consolas", 10), undo=False)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=box.yview)
        box.configure(yscrollcommand=scrollbar.set, state="disabled")
        scrollbar.pack(side="right", fill="y")
        box.pack(side="left", fill="both", expand=True)
        return box

    cube_flag = tk.BooleanVar(value=False)
    ttk.Checkbutton(inspect, text="Also simulate Rubik research review plan (not diagnosis)", variable=cube_flag).pack(anchor="w")
    file_output = output_area(inspect)

    def display(box: tk.Text, result: dict) -> None:
        box.configure(state="normal")
        box.delete("1.0", tk.END)
        box.insert("1.0", json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
        box.configure(state="disabled")

    def run_file() -> None:
        if not selected_path.get():
            display(file_output, {"status": "Select a local file; nothing processed"})
            return
        try:
            result = inspect_local_file(
                Path(selected_path.get()), private_local=True,
                include_pixel_summary=pixel_flag.get(),
            )
            if cube_flag.get():
                result = {"fieldlab": result, "cube_review_plan": create_offline_review_plan(result)}
        except (FieldLabError, OSError):
            result = {"status": "file_rejected_or_reader_missing",
                      "note": "No clinical conclusion; review file type, permissions and installed libraries"}
        display(file_output, result)

    ttk.Button(inspect, text="Inspect locally (explicit approval)", command=run_file).pack(anchor="w")

    ttk.Label(chemistry, text="Research-only SMILES (no molecular binding or drug efficacy prediction)").pack(anchor="w")
    smiles_var = tk.StringVar(value="CCO")
    entry = ttk.Entry(chemistry, textvariable=smiles_var)
    entry.pack(fill="x", pady=5)
    chem_cube_flag = tk.BooleanVar(value=False)
    ttk.Checkbutton(chemistry, text="Also simulate molecule evidence-plane review", variable=chem_cube_flag).pack(anchor="w")
    mol_output = output_area(chemistry)

    def run_molecule() -> None:
        try:
            result = molecular_descriptors(smiles_var.get().strip())
            if chem_cube_flag.get():
                result = {"fieldlab": result, "cube_review_plan": create_offline_review_plan(result)}
        except FieldLabError:
            result = {"status": "invalid_molecular_structure_or_reader_missing",
                      "drug_efficacy_inferred": False, "binding_prediction_executed": False}
        display(mol_output, result)

    ttk.Button(chemistry, text="Compute RDKit properties", command=run_molecule).pack(anchor="w")
    dep_output = output_area(deps)

    def update_status() -> None:
        display(dep_output, runtime_capabilities())

    ttk.Button(deps, text="Check actual local imports and versions", command=update_status).pack(anchor="w")
    update_status()
    root.mainloop()


if __name__ == "__main__":
    start()
