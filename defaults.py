from dataclasses import dataclass, field
from typing import List, Optional, Dict
from datetime import datetime
from models import WorkerResource, EquipmentResource, BaseTask, Task  # ← fixed comma issue


# =======================
# WORKER RESOURCES
# =======================
workers = {
    "BétonArmée": WorkerResource(
        "BétonArmée", count=200, hourly_rate=18,
        productivity_rates={
            "3.1": 5, "3.2": 5, "2.1": 5, "3.4": 5, "3.5": 5, "4.1": 12, "3.8": 5, "3.9": 5,
            "3.7": 5, "3.10": 10, "3.11": 10, "3.13": 10, "4.3": 10, "4.4": 10,
            "4.6": 10, "4.7": 10, "4.9": 10, "4.10": 10
        },
        skills=["BétonArmée"],
        max_crews={
            "3.1": 25, "3.2": 25, "2.1": 25, "3.4": 25, "3.5": 25, "4.1": 25, "3.8": 25, "3.9": 25,
            "3.7": 25, "3.10": 25, "3.11": 25, "3.13": 25, "4.3": 25, "4.4": 25,
            "4.6": 25, "4.7": 25, "4.9": 25, "4.10": 25
        }
    ),

    "Férrailleur": WorkerResource(
        "Férrailleur", count=85, hourly_rate=18,
        productivity_rates={
            "3.3": 400, "3.6": 180, "3.12": 300, "4.2": 180, "4.5": 300, "4.8": 120
        },
        skills=["BétonArmée"],
        max_crews={
            "3.3": 25, "3.6": 25, "3.12": 25, "4.2": 25, "4.5": 25, "4.8": 25
        }
    ),

    "Topograph": WorkerResource(
        "Topograph", count=5, hourly_rate=18,
        productivity_rates={"1.3": 100},
        skills=["Topographie"],
        max_crews={"1.3": 10}
    ),

    "ConstMéttalique": WorkerResource(
        "ConstMéttalique", count=3, hourly_rate=60,
        productivity_rates={"9.2": 8},
        skills=["ConstMéttalique"],
        max_crews={"9.2": 10}
    ),

    "Maçon": WorkerResource(
        "Maçon", count=84, hourly_rate=40,
        productivity_rates={"5.1": 10, "6.1": 10},
        skills=["Maçonnerie"],
        max_crews={"5.1": 25, "6.1": 25}
    ),

    "plaquiste": WorkerResource(
        "plaquiste", count=84, hourly_rate=40,
        productivity_rates={"5.2": 10, "5.8": 10, "7.2": 10},
        skills=["Cloisennement", "Faux-plafond"],
        max_crews={"5.2": 25, "5.8": 25, "7.2": 25}
    ),

    "Etanchéiste": WorkerResource(
        "Etanchiété", count=83, hourly_rate=40,
        productivity_rates={"3.10": 10, "5.3": 10},
        skills=["Etanchiété"],
        max_crews={"3.10": 25, "5.3": 25}
    ),

    "Revetement": WorkerResource(
        "Revetement", count=84, hourly_rate=40,
        productivity_rates={"5.4": 15, "5.5": 10, "7.3": 15},
        skills=["Carrelage", "Marbre", "Revetement"],
        max_crews={"5.4": 15, "5.5": 15, "7.3": 15}
    ),

    "Peintre": WorkerResource(
        "Peintre", count=8, hourly_rate=40,
        productivity_rates={"5.6": 10, "7.4": 25},
        skills=["Peinture"],
        max_crews={"5.6": 15, "7.4": 15}
    ),

    "charpentier": WorkerResource(
        "charpentier", count=12, hourly_rate=45,
        productivity_rates={"8.1": 8},
        skills=["Charpenterie"],
        max_crews={"8.1": 10}
    ),

    "Soudeur": WorkerResource(
        "Soudeur", count=8, hourly_rate=50,
        productivity_rates={"8.2": 6},
        skills=["Soudure"],
        max_crews={"8.2": 8}
    ),

    "Ascensoriste": WorkerResource(
        "Ascensoriste", count=6, hourly_rate=55,
        productivity_rates={"9.1": 4},
        skills=["Ascenseurs"],
        max_crews={"9.1": 6}
    ),

    "Agent de Netoyage": WorkerResource(
        "Agent de Netoyage", count=15, hourly_rate=25,
        productivity_rates={"10.1": 100},
        skills=["Nettoyage"],
        max_crews={"10.1": 10}
    ),
}


# =======================
# EQUIPMENT RESOURCES
# =======================
equipment = {
    "Chargeuse": EquipmentResource(
        "Chargeuse", count=160, hourly_rate=100,
        productivity_rates={"2.2": 120, "2.3": 20, "2.4": 40, "2.5": 20, "2.6": 20, "2.7": 20, "2.9": 20},
        type="Terrassement", max_equipment=6
    ),

    "Bulldozer": EquipmentResource(
        "Bulldozer", count=16, hourly_rate=100,
        productivity_rates={"2.1": 15, "2.2": 200, "2.3": 20},
        type="Terrassement", max_equipment=6
    ),

    "Pelle": EquipmentResource(
        "Pelle", count=16, hourly_rate=100,
        productivity_rates={"2.1": 15, "2.2": 200, "2.3": 20},
        type="Terrassement", max_equipment=6
    ),

    "Tractopelle": EquipmentResource(
        "Tractopelle", count=16, hourly_rate=100,
        productivity_rates={"2.1": 15, "2.2": 200, "2.3": 20},
        type="Terrassement", max_equipment=6
    ),

    "Niveleuse": EquipmentResource(
        "Niveleuse", count=16, hourly_rate=100,
        productivity_rates={"2.1": 15, "2.2": 200, "2.3": 20},
        type="Terrassement", max_equipment=6
    ),

    "Compacteur": EquipmentResource(
        "Compacteur", count=16, hourly_rate=100,
        productivity_rates={"2.9": 20},
        type="Terrassement", max_equipment=6
    ),

    "Grue à tour": EquipmentResource(
        "Grue à tour", count=180, hourly_rate=150,
        productivity_rates={"5.1": 10},
        type="Levage", max_equipment=8
    ),

    "Grue mobile": EquipmentResource(
        "Grue mobile", count=90, hourly_rate=150,
        productivity_rates={"5.1": 10},
        type="Levage", max_equipment=8
    ),

    "Nacelle": EquipmentResource(
        "Nacelle", count=16, hourly_rate=100,
        productivity_rates={"2.1": 15, "2.2": 200, "2.3": 20},
        type="Levage", max_equipment=6
    ),

    "Pump": EquipmentResource(
        "Pump", count=30, hourly_rate=190,
        productivity_rates={"3.5": 14, "4.1": 16},
        type="Bétonnage", max_equipment=3
    ),

    "Camion": EquipmentResource(
        "Camion", count=9, hourly_rate=190,
        productivity_rates={"2.10": 120, "2.8": 120},
        type="Transport", max_equipment=3
    ),

    "Bétonier": EquipmentResource(
        "Bétonier", count=9, hourly_rate=190,
        productivity_rates={"3.5": 14, "4.1": 16},
        type="Bétonnage", max_equipment=3
    ),

    "Manito": EquipmentResource(
        "Manito", count=19, hourly_rate=190,
        productivity_rates={"3.5": 14, "4.1": 16},
        type="Transport", max_equipment=8
    ),
}


# =======================
# BASE TASK DEFINITIONS
# =======================
# (kept identical to your original snippet; only fixed typos and syntax)

BASE_TASKS = {
    "Préliminaires": [
        BaseTask(
            id="PRE-01", name="Validation Plan Implantation EXE", discipline="Préliminaires",
            sub_discipline="PréparationTerrain", resource_type="Topographe", task_type="supervision", 
            base_duration=1, predecessors=[], repeat_on_floor=False
        ),
        BaseTask(
            id="PRE-02", name="Installation Chantier - Bases Vie", discipline="Préliminaires",
            sub_discipline="InstallationChantier", resource_type="Maçon", task_type="worker", 
            base_duration=5, repeat_on_floor=False, min_crews_needed=2, predecessors=["PRE-01"]
        ),
        BaseTask(
            id="PRE-03", name="Levé Topographique Initial", discipline="Préliminaires",
            sub_discipline="PréparationTerrain", resource_type="Topographe", predecessors=["PRE-01"], 
            base_duration=2, repeat_on_floor=False, min_crews_needed=1
        ),
    ],
    
    "Terrassement": [
        BaseTask(
            id="TER-01", name="Validation Plans Niveaux EXE", discipline="Terrassement",
            sub_discipline="Excavation", resource_type="Topographe", task_type="supervision", 
            base_duration=1, min_crews_needed=1, predecessors=["PRE-03"], repeat_on_floor=False
        ),
        BaseTask(
            id="TER-02", name="Décapage Terrain Végétal", discipline="Terrassement",
            sub_discipline="Décapage", resource_type="ConducteurEngins", task_type="equipment", 
            base_duration=3, min_equipment_needed={"Bulldozer": 1, "Chargeuse": 1}, 
            min_crews_needed=2, predecessors=["TER-01"], repeat_on_floor=False
        ),
        BaseTask(
            id="TER-03", name="Excavation en Masse", discipline="Terrassement",
            sub_discipline="Excavation", resource_type="ConducteurEngins", task_type="equipment", 
            base_duration=10, min_equipment_needed={"Pelle Hydraulique": 2, "Chargeuse": 1, "Camion": 3},
            min_crews_needed=4, predecessors=["TER-02"], repeat_on_floor=False
        ),
    ],
    
    "FondationsProfondes": [
        # PIEUX FORÉS
        BaseTask(
            id="FDP-01", name="Reconnaissance Géotechnique Complémentaire", discipline="FondationsProfondes",
            sub_discipline="Pieux", resource_type="Foreur", task_type="supervision", base_duration=3,
            predecessors=["TER-03"], repeat_on_floor=False
        ),
        BaseTask(
            id="FDP-02", name="Implantation Axes Pieux", discipline="FondationsProfondes",
            sub_discipline="Pieux", resource_type="Topographe", task_type="worker", base_duration=2,
            min_crews_needed=2, predecessors=["FDP-01"], repeat_on_floor=False
        ),
        BaseTask(
            id="FDP-03", name="Forage des Pieux", discipline="FondationsProfondes",
            sub_discipline="Pieux", resource_type="Foreur", task_type="equipment", base_duration=15,
            min_equipment_needed={"Foreuse": 2, "Camion Benne": 3}, min_crews_needed=4,
            predecessors=["FDP-02"], repeat_on_floor=False
        ),
        BaseTask(
            id="FDP-04", name="Nettoyage Fond de Fouille", discipline="FondationsProfondes",
            sub_discipline="Pieux", resource_type="Foreur", task_type="equipment", base_duration=2,
            min_equipment_needed={"Bennego": 1}, min_crews_needed=2,
            predecessors=["FDP-03"], repeat_on_floor=False
        ),
        BaseTask(
            id="FDP-05", name="Contrôle Géotechnique Fond de Fouille", discipline="FondationsProfondes",
            sub_discipline="Pieux", resource_type="Foreur", task_type="supervision", base_duration=1,
            min_crews_needed=1, predecessors=["FDP-04"], repeat_on_floor=False
        ),
        BaseTask(
            id="FDP-06", name="Ferraillage des Pieux", discipline="FondationsProfondes",
            sub_discipline="Pieux", resource_type="Ferrailleur", task_type="worker", base_duration=8,
            min_equipment_needed={"Grue Mobile": 1}, min_crews_needed=3,
            predecessors=["FDP-05"], repeat_on_floor=False
        ),
        BaseTask(
            id="FDP-07", name="Bétonnage des Pieux par Trémie", discipline="FondationsProfondes",
            sub_discipline="Pieux", resource_type="BétonArmé", task_type="hybrid", base_duration=6,
            min_equipment_needed={"Malaxeur": 2, "Pompe à Béton": 1}, min_crews_needed=4,
            predecessors=["FDP-06"], repeat_on_floor=False
        ),
        BaseTask(
            id="FDP-08", name="Contrôle Béton par Carottage", discipline="FondationsProfondes",
            sub_discipline="Pieux", resource_type="BétonArmé", task_type="supervision", base_duration=4,
            min_crews_needed=1, predecessors=["FDP-07"], repeat_on_floor=False, delay=14
        ),
        
        # PAROIS MOULÉES
        BaseTask(
            id="FDP-09", name="Exécution Parois Moulées Guides", discipline="FondationsProfondes",
            sub_discipline="ParoisMoulées", resource_type="Foreur", task_type="equipment", base_duration=5,
            min_equipment_needed={"Hydrofraise": 1}, min_crews_needed=3,
            predecessors=["FDP-02"], repeat_on_floor=False
        ),
        BaseTask(
            id="FDP-10", name="Forage Parois Moulées", discipline="FondationsProfondes",
            sub_discipline="ParoisMoulées", resource_type="Foreur", task_type="equipment", base_duration=12,
            min_equipment_needed={"Hydrofraise": 1, "Unité de Traitement": 1}, min_crews_needed=4,
            predecessors=["FDP-09"], repeat_on_floor=False
        ),
        BaseTask(
            id="FDP-11", name="Pose Cage Ferraillage Parois", discipline="FondationsProfondes",
            sub_discipline="ParoisMoulées", resource_type="Ferrailleur", task_type="worker", base_duration=7,
            min_equipment_needed={"Grue Mobile": 2}, min_crews_needed=4,
            predecessors=["FDP-10"], repeat_on_floor=False
        ),
        BaseTask(
            id="FDP-12", name="Bétonnage Parois Moulées", discipline="FondationsProfondes",
            sub_discipline="ParoisMoulées", resource_type="BétonArmé", task_type="hybrid", base_duration=8,
            min_equipment_needed={"Tremie": 2, "Malaxeur": 3}, min_crews_needed=5,
            predecessors=["FDP-11"], repeat_on_floor=False
        ),
        
        # MICROPIEUX ET INCLUSIONS
        BaseTask(
            id="FDP-13", name="Forage MicroPieux", discipline="FondationsProfondes",
            sub_discipline="MicroPieux", resource_type="Foreur", task_type="equipment", base_duration=10,
            min_equipment_needed={"Foreuse Légère": 3}, min_crews_needed=4,
            predecessors=["FDP-02"], repeat_on_floor=False
        ),
        BaseTask(
            id="FDP-14", name="Injection MicroPieux", discipline="FondationsProfondes",
            sub_discipline="MicroPieux", resource_type="Foreur", task_type="hybrid", base_duration=6,
            min_equipment_needed={"Unité d'Injection": 2}, min_crews_needed=3,
            predecessors=["FDP-13"], repeat_on_floor=False
        ),
        BaseTask(
            id="FDP-15", name="Mise en Place Inclusions Rigides", discipline="FondationsProfondes",
            sub_discipline="Inclusions", resource_type="BétonArmé", task_type="equipment", base_duration=8,
            min_equipment_needed={"Foreuse": 2, "Vibrofonçage": 1}, min_crews_needed=3,
            predecessors=["FDP-02"], repeat_on_floor=False
        ),
        
        # TRAITEMENTS DE SOL
        BaseTask(
            id="FDP-16", name="Jet Grouting - Colonnes de Sol", discipline="FondationsProfondes",
            sub_discipline="Inclusions", resource_type="OpérateurJetGrouting", task_type="equipment", base_duration=12,
            min_equipment_needed={"Unité Jet Grouting": 2}, min_crews_needed=4,
            predecessors=["FDP-01"], repeat_on_floor=False
        ),
        BaseTask(
            id="FDP-17", name="Contrôle Intégrité Pieux par Sismique", discipline="FondationsProfondes",
            sub_discipline="Pieux", resource_type="Foreur", task_type="supervision", base_duration=3,
            min_crews_needed=2, predecessors=["FDP-08"], repeat_on_floor=False
        ),
    ],
    
    "GrosŒuvre": [
        # FONDATIONS SUPERFICIELLES (moved from old Fondations)
        BaseTask(
            id="GO-F-01", name="Validation Plans Coffrage/Ferraillage Fondations", discipline="GrosŒuvre",
            sub_discipline="FondationsSuperficielles", resource_type="BétonArmé", task_type="supervision", base_duration=1,
            predecessors=["FDP-08", "FDP-12"], repeat_on_floor=False
        ),
        BaseTask(
            id="GO-F-02", name="Préparation Plateforme Radier", discipline="GrosŒuvre",
            sub_discipline="FondationsSuperficielles", resource_type="BétonArmé", task_type="hybrid", base_duration=3,
            min_equipment_needed={"Compacteur": 1, "Niveleuse": 1}, min_crews_needed=2,
            predecessors=["GO-F-01"], repeat_on_floor=False
        ),
        BaseTask(
            id="GO-F-03", name="Coffrage Radier", discipline="GrosŒuvre",
            sub_discipline="FondationsSuperficielles", resource_type="BétonArmé", task_type="hybrid", base_duration=5,
            min_equipment_needed={"Grue à Tour": 1}, min_crews_needed=3,
            predecessors=["GO-F-02"], repeat_on_floor=False
        ),
        BaseTask(
            id="GO-F-04", name="Ferraillage Radier", discipline="GrosŒuvre",
            sub_discipline="FondationsSuperficielles", resource_type="Ferrailleur", task_type="worker", base_duration=7,
            min_equipment_needed={"Grue à Tour": 1}, min_crews_needed=4,
            predecessors=["GO-F-03"], repeat_on_floor=False
        ),
        BaseTask(
            id="GO-F-05", name="Bétonnage Radier", discipline="GrosŒuvre",
            sub_discipline="FondationsSuperficielles", resource_type="BétonArmé", task_type="hybrid", base_duration=4,
            min_equipment_needed={"Pompe à Béton": 2, "Bétonnière": 3}, min_crews_needed=5,
            predecessors=["GO-F-04"], repeat_on_floor=False
        ),
        
        # SUPERSTRUCTURE
        BaseTask(
            id="GO-S-01", name="Validation Plans Structure EXE", discipline="GrosŒuvre",
            sub_discipline="StructureBéton", resource_type="BétonArmé", task_type="supervision", base_duration=1,
            min_equipment_needed={"Grue à Tour": 1}, min_crews_needed=2, predecessors=["GO-F-05"]
        ),
        BaseTask(
            id="GO-S-02", name="Préparation Armatures Poteaux/Voiles", discipline="GrosŒuvre",
            sub_discipline="StructureBéton", resource_type="Ferrailleur", task_type="worker", base_duration=3,
            min_equipment_needed={"Grues Mobiles": 1}, min_crews_needed=3,
            predecessors=["GO-S-01"], repeat_on_floor=True
        ),
        BaseTask(
            id="GO-S-03", name="Coffrage et Pose Armatures Poteaux/Voiles", discipline="GrosŒuvre",
            sub_discipline="StructureBéton", resource_type="BétonArmé", task_type="hybrid", base_duration=4,
            min_equipment_needed={"Grue à Tour": 1}, min_crews_needed=3,
            predecessors=["GO-S-02"], repeat_on_floor=True
        ),
        BaseTask(
            id="GO-S-04", name="Bétonnage Poteaux/Voiles", discipline="GrosŒuvre",
            sub_discipline="StructureBéton", resource_type="BétonArmé", task_type="hybrid", base_duration=2,
            min_equipment_needed={"Pompe à Béton": 1, "Bétonnière": 2}, min_crews_needed=3,
            predecessors=["GO-S-03"], repeat_on_floor=True
        ),
        BaseTask(
            id="GO-S-05", name="Préparation Armatures Planchers", discipline="GrosŒuvre",
            sub_discipline="StructureBéton", resource_type="Ferrailleur", task_type="worker", base_duration=4,
            min_equipment_needed={"Grue à Tour": 1}, min_crews_needed=3,
            predecessors=["GO-S-04"], repeat_on_floor=True
        ),
        BaseTask(
            id="GO-S-06", name="Coffrage et Pose Armatures Planchers", discipline="GrosŒuvre",
            sub_discipline="StructureBéton", resource_type="BétonArmé", task_type="hybrid", base_duration=5,
            min_equipment_needed={"Grue à Tour": 1, "Échafaudages": 1}, min_crews_needed=3,
            predecessors=["GO-S-05"], repeat_on_floor=True
        ),
        BaseTask(
            id="GO-S-07", name="Bétonnage Planchers", discipline="GrosŒuvre",
            sub_discipline="StructureBéton", resource_type="BétonArmé", task_type="hybrid", base_duration=3,
            min_equipment_needed={"Pompe à Béton": 1, "Bétonnière": 2}, min_crews_needed=3,
            predecessors=["GO-S-06"], repeat_on_floor=True
        ),
    ],
    
    "SecondŒuvre": [
        BaseTask(
            id="SO-01", name="Maçonnerie - Cloisons", discipline="SecondŒuvre",
            sub_discipline="Cloisons", resource_type="Maçon", task_type="worker", base_duration=4,
            min_equipment_needed={"Monte-charge": 1}, min_crews_needed=3,
            predecessors=["GO-S-07"], repeat_on_floor=True
        ),
        BaseTask(
            id="SO-02", name="Étanchéité Terrasses et Balcons", discipline="SecondŒuvre",
            sub_discipline="Revêtements", resource_type="Étanchéiste", task_type="worker", base_duration=3,
            min_crews_needed=2, predecessors=["SO-01"], repeat_on_floor=True
        ),
    ]
}

ACCELERATION_FACTORS = {
    "Terrassement": {"factor": 3.0, "max_crews": 5, "constraints": ["space_availability", "equipment_limits"]},
    "FondationsProfondes": {"factor": 2.0, "max_crews": 4, "constraints": ["curing_time", "sequential_work", "specialized_equipment"]},
    "GrosŒuvre": {"factor": 1.5, "max_crews": 3, "constraints": ["curing_time", "structural_sequence"]},
    "SecondŒuvre": {"factor": 1.2, "max_crews": 4, "constraints": ["space_limitation", "trade_coordination"]},
    "default": {"factor": 1.0, "max_crews": 2, "constraints": ["quality_requirements"]}
}

CROSS_FLOOR_DEPENDENCIES = {
    # Deep foundations to superstructure
    "GO-F-01": ["FDP-08", "FDP-12", "FDP-17"],
    
    # Structural dependencies
    "GO-S-04": ["GO-S-07"],  # Columns (F+1) depend on Slab (F)
    "GO-S-05": ["GO-S-07"],  # Plancher prep depends on previous slab
    "GO-S-07": ["GO-S-04"],  # Slab depends on columns from same level
    
    # Quality gates for deep foundations
    "FDP-05": ["FDP-04"],  # Geotechnical control after cleaning
    "FDP-08": ["FDP-07"],  # Core testing after concreting
    "FDP-17": ["FDP-08"],  # Integrity testing after core tests
}

QUALITY_GATES = {
    "PRE-01": "Site Establishment Approval",
    "TER-01": "Earthworks Approval", 
    "FDP-05": "Geotechnical Control - Bottom of Excavation",
    "FDP-08": "Deep Foundations Quality Control",
    "FDP-17": "Integrity Testing Approval",
    "GO-F-01": "Shallow Foundations Approval",
    "GO-S-01": "Structural Works Approval",
    "SO-01": "Enclosed Building Status",
}

cross_floor_links = {
    "2.1": ["1.2"],
    "4.1": ["4.7"],
    "4.2": ["4.7"],
    "4.3": ["4.7"],  # Columns(F+1) depend on Slab(F)
    "4.8": ["4.7"],
    "5.1": ["4.7"],  # Masonry(F) depends on Slab(F) (cross-floor carryover)
    # Waterproofing(F) depends on Masonry(F-1) if needed
    # Add more as project requires
}
# ... keep BASE_TASKS, acceleration, cross_floor_links, and SHIFT_CONFIG as in your version ...
# No need to repeat here unless you want me to check internal logic consistency too.


# =======================
# SHIFT AND ACCELERATION
# =======================
acceleration = {
    "Terrassement": {"factor": 3.0},
    "Fondations": {"factor": 2.0},
    "Superstructure": {"factor": 1.0},
    "default": {"factor": 1.0},
}
disciplines=["Préliminaire","Terrassement","Fondations","Superstructure","SecondeOeuvre"]
cross_floor_links = {
    "2.1": ["1.2"],
    "4.1": ["4.7"],
    "4.2": ["4.7"],
    "4.3": ["4.7"],
    "4.8": ["4.7"],
    "5.1": ["4.7"],
}

SHIFT_CONFIG = {
    "default": 1.0,
    "Terrassement": 2.0,
    "GrosOeuvres": 1.5,
    "SecondeOeuvres": 1.0,
}
