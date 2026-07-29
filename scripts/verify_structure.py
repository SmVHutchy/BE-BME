"""Strukturpruefung des Repositorys.

Automatisiert drei der Selbstpruefungsfragen, die vor jeder Phasenuebergabe zu
beantworten sind:

  - Wirkt eine der sechs Eingangsgroessen auf mehr als eine Stelle?
  - Gibt es Zahlen im Detektor oder Mapping, die nicht aus params.yaml stammen?
  - Wurde die Interaktionsform festgelegt - auch implizit, durch eine
    Schnittstelle oder ein Config-Feld?

Aufruf aus dem Projektwurzelverzeichnis:

    uv run --with pyyaml python scripts/verify_structure.py

Die Pruefung ist bewusst statisch und ohne Projektabhaengigkeiten: Sie muss
laufen, bevor irgendetwas installiert ist.
"""
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
ok = True


def check(label, condition, detail=""):
    global ok
    print(f"  [{'OK ' if condition else 'FAIL'}] {label}{(' - ' + detail) if detail else ''}")
    if not condition:
        ok = False


# --- 1. params.yaml laedt -----------------------------------------------
print("\n1. Konfiguration laedt")
cfg = yaml.safe_load((ROOT / "config/params.yaml").read_text(encoding="utf-8"))
check("params.yaml ist gueltiges YAML", isinstance(cfg, dict), f"{len(cfg)} Abschnitte")

TOP = {"run", "sim", "field", "flow", "mass", "coupling", "environment",
       "audio", "metrics", "detector", "chronicle", "snapshot", "health", "server"}
check("alle erwarteten Abschnitte vorhanden", TOP <= set(cfg),
      f"fehlt: {TOP - set(cfg) or 'nichts'}")


# --- 2. Genau sechs Kopplungen -----------------------------------------
print("\n2. Kopplungsregel: sechs Eingangsgroessen, sechs Angriffspunkte")
couplings = cfg["coupling"]
check("genau 6 Kopplungsbloecke in params.yaml", len(couplings) == 6,
      ", ".join(couplings))

mapping = (ROOT / "docs/mapping.md").read_text(encoding="utf-8")
# Zeilen der Haupttabelle: beginnen mit "| <ziffer> |"
rows = [r for r in mapping.splitlines() if re.match(r"^\|\s*[1-6]\s*\|", r)]
check("genau 6 Kopplungszeilen in mapping.md", len(rows) == 6, f"{len(rows)} Zeilen")

attack_points = [r.split("|")[5].strip() for r in rows]
check("jeder Angriffspunkt genau einmal", len(set(attack_points)) == 6,
      f"{len(set(attack_points))} verschiedene von {len(attack_points)}")
for a in attack_points:
    print(f"        - {a}")

check("keine siebte Kopplung angelegt", not re.search(r"^\|\s*7\s*\|", mapping, re.M))


# --- 3. In der Doku genannte Config-Schluessel existieren ---------------
print("\n3. Vertrag und Mapping verweisen nur auf vorhandene Schluessel")
docs = {p.name: p.read_text(encoding="utf-8")
        for p in [ROOT / "docs/contract.md", ROOT / "docs/mapping.md"]}

def resolve(path):
    node = cfg
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            return False
        node = node[part]
    return True

# contract.md hat zwei Namensraeume: Nachrichtenfelder (`mass.total`) und
# Konfigurationsschluessel. Letztere sind dort durchgaengig als
# `params.yaml -> schluessel` geschrieben, damit sie unterscheidbar bleiben.
# mapping.md kennt nur Konfigurationsschluessel.
refs = [("contract.md", m) for m in
        re.findall(r"`params\.yaml → ([a-z_]+(?:\.[a-z_]+)*)`", docs["contract.md"])]
refs += [("contract.md", m) for m in
         re.findall(r"`(sim\.[a-z_]+)`", docs["contract.md"])]
refs += [("mapping.md", m) for m in
         re.findall(r"`([a-z_]+(?:\.[a-z_]+)+)`", docs["mapping.md"])
         if m.split(".")[0] in TOP]

missing = [f"{name}: {m}" for name, m in refs if not resolve(m)]
check("alle referenzierten Schluessel aufloesbar", not missing,
      "; ".join(missing) if missing else f"{len(refs)} Verweise geprueft")
check("Konfigurationsverweise im Vertrag sind als solche kenntlich",
      "params.yaml →" in docs["contract.md"])


# --- 4. Interaktionsform nicht festgelegt -------------------------------
print("\n4. Interaktionsform bleibt offen (Expose 6.5)")
forbidden = {"interaction", "voice", "speech", "stt", "tts", "presence", "wake_word"}
found_cfg = forbidden & set(cfg)
check("kein Abschnitt zur Interaktionsform in params.yaml", not found_cfg, str(found_cfg))

dirs = {p.name for p in ROOT.rglob("*") if p.is_dir() and ".git" not in p.parts}
check("kein Modul zur Interaktionsform", not (forbidden & dirs), str(forbidden & dirs))

contract = docs["contract.md"]
check("keine Vertragsnachricht zur Interaktionsform",
      not re.search(r'"(voice|presence|attention|speech)"', contract))


# --- 5. Kein Sprachmodell im Sim-/Detektorpfad --------------------------
print("\n5. Selbstpruefung: kein LLM im Simulationstakt oder in der Erkennung")
detect_doc = (ROOT / "core/src/frame_core/detect/__init__.py").read_text(encoding="utf-8")
check("Detektor als reines Python deklariert", "REINES PYTHON" in detect_doc)
check("Chronikpfad ohne Cloud-Endpunkt",
      cfg["chronicle"]["base_url"].startswith("http://localhost"),
      cfg["chronicle"]["base_url"])
check("Zeitraffer vorhanden und im Bereich 1..100",
      1 <= cfg["sim"]["speed"] <= 100, f"speed={cfg['sim']['speed']}")
check("Massentoleranz gesetzt", cfg["mass"]["drift_tolerance_pct"] == 2.0)
check("Chronik-Rueckfallebene ist Voreinstellung",
      cfg["chronicle"]["backend"] == "single")

print("\n" + ("=" * 60))
print("PHASE 0 ABNAHME: " + ("BESTANDEN" if ok else "NICHT BESTANDEN"))
print("=" * 60)
sys.exit(0 if ok else 1)
