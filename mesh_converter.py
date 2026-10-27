import math
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import BinaryIO

from defusedxml import ElementTree
from defusedxml.common import DefusedXmlException


@dataclass(frozen=True)
class Vessel:
    name: str
    color: str
    edges: list[list[tuple[float, float, float, float]]]


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _color(value: str | None) -> str:
    if value is None or re.fullmatch(r"#[0-9a-fA-F]{6}", value) is None:
        raise ValueError("A vessel has a missing or invalid RGB color.")
    return value.upper()


def read_vessels(xml_file: BinaryIO) -> list[Vessel]:
    try:
        root = ElementTree.parse(xml_file).getroot()
    except (ET.ParseError, DefusedXmlException) as exc:
        raise ValueError(f"Could not parse the XML file: {exc}") from exc

    vessels: list[Vessel] = []
    for vessel_number, element in enumerate(
        (item for item in root.iter() if _local_name(item.tag) == "vessel"), start=1
    ):
        edges: list[list[tuple[float, float, float, float]]] = []
        for edge in element:
            if _local_name(edge.tag) != "edges":
                continue
            for edge_element in edge:
                if _local_name(edge_element.tag) != "edge":
                    continue
                points: list[tuple[float, float, float, float]] = []
                for point_number, point in enumerate(edge_element, start=1):
                    if _local_name(point.tag) != "point":
                        continue
                    try:
                        x, y, z, diameter = (
                            float(point.attrib[key]) for key in ("x", "y", "z", "d")
                        )
                    except (KeyError, ValueError) as exc:
                        raise ValueError(
                            f"Vessel {vessel_number} has an invalid point "
                            f"in edge {edge_element.get('id', '?')} "
                            f"(point {point_number})."
                        ) from exc
                    if not all(math.isfinite(value) for value in (x, y, z, diameter)):
                        raise ValueError(
                            f"Vessel {vessel_number} has a non-finite coordinate "
                            f"or diameter in edge {edge_element.get('id', '?')}."
                        )
                    if diameter <= 0:
                        raise ValueError(
                            f"Vessel {vessel_number} has a non-positive diameter "
                            f"in edge {edge_element.get('id', '?')}."
                        )
                    points.append((x, y, z, diameter))
                if len(points) >= 2:
                    edges.append(points)
        if edges:
            name = element.get("class") or f"Vessel {vessel_number}"
            vessels.append(Vessel(name, _color(element.get("color")), edges))

    if not vessels:
        raise ValueError("No vessel edges with at least two points were found in the XML.")
    return vessels


def _normalize(vector: tuple[float, float, float]) -> tuple[float, float, float]:
    length = math.sqrt(sum(component * component for component in vector))
    if length <= 1e-12:
        raise ValueError("Could not determine a nonzero direction for a vessel edge.")
    return tuple(component / length for component in vector)


def _cross(
    left: tuple[float, float, float], right: tuple[float, float, float]
) -> tuple[float, float, float]:
    return (
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    )


def _subtract(
    left: tuple[float, float, float], right: tuple[float, float, float]
) -> tuple[float, float, float]:
    return (left[0] - right[0], left[1] - right[1], left[2] - right[2])


def _edge_tangents(
    points: list[tuple[float, float, float, float]],
) -> list[tuple[float, float, float]]:
    positions = [point[:3] for point in points]
    tangents = []
    for index, position in enumerate(positions):
        before = next(
            (
                positions[i]
                for i in range(index - 1, -1, -1)
                if positions[i] != position
            ),
            None,
        )
        after = next(
            (
                positions[i]
                for i in range(index + 1, len(positions))
                if positions[i] != position
            ),
            None,
        )
        if before is not None and after is not None:
            direction = _subtract(after, before)
            if sum(component * component for component in direction) <= 1e-24:
                direction = _subtract(after, position)
        elif after is not None:
            direction = _subtract(after, position)
        elif before is not None:
            direction = _subtract(position, before)
        else:
            raise ValueError("A vessel edge contains no measurable length.")
        tangents.append(_normalize(direction))
    return tangents


def _material_name(index: int) -> str:
    return f"vessel_{index:04d}"


def export_obj(
    vessels: list[Vessel], radial_segments: int = 8, max_vertices: int = 2_000_000
) -> tuple[str, str]:
    if radial_segments < 3 or radial_segments > 64:
        raise ValueError("Radial segments must be between 3 and 64.")

    obj_lines = [
        "# Neurolucida vessel centerlines converted to tube meshes",
        "mtllib vessels.mtl",
    ]
    mtl_lines = ["# Vessel colors from the Neurolucida XML"]
    vertex_count = 0

    for vessel_index, vessel in enumerate(vessels, start=1):
        material = _material_name(vessel_index)
        obj_lines.extend((f"o vessel_{vessel_index:04d}", f"usemtl {material}"))
        red, green, blue = (
            int(vessel.color[offset : offset + 2], 16) / 255 for offset in (1, 3, 5)
        )
        mtl_lines.extend(
            (
                f"newmtl {material}",
                f"# {vessel.name}",
                f"Kd {red:.6f} {green:.6f} {blue:.6f}",
                "Ka 0.000000 0.000000 0.000000",
                "Ks 0.000000 0.000000 0.000000",
                "d 1.0",
                "illum 1",
                "",
            )
        )

        for points in vessel.edges:
            required_vertices = len(points) * radial_segments + 2
            if vertex_count + required_vertices > max_vertices:
                raise ValueError(
                    f"The generated mesh exceeds the {max_vertices:,}-vertex limit. "
                    "Use a smaller XML file or reduce the radial segments."
                )
            tangents = _edge_tangents(points)
            first_tangent = tangents[0]
            reference = min(
                ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
                key=lambda axis: abs(sum(a * b for a, b in zip(axis, first_tangent))),
            )
            frame_u = _normalize(_cross(first_tangent, reference))

            rings: list[list[int]] = []
            previous_u = frame_u
            for point, tangent in zip(points, tangents):
                projected_u = tuple(
                    previous_u[i]
                    - sum(previous_u[j] * tangent[j] for j in range(3)) * tangent[i]
                    for i in range(3)
                )
                try:
                    frame_u = _normalize(projected_u)
                except ValueError:
                    reference = min(
                        ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
                        key=lambda axis: abs(sum(a * b for a, b in zip(axis, tangent))),
                    )
                    frame_u = _normalize(_cross(tangent, reference))
                frame_v = _cross(tangent, frame_u)
                previous_u = frame_u
                center = point[:3]
                radius = point[3] / 2.0
                ring = []
                for segment in range(radial_segments):
                    angle = 2.0 * math.pi * segment / radial_segments
                    cosine, sine = math.cos(angle), math.sin(angle)
                    vertex = tuple(
                        center[axis]
                        + radius * (cosine * frame_u[axis] + sine * frame_v[axis])
                        for axis in range(3)
                    )
                    obj_lines.append(f"v {vertex[0]:.6f} {vertex[1]:.6f} {vertex[2]:.6f}")
                    vertex_count += 1
                    ring.append(vertex_count)
                rings.append(ring)

            for ring_index in range(len(rings) - 1):
                current, following = rings[ring_index], rings[ring_index + 1]
                for segment in range(radial_segments):
                    next_segment = (segment + 1) % radial_segments
                    obj_lines.append(
                        f"f {current[segment]} {current[next_segment]} "
                        f"{following[next_segment]} {following[segment]}"
                    )

            start_center = points[0][:3]
            end_center = points[-1][:3]
            obj_lines.append(
                f"v {start_center[0]:.6f} {start_center[1]:.6f} {start_center[2]:.6f}"
            )
            start_index = vertex_count + 1
            obj_lines.append(f"v {end_center[0]:.6f} {end_center[1]:.6f} {end_center[2]:.6f}")
            end_index = vertex_count + 2
            vertex_count += 2
            for segment in range(radial_segments):
                next_segment = (segment + 1) % radial_segments
                obj_lines.append(
                    f"f {start_index} {rings[0][next_segment]} {rings[0][segment]}"
                )
                obj_lines.append(
                    f"f {end_index} {rings[-1][segment]} {rings[-1][next_segment]}"
                )

    return "\n".join(obj_lines) + "\n", "\n".join(mtl_lines) + "\n"
