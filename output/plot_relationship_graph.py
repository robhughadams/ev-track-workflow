"""Relationship graph of Dr Iain Dykes's network."""
import csv
import math
import os

import matplotlib.pyplot as plt
import networkx as nx

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_PNG = os.path.join(HERE, "plots", "iain_dykes_relationships.png")
OUT_CSV = os.path.join(HERE, "relationship_graph_data.csv")

roles = {
    "Iain Dykes": "iain",
    "Jose M Prieto": "ljmu",
    "Kehinde Ross": "ljmu",
    "Robyn Lotto": "ljmu",
    "Andrew K Powell": "ljmu",
    "Sandra Ortega-Martorell": "ljmu",
    "Fatima Perez de Heredia": "ljmu",
    "Katie Evans": "ljmu",
    "Darren Sexton": "ljmu",
    "Jon Ashley": "ljmu",
    "Mosharraf Sarker": "ljmu",
    "Shaqil Chaudary": "ljmu",
    "Petra Adamova": "phd",
    "Adam Crockett": "phd",
    "Lesley Sloan": "phd",
    "Lise Croft": "family",
    "Claire Harper": "other",
    "Iain Buckingham": "jet",
    "Iain Buchanan": "other",
    "Jason Johnson": "former",
    "Paul Savage": "former",
    "Mark Bond": "former",
    "Elisa A": "former",
    "Jan Fox": "former",
    "Nicola Smart": "former",
    "Peter Scambler": "former",
    "Ayad Eddaoudi": "former",
    "Dorota Szumska-Bilska": "former",
    "Peter Joyce": "former",
    "Sezin Aday Aydin": "ev",
    "Mahmoud Eldahshoury": "ev",
    "Bethy Airstone": "ev",
    "Fahim Razai": "candidate",
    "Himani Taneja": "candidate",
    "Matthew Wenjie Feng": "candidate",
}

institutions = {
    "LJMU": "inst",
    "University of Bristol": "inst",
    "UCL / ICH": "inst",
    "University of Oxford": "inst",
    "EV Community": "inst",
    "University of Liverpool": "inst",
}

node_roles = {**roles, **institutions}

edge_styles = {
    "supervisor": {"color": "#d62728", "style": "solid", "weight": 2.2},
    "coauthor": {"color": "#2ca02c", "style": "dashed", "weight": 1.6},
    "colleague": {"color": "#1f77b4", "style": "solid", "weight": 1.6},
    "former_colleague": {"color": "#7f7f7f", "style": "dashed", "weight": 1.2},
    "50th_invitee": {"color": "#ff7f0e", "style": "dotted", "weight": 2.0},
    "family": {"color": "#9467bd", "style": "dotted", "weight": 2.4},
    "candidate": {"color": "#111111", "style": "dashdot", "weight": 1.8},
    "affiliation": {"color": "#cccccc", "style": "solid", "weight": 0.8},
}

relationships = [
    ("Iain Dykes", "Jose M Prieto", "colleague"),
    ("Iain Dykes", "Kehinde Ross", "colleague"),
    ("Iain Dykes", "Robyn Lotto", "coauthor"),
    ("Iain Dykes", "Andrew K Powell", "coauthor"),
    ("Iain Dykes", "Sandra Ortega-Martorell", "colleague"),
    ("Iain Dykes", "Fatima Perez de Heredia", "colleague"),
    ("Iain Dykes", "Katie Evans", "colleague"),
    ("Iain Dykes", "Darren Sexton", "colleague"),
    ("Iain Dykes", "Jon Ashley", "colleague"),
    ("Iain Dykes", "Mosharraf Sarker", "colleague"),
    ("Iain Dykes", "Shaqil Chaudary", "colleague"),
    ("Iain Dykes", "Petra Adamova", "supervisor"),
    ("Iain Dykes", "Adam Crockett", "supervisor"),
    ("Iain Dykes", "Lesley Sloan", "supervisor"),
    ("Iain Dykes", "Lise Croft", "family"),
    ("Iain Dykes", "Jason Johnson", "former_colleague"),
    ("Iain Dykes", "Paul Savage", "former_colleague"),
    ("Iain Dykes", "Mark Bond", "former_colleague"),
    ("Iain Dykes", "Elisa A", "former_colleague"),
    ("Iain Dykes", "Jan Fox", "former_colleague"),
    ("Iain Dykes", "Nicola Smart", "former_colleague"),
    ("Iain Dykes", "Peter Scambler", "former_colleague"),
    ("Iain Dykes", "Ayad Eddaoudi", "former_colleague"),
    ("Iain Dykes", "Dorota Szumska-Bilska", "former_colleague"),
    ("Iain Dykes", "Peter Joyce", "former_colleague"),
    ("Iain Dykes", "Sezin Aday Aydin", "ev"),
    ("Iain Dykes", "Mahmoud Eldahshoury", "ev"),
    ("Iain Dykes", "Bethy Airstone", "ev"),
    ("Iain Dykes", "Fahim Razai", "candidate"),
    ("Iain Dykes", "Himani Taneja", "candidate"),
    ("Iain Dykes", "Matthew Wenjie Feng", "candidate"),
]

whatsapp_50th = {
    "Jose M Prieto", "Kehinde Ross", "Lesley Sloan", "Robyn Lotto",
    "Lise Croft", "Claire Harper", "Iain Buckingham", "Iain Buchanan",
}
for node in whatsapp_50th:
    relationships.append(("Iain Dykes", node, "50th_invitee"))

affiliations = {
    "Iain Dykes": "LJMU",
    "Jose M Prieto": "LJMU",
    "Kehinde Ross": "LJMU",
    "Robyn Lotto": "LJMU",
    "Andrew K Powell": "LJMU",
    "Sandra Ortega-Martorell": "LJMU",
    "Fatima Perez de Heredia": "LJMU",
    "Katie Evans": "LJMU",
    "Darren Sexton": "LJMU",
    "Jon Ashley": "LJMU",
    "Mosharraf Sarker": "LJMU",
    "Shaqil Chaudary": "LJMU",
    "Petra Adamova": "LJMU",
    "Adam Crockett": "LJMU",
    "Lesley Sloan": "LJMU",
    "Jason Johnson": "University of Bristol",
    "Paul Savage": "University of Bristol",
    "Mark Bond": "University of Bristol",
    "Elisa A": "University of Bristol",
    "Jan Fox": "University of Bristol",
    "Nicola Smart": "University of Bristol",
    "Peter Scambler": "UCL / ICH",
    "Ayad Eddaoudi": "UCL / ICH",
    "Dorota Szumska-Bilska": "University of Oxford",
    "Peter Joyce": "University of Oxford",
    "Sezin Aday Aydin": "EV Community",
    "Mahmoud Eldahshoury": "EV Community",
    "Bethy Airstone": "EV Community",
    "Fahim Razai": "University of Liverpool",
    "Himani Taneja": "University of Liverpool",
    "Matthew Wenjie Feng": "University of Liverpool",
}
for person, inst in affiliations.items():
    relationships.append((person, inst, "affiliation"))

G = nx.Graph()
for src, tgt, etype in relationships:
    G.add_edge(src, tgt, type=etype)

with open(OUT_CSV, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["source", "source_role", "target", "target_role", "relationship_type"])
    for src, tgt, data in G.edges(data=True):
        writer.writerow([src, node_roles.get(src, "other"), tgt, node_roles.get(tgt, "other"), data["type"]])

shape_map = {
    "iain": "s",
    "ljmu": "o",
    "phd": "D",
    "former": "o",
    "ev": "o",
    "family": "h",
    "jet": "X",
    "other": "o",
    "candidate": "P",
    "inst": "s",
}

color_map = {
    "iain": "#8c564b",
    "ljmu": "#1f77b4",
    "phd": "#17becf",
    "former": "#7f7f7f",
    "ev": "#bcbd22",
    "family": "#9467bd",
    "jet": "#e377c2",
    "other": "#999999",
    "candidate": "#ff7f0e",
    "inst": "#2ca02c",
}

size_map = {
    "iain": 3000,
    "candidate": 1700,
    "phd": 1200,
    "ljmu": 950,
    "family": 1300,
    "former": 800,
    "ev": 800,
    "jet": 800,
    "other": 800,
    "inst": 2200,
}

center = "Iain Dykes"
people_nodes = [n for n in G.nodes if node_roles.get(n, "other") != "inst"]
inst_nodes = [n for n in G.nodes if node_roles.get(n, "other") == "inst"]

pos = {center: (0.0, 0.0)}
people_circle = 2.3
for i, n in enumerate(people_nodes):
    if n == center:
        continue
    angle = 2 * math.pi * i / max(1, len(people_nodes) - 1)
    r = people_circle
    if node_roles.get(n) == "candidate":
        r = 2.9
    pos[n] = (r * math.cos(angle), r * math.sin(angle))

inst_radius = 4.4
for i, n in enumerate(inst_nodes):
    angle = 2 * math.pi * i / max(1, len(inst_nodes))
    pos[n] = (inst_radius * math.cos(angle), inst_radius * math.sin(angle))

fig, ax = plt.subplots(figsize=(22, 22), dpi=300)

for src, tgt, data in G.edges(data=True):
    etype = data["type"]
    style = edge_styles.get(etype, edge_styles["affiliation"])
    ax.plot(
        [pos[src][0], pos[tgt][0]],
        [pos[src][1], pos[tgt][1]],
        color=style["color"],
        linestyle=style["style"],
        linewidth=style["weight"],
        alpha=0.8,
        zorder=1,
    )

for node in G.nodes:
    role = node_roles.get(node, "other")
    shape = shape_map.get(role, "o")
    color = color_map.get(role, "#999999")
    size = size_map.get(role, 800)
    ax.scatter(
        pos[node][0], pos[node][1],
        marker=shape, s=size, c=color, edgecolors="black",
        linewidths=1.2, zorder=2, alpha=0.95,
    )
    label = node.replace("Fatima Perez de Heredia", "F. Perez de Heredia")
    ax.annotate(
        label, pos[node],
        textcoords="offset points",
        xytext=(0, 0),
        ha="center", va="center",
        fontsize=7.5 if role != "inst" else 9,
        fontweight="bold" if node == center else "normal",
        zorder=3,
    )

legend_handles = []
for etype, style in edge_styles.items():
    legend_handles.append(
        plt.Line2D([0], [0], color=style["color"], linestyle=style["style"],
                   lw=2, label=etype.replace("_", " ").title())
    )
ax.legend(handles=legend_handles, loc="upper left", bbox_to_anchor=(1.02, 1.0),
          fontsize=9, title="Edge types", title_fontsize=10)

ax.set_title("Dr Iain Dykes — Relationship Network", fontsize=18, fontweight="bold", pad=20)
ax.axis("off")
ax.margins(0.1)
fig.tight_layout()

os.makedirs(os.path.dirname(OUT_PNG), exist_ok=True)
fig.savefig(OUT_PNG, bbox_inches="tight")
print(f"Wrote {OUT_PNG}")
print(f"Wrote {OUT_CSV}")
print(f"Nodes: {G.number_of_nodes()}, Edges: {G.number_of_edges()}")
