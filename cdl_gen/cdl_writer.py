"""Serialize ASC CDL values to the standard .cc and .cdl XML file formats."""
from __future__ import annotations

import xml.etree.ElementTree as ET
from xml.dom import minidom

import numpy as np


def identity_values() -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    """Return the no-op CDL: slope 1, offset 0, power 1, saturation 1."""
    return np.ones(3), np.zeros(3), np.ones(3), 1.0


def _fmt_vec3(values: np.ndarray) -> str:
    return " ".join(f"{v:.6f}" for v in values)


def _build_cc_element(
    slope: np.ndarray,
    offset: np.ndarray,
    power: np.ndarray,
    saturation: float,
    cc_id: str,
) -> ET.Element:
    cc = ET.Element("ColorCorrection", {"id": cc_id})
    sop = ET.SubElement(cc, "SOPNode")
    ET.SubElement(sop, "Slope").text = _fmt_vec3(slope)
    ET.SubElement(sop, "Offset").text = _fmt_vec3(offset)
    ET.SubElement(sop, "Power").text = _fmt_vec3(power)
    sat = ET.SubElement(cc, "SatNode")
    ET.SubElement(sat, "Saturation").text = f"{saturation:.6f}"
    return cc


def _prettify(elem: ET.Element) -> str:
    rough = ET.tostring(elem, encoding="utf-8")
    return minidom.parseString(rough).toprettyxml(indent="    ")


def write_cc(
    path: str,
    slope: np.ndarray,
    offset: np.ndarray,
    power: np.ndarray,
    saturation: float,
    cc_id: str = "cc001",
) -> None:
    """Write a standalone ASC Color Correction (.cc) file."""
    cc = _build_cc_element(slope, offset, power, saturation, cc_id)
    with open(path, "w", encoding="utf-8") as f:
        f.write(_prettify(cc))


def write_cdl(
    path: str,
    slope: np.ndarray,
    offset: np.ndarray,
    power: np.ndarray,
    saturation: float,
    cc_id: str = "cc001",
) -> None:
    """Write an ASC Color Decision List (.cdl) file wrapping a single decision."""
    cdl = ET.Element("ColorDecisionList", {"xmlns": "urn:ASC:CDL:v1.2"})
    decision = ET.SubElement(cdl, "ColorDecision")
    decision.append(_build_cc_element(slope, offset, power, saturation, cc_id))
    with open(path, "w", encoding="utf-8") as f:
        f.write(_prettify(cdl))
