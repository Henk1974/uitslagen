"""Startpunt voor de geïnstalleerde versie: opent direct de webversie, zonder consolevenster."""
import os
import sys

# Zonder consolevenster zijn stdout/stderr None; de server logt daarheen.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

from main import start_webapp

try:
    start_webapp()
except Exception as exc:
    from tkinter import Tk, messagebox

    root = Tk()
    root.withdraw()
    messagebox.showerror("Uitslagen", f"Uitslagen kon niet worden gestart:\n\n{exc}")
