from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Union
from datetime import datetime

# Import models - fixed import path
try:
    from models import WorkerResource, EquipmentResource, BaseTask, Task
except ImportError:
    # Fallback for different project structure
    try:
        from .models import WorkerResource, EquipmentResource, BaseTask, Task
    except ImportError:
        print("❌ Could not import models. Please check the import path.")
        raise

# =======================
# VALIDATION CONSTANTS
# =======================

VALID_DISCIPLINES = {
    'Préliminaires': ['InstallationChantier', 'PréparationTerrain'],
    'Terrassement': ['Décapage', 'Excavation', 'Soutènement Temporaire','Soutènement Permanant'],
    'FondationsProfondes': ['Pieux', 'ParoisMoulées', 'Inclusions', 'MicroPieux'],
    'GrosŒuvre': ['FondationsSuperficielles', 'StructureBéton', 'StructureMétallique'],
    'SecondŒuvre': ['Cloisons', 'Revêtements', 'Menuiseries','Faux-plafond'],
    'Lots techniques': ['CFO','CFA' , 'Ventillation', 'climatisation','Plomberie'],
    'AménagementsExtérieurs': ['VRD', 'EspacesVerts']
}
disciplines=['Préliminaires',
    'Terrassement',
    'FondationsProfondes',
    'GrosŒuvre',
    'SecondŒuvre' ,
    'Lots techniques',
    'AménagementsExtérieurs']
VALID_RESOURCE_TYPES = [
    'BétonArmé', 'Ferrailleur', 'Plaquiste', 'Maçon', 
    'Étanchéiste', 'Staffeur', 'Peintre', 'Topographe', 'Charpentier', 
    'Soudeur', 'Agent de netoyage', 'Ascensoriste', 'Grutier', 'ConducteurEngins',
     'OpérateurMalaxeur', 'OpérateurJetGrouting','Carreleur-Marbrier'
]
# =======================
# WORKER RESOURCES
# =======================
workers = {
    "BétonArmé": WorkerResource(
        "BétonArmé", count=200, hourly_rate=18,
        productivity_rates={
            "GO-F-03": 5, "GO-F-05": 5, "GO-S-03": 5, "GO-S-04": 5, "GO-S-06": 5, "GO-S-07": 12, 
            "FDP-07": 5, "FDP-12": 5, "FDP-15": 5
        },
        skills=["BétonArmé"],
        max_crews={
            "GO-F-03": 25, "GO-F-05": 25, "GO-S-03": 25, "GO-S-04": 25, "GO-S-06": 25, "GO-S-07": 25, 
            "FDP-07": 25, "FDP-12": 25, "FDP-15": 25
        }
    ),

    "Ferrailleur": WorkerResource(
        "Ferrailleur", count=85, hourly_rate=18,
        productivity_rates={
            "FDP-06": 400, "FDP-11": 180, "GO-F-04": 300, "GO-S-02": 180, "GO-S-05": 300
        },
        skills=["BétonArmé"],
        max_crews={
            "FDP-06": 25, "FDP-11": 25, "GO-F-04": 25, "GO-S-02": 25, "GO-S-05": 25
        }
    ),

    "Topographe": WorkerResource(
        "Topographe", count=5, hourly_rate=18,
        productivity_rates={"PRE-01": 100, "PRE-03": 100, "TER-01": 100, "FDP-01": 100, "FDP-02": 100, "FDP-05": 100, "FDP-17": 100},
        skills=["Topographie"],
        max_crews={"PRE-01": 10, "PRE-03": 10, "TER-01": 10, "FDP-01": 10, "FDP-02": 10, "FDP-05": 10, "FDP-17": 10}
    ),

    "Maçon": WorkerResource(
        "Maçon", count=84, hourly_rate=40,
        productivity_rates={"PRE-02": 10, "SO-01": 10},
        skills=["Maçonnerie"],
        max_crews={"PRE-02": 25, "SO-01": 25}
    ),

    "Plaquiste": WorkerResource(
        "Plaquiste", count=84, hourly_rate=40,
        productivity_rates={"SO-02": 10, "SO-03": 10},
        skills=["Cloisennement", "Faux-plafond"],
        max_crews={"SO-02": 25, "SO-03": 25}
    ),

    "Étanchéiste": WorkerResource(
        "Étanchéiste", count=83, hourly_rate=40,
        productivity_rates={"SO-06": 10, "SO-07": 10},
        skills=["Etanchiété"],
        max_crews={"SO-06": 25, "SO-07": 25}
    ),

    "Carreleur-Marbrier": WorkerResource(
        "Carreleur-Marbrier", count=84, hourly_rate=40,
        productivity_rates={"SO-04": 15, "SO-05": 10},
        skills=["Carrelage", "Marbre", "Revetement"],
        max_crews={"SO-04": 15, "SO-05": 15}
    ),

    "Peintre": WorkerResource(
        "Peintre", count=8, hourly_rate=40,
        productivity_rates={"SO-08": 10, "SO-09": 25},
        skills=["Peinture"],
        max_crews={"SO-08": 15, "SO-09": 15}
    ),

    "Charpentier": WorkerResource(
        "Charpentier", count=15, hourly_rate=45,  # Increased count to cover both wood and metal work
        productivity_rates={"GO-S-08": 8, "GO-S-09": 6},
        skills=["Charpenterie", "StructureMétallique"],
        max_crews={"GO-S-08": 10, "GO-S-09": 8}
    ),

    "Soudeur": WorkerResource(
        "Soudeur", count=8, hourly_rate=50,
        productivity_rates={"GO-S-10": 6},
        skills=["Soudure"],
        max_crews={"GO-S-10": 8}
    ),

    "Ascensoriste": WorkerResource(
        "Ascensoriste", count=6, hourly_rate=55,
        productivity_rates={"SO-10": 4},
        skills=["Ascenseurs"],
        max_crews={"SO-10": 6}
    ),

    "Agent de netoyage": WorkerResource(
        "Agent de netoyage", count=15, hourly_rate=25,
        productivity_rates={"SO-11": 100},
        skills=["Nettoyage"],
        max_crews={"SO-11": 10}
    ),
    
    "ConducteurEngins": WorkerResource(
        "ConducteurEngins", count=50, hourly_rate=35,
        productivity_rates={
            "TER-02": 15, "TER-03": 20, "FDP-03": 25, "FDP-04": 15, 
            "FDP-09": 20, "FDP-10": 25, "FDP-13": 20
        },
        skills=["ConduiteEngins"],
        max_crews={
            "TER-02": 10, "TER-03": 15, "FDP-03": 10, "FDP-04": 8, 
            "FDP-09": 10, "FDP-10": 12, "FDP-13": 10
        }
    ),
    
    "OpérateurJetGrouting": WorkerResource(
        "OpérateurJetGrouting", count=12, hourly_rate=45,
        productivity_rates={"FDP-14": 15, "FDP-16": 20},
        skills=["JetGrouting"],
        max_crews={"FDP-14": 6, "FDP-16": 8}
    ),
}


# =======================
# EQUIPMENT RESOURCES
# =======================
equipment = {
    "Chargeuse": EquipmentResource(
        "Chargeuse", count=160, hourly_rate=100,
        productivity_rates={"TER-02": 120, "TER-03": 20, "GO-F-02": 40},
        type="Terrassement", max_equipment=6
    ),

    "Bulldozer": EquipmentResource(
        "Bulldozer", count=16, hourly_rate=100,
        productivity_rates={"TER-02": 200, "TER-03": 20},
        type="Terrassement", max_equipment=6
    ),

    "Pelle": EquipmentResource(
        "Pelle", count=16, hourly_rate=100,
        productivity_rates={"TER-03": 15, "FDP-03": 20},
        type="Terrassement", max_equipment=6
    ),

    "Tractopelle": EquipmentResource(
        "Tractopelle", count=16, hourly_rate=100,
        productivity_rates={"TER-02": 15, "TER-03": 200},
        type="Terrassement", max_equipment=6
    ),

    "Niveleuse": EquipmentResource(
        "Niveleuse", count=16, hourly_rate=100,
        productivity_rates={"GO-F-02": 15},
        type="Terrassement", max_equipment=6
    ),

    "Compacteur": EquipmentResource(
        "Compacteur", count=16, hourly_rate=100,
        productivity_rates={"GO-F-02": 20},
        type="Terrassement", max_equipment=6
    ),

    "Grue à tour": EquipmentResource(
        "Grue à tour", count=180, hourly_rate=150,
        productivity_rates={"GO-F-03": 10, "GO-S-03": 10, "GO-S-06": 10, "SO-01": 10, "SO-02": 10},
        type="Levage", max_equipment=8
    ),

    "Grue mobile": EquipmentResource(
        "Grue mobile", count=90, hourly_rate=150,
        productivity_rates={"FDP-06": 10, "FDP-11": 10, "GO-F-04": 10, "GO-S-02": 10},
        type="Levage", max_equipment=8
    ),

    "Nacelle": EquipmentResource(
        "Nacelle", count=16, hourly_rate=100,
        productivity_rates={"SO-06": 15, "SO-07": 15},
        type="Levage", max_equipment=6
    ),

    "Pump": EquipmentResource(
        "Pump", count=30, hourly_rate=190,
        productivity_rates={"FDP-07": 14, "FDP-12": 16, "GO-F-05": 14, "GO-S-04": 16, "GO-S-07": 16},
        type="Bétonnage", max_equipment=3
    ),

    "Camion": EquipmentResource(
        "Camion", count=9, hourly_rate=190,
        productivity_rates={"TER-03": 120, "FDP-03": 120},
        type="Transport", max_equipment=3
    ),

    "Bétonier": EquipmentResource(
        "Bétonier", count=9, hourly_rate=190,
        productivity_rates={"FDP-07": 14, "FDP-12": 16, "GO-F-05": 14, "GO-S-04": 16, "GO-S-07": 16},
        type="Bétonnage", max_equipment=3
    ),

    "Manito": EquipmentResource(
        "Manito", count=19, hourly_rate=190,
        productivity_rates={"SO-01": 14, "SO-02": 16, "SO-03": 16},
        type="Transport", max_equipment=8
    ),
    
    "Foreuse": EquipmentResource(
        "Foreuse", count=8, hourly_rate=200,
        productivity_rates={"FDP-03": 15, "FDP-13": 20, "FDP-15": 18},
        type="Fondations", max_equipment=4
    ),
    
    "Hydrofraise": EquipmentResource(
        "Hydrofraise", count=4, hourly_rate=300,
        productivity_rates={"FDP-09": 12, "FDP-10": 15},
        type="Fondations", max_equipment=2
    ),
}


# =======================
# BASE TASK DEFINITIONS
# =======================

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
            base_duration=10, min_equipment_needed={"Pelle": 2, "Chargeuse": 1, "Camion": 3},
            min_crews_needed=4, predecessors=["TER-02"], repeat_on_floor=False
        ),
    ],
    
    "FondationsProfondes": [
        # PIEUX FORÉS
        BaseTask(
            id="FDP-01", name="Reconnaissance Géotechnique Complémentaire", discipline="FondationsProfondes",
            sub_discipline="Pieux", resource_type="Topographe", task_type="supervision", base_duration=3,
            predecessors=["TER-03"], repeat_on_floor=False
        ),
        BaseTask(
            id="FDP-02", name="Implantation Axes Pieux", discipline="FondationsProfondes",
            sub_discipline="Pieux", resource_type="Topographe", task_type="worker", base_duration=2,
            min_crews_needed=2, predecessors=["FDP-01"], repeat_on_floor=False
        ),
        BaseTask(
            id="FDP-03", name="Forage des Pieux", discipline="FondationsProfondes",
            sub_discipline="Pieux", resource_type="ConducteurEngins", task_type="equipment", base_duration=15,
            min_equipment_needed={"Foreuse": 2, "Camion": 3}, min_crews_needed=4,
            predecessors=["FDP-02"], repeat_on_floor=False
        ),
        BaseTask(
            id="FDP-04", name="Nettoyage Fond de Fouille", discipline="FondationsProfondes",
            sub_discipline="Pieux", resource_type="ConducteurEngins", task_type="equipment", base_duration=2,
            min_equipment_needed={"Pelle": 1}, min_crews_needed=2,
            predecessors=["FDP-03"], repeat_on_floor=False
        ),
        BaseTask(
            id="FDP-05", name="Contrôle Géotechnique Fond de Fouille", discipline="FondationsProfondes",
            sub_discipline="Pieux", resource_type="Topographe", task_type="supervision", base_duration=1,
            min_crews_needed=1, predecessors=["FDP-04"], repeat_on_floor=False
        ),
        BaseTask(
            id="FDP-06", name="Ferraillage des Pieux", discipline="FondationsProfondes",
            sub_discipline="Pieux", resource_type="Ferrailleur", task_type="worker", base_duration=8,
            min_equipment_needed={"Grue mobile": 1}, min_crews_needed=3,
            predecessors=["FDP-05"], repeat_on_floor=False
        ),
        BaseTask(
            id="FDP-07", name="Bétonnage des Pieux par Trémie", discipline="FondationsProfondes",
            sub_discipline="Pieux", resource_type="BétonArmé", task_type="hybrid", base_duration=6,
            min_equipment_needed={"Bétonier": 2, "Pump": 1}, min_crews_needed=4,
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
            sub_discipline="ParoisMoulées", resource_type="ConducteurEngins", task_type="equipment", base_duration=5,
            min_equipment_needed={"Hydrofraise": 1}, min_crews_needed=3,
            predecessors=["FDP-02"], repeat_on_floor=False
        ),
        BaseTask(
            id="FDP-10", name="Forage Parois Moulées", discipline="FondationsProfondes",
            sub_discipline="ParoisMoulées", resource_type="ConducteurEngins", task_type="equipment", base_duration=12,
            min_equipment_needed={"Hydrofraise": 1}, min_crews_needed=4,
            predecessors=["FDP-09"], repeat_on_floor=False
        ),
        BaseTask(
            id="FDP-11", name="Pose Cage Ferraillage Parois", discipline="FondationsProfondes",
            sub_discipline="ParoisMoulées", resource_type="Ferrailleur", task_type="worker", base_duration=7,
            min_equipment_needed={"Grue mobile": 2}, min_crews_needed=4,
            predecessors=["FDP-10"], repeat_on_floor=False
        ),
        BaseTask(
            id="FDP-12", name="Bétonnage Parois Moulées", discipline="FondationsProfondes",
            sub_discipline="ParoisMoulées", resource_type="BétonArmé", task_type="hybrid", base_duration=8,
            min_equipment_needed={"Bétonier": 3, "Pump": 1}, min_crews_needed=5,
            predecessors=["FDP-11"], repeat_on_floor=False
        ),
        
        # MICROPIEUX ET INCLUSIONS
        BaseTask(
            id="FDP-13", name="Forage MicroPieux", discipline="FondationsProfondes",
            sub_discipline="MicroPieux", resource_type="ConducteurEngins", task_type="equipment", base_duration=10,
            min_equipment_needed={"Foreuse": 3}, min_crews_needed=4,
            predecessors=["FDP-02"], repeat_on_floor=False
        ),
        BaseTask(
            id="FDP-14", name="Injection MicroPieux", discipline="FondationsProfondes",
            sub_discipline="MicroPieux", resource_type="OpérateurJetGrouting", task_type="hybrid", base_duration=6,
            min_equipment_needed={"Pump": 2}, min_crews_needed=3,
            predecessors=["FDP-13"], repeat_on_floor=False
        ),
        BaseTask(
            id="FDP-15", name="Mise en Place Inclusions Rigides", discipline="FondationsProfondes",
            sub_discipline="Inclusions", resource_type="BétonArmé", task_type="equipment", base_duration=8,
            min_equipment_needed={"Foreuse": 2}, min_crews_needed=3,
            predecessors=["FDP-02"], repeat_on_floor=False
        ),
        
        # TRAITEMENTS DE SOL
        BaseTask(
            id="FDP-16", name="Jet Grouting - Colonnes de Sol", discipline="FondationsProfondes",
            sub_discipline="Inclusions", resource_type="OpérateurJetGrouting", task_type="equipment", base_duration=12,
            min_equipment_needed={"Pump": 2}, min_crews_needed=4,
            predecessors=["FDP-01"], repeat_on_floor=False
        ),
        BaseTask(
            id="FDP-17", name="Contrôle Intégrité Pieux par Sismique", discipline="FondationsProfondes",
            sub_discipline="Pieux", resource_type="Topographe", task_type="supervision", base_duration=3,
            min_crews_needed=2, predecessors=["FDP-08"], repeat_on_floor=False
        ),
    ],
    
    "GrosŒuvre": [
        # FONDATIONS SUPERFICIELLES
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
            min_equipment_needed={"Grue à tour": 1}, min_crews_needed=3,
            predecessors=["GO-F-02"], repeat_on_floor=False
        ),
        BaseTask(
            id="GO-F-04", name="Ferraillage Radier", discipline="GrosŒuvre",
            sub_discipline="FondationsSuperficielles", resource_type="Ferrailleur", task_type="worker", base_duration=7,
            min_equipment_needed={"Grue à tour": 1}, min_crews_needed=4,
            predecessors=["GO-F-03"], repeat_on_floor=False
        ),
        BaseTask(
            id="GO-F-05", name="Bétonnage Radier", discipline="GrosŒuvre",
            sub_discipline="FondationsSuperficielles", resource_type="BétonArmé", task_type="hybrid", base_duration=4,
            min_equipment_needed={"Pump": 2, "Bétonier": 3}, min_crews_needed=5,
            predecessors=["GO-F-04"], repeat_on_floor=False
        ),
        
        # SUPERSTRUCTURE
        BaseTask(
            id="GO-S-01", name="Validation Plans Structure EXE", discipline="GrosŒuvre",
            sub_discipline="StructureBéton", resource_type="BétonArmé", task_type="supervision", base_duration=1,
            min_equipment_needed={"Grue à tour": 1}, min_crews_needed=2, predecessors=["GO-F-05"]
        ),
        BaseTask(
            id="GO-S-02", name="Préparation Armatures Poteaux/Voiles", discipline="GrosŒuvre",
            sub_discipline="StructureBéton", resource_type="Ferrailleur", task_type="worker", base_duration=3,
            min_equipment_needed={"Grue mobile": 1}, min_crews_needed=3,
            predecessors=["GO-S-01"], repeat_on_floor=True
        ),
        BaseTask(
            id="GO-S-03", name="Coffrage et Pose Armatures Poteaux/Voiles", discipline="GrosŒuvre",
            sub_discipline="StructureBéton", resource_type="BétonArmé", task_type="hybrid", base_duration=4,
            min_equipment_needed={"Grue à tour": 1}, min_crews_needed=3,
            predecessors=["GO-S-02"], repeat_on_floor=True
        ),
        BaseTask(
            id="GO-S-04", name="Bétonnage Poteaux/Voiles", discipline="GrosŒuvre",
            sub_discipline="StructureBéton", resource_type="BétonArmé", task_type="hybrid", base_duration=2,
            min_equipment_needed={"Pump": 1, "Bétonier": 2}, min_crews_needed=3,
            predecessors=["GO-S-03"], repeat_on_floor=True
        ),
        BaseTask(
            id="GO-S-05", name="Préparation Armatures Planchers", discipline="GrosŒuvre",
            sub_discipline="StructureBéton", resource_type="Ferrailleur", task_type="worker", base_duration=4,
            min_equipment_needed={"Grue à tour": 1}, min_crews_needed=3,
            predecessors=["GO-S-04"], repeat_on_floor=True
        ),
        BaseTask(
            id="GO-S-06", name="Coffrage et Pose Armatures Planchers", discipline="GrosŒuvre",
            sub_discipline="StructureBéton", resource_type="BétonArmé", task_type="hybrid", base_duration=5,
            min_equipment_needed={"Grue à tour": 1}, min_crews_needed=3,
            predecessors=["GO-S-05"], repeat_on_floor=True
        ),
        BaseTask(
            id="GO-S-07", name="Bétonnage Planchers", discipline="GrosŒuvre",
            sub_discipline="StructureBéton", resource_type="BétonArmé", task_type="hybrid", base_duration=3,
            min_equipment_needed={"Pump": 1, "Bétonier": 2}, min_crews_needed=3,
            predecessors=["GO-S-06"], repeat_on_floor=True
        ),
        
        # STRUCTURE MÉTALLIQUE
        BaseTask(
            id="GO-S-08", name="Charpente Métallique", discipline="GrosŒuvre",
            sub_discipline="StructureMétallique", resource_type="Charpentier", task_type="worker", base_duration=8,
            min_equipment_needed={"Grue à tour": 1}, min_crews_needed=3,
            predecessors=["GO-S-07"], repeat_on_floor=True
        ),
        BaseTask(
            id="GO-S-09", name="Assemblage Charpente", discipline="GrosŒuvre",
            sub_discipline="StructureMétallique", resource_type="Charpentier", task_type="worker", base_duration=6,
            min_equipment_needed={"Grue à tour": 1}, min_crews_needed=2,
            predecessors=["GO-S-08"], repeat_on_floor=True
        ),
        BaseTask(
            id="GO-S-10", name="Soudure Structure Métallique", discipline="GrosŒuvre",
            sub_discipline="StructureMétallique", resource_type="Soudeur", task_type="worker", base_duration=4,
            min_crews_needed=2, predecessors=["GO-S-09"], repeat_on_floor=True
        ),
    ],
    
    "SecondŒuvre": [
        BaseTask(
            id="SO-01", name="Maçonnerie", discipline="SecondŒuvre",
            sub_discipline="Cloisons", resource_type="Maçon", task_type="worker", base_duration=4,
            min_equipment_needed={"Manito": 1}, min_crews_needed=3,
            predecessors=["GO-S-07"], repeat_on_floor=True
        ),
        BaseTask(
            id="SO-02", name="Cloisonnement", discipline="SecondŒuvre",
            sub_discipline="Cloisons", resource_type="Plaquiste", task_type="worker", base_duration=4,
            min_equipment_needed={"Manito": 1}, min_crews_needed=3,
            predecessors=["GO-S-07"], repeat_on_floor=True
        ),
         BaseTask(
            id="SO-03", name="Faux-plafond", discipline="SecondŒuvre",
            sub_discipline="Faux-plafond", resource_type="Plaquiste", task_type="worker", base_duration=4,
            min_equipment_needed={"Manito": 1}, min_crews_needed=3,
            predecessors=["GO-S-07"], repeat_on_floor=True
        ),
         BaseTask(
            id="SO-04", name="Carrelage", discipline="SecondŒuvre",
            sub_discipline="Revêtements", resource_type="Carreleur-Marbrier", task_type="worker", base_duration=4,
            min_equipment_needed={"Monte-charge": 1}, min_crews_needed=3,
            predecessors=["SO-01"], repeat_on_floor=True
        ),
        BaseTask(
            id="SO-05", name="Marbre", discipline="SecondŒuvre",
            sub_discipline="Revêtements", resource_type="Carreleur-Marbrier", task_type="worker", base_duration=4,
            min_equipment_needed={"Monte-charge": 1}, min_crews_needed=3,
            predecessors=["SO-01"], repeat_on_floor=True
        ),
        BaseTask(
            id="SO-06", name="Etanchéité Terrasses et Balcons", discipline="SecondŒuvre",
            sub_discipline="Revêtements", resource_type="Étanchéiste", task_type="worker", base_duration=3,
            min_crews_needed=2, predecessors=["SO-01"], repeat_on_floor=True
        ),
        BaseTask(
            id="SO-07", name="Etanchéité des Sales de Bain", discipline="SecondŒuvre",
            sub_discipline="Revêtements", resource_type="Étanchéiste", task_type="worker", base_duration=3,
            min_crews_needed=2, predecessors=["SO-01"], repeat_on_floor=True
        ),
        BaseTask(
            id="SO-08", name="Peinture Intérieure", discipline="SecondŒuvre",
            sub_discipline="Revêtements", resource_type="Peintre", task_type="worker", base_duration=4,
            min_crews_needed=2, predecessors=["SO-02"], repeat_on_floor=True
        ),
        BaseTask(
            id="SO-09", name="Peinture Extérieure", discipline="SecondŒuvre",
            sub_discipline="Revêtements", resource_type="Peintre", task_type="worker", base_duration=3,
            min_equipment_needed={"Nacelle": 1}, min_crews_needed=2,
            predecessors=["SO-08"], repeat_on_floor=True
        ),
        BaseTask(
            id="SO-10", name="Installation Ascenseurs", discipline="SecondŒuvre",
            sub_discipline="Menuiseries", resource_type="Ascensoriste", task_type="worker", base_duration=5,
            min_crews_needed=2, predecessors=["SO-03"], repeat_on_floor=True
        ),
        BaseTask(
            id="SO-11", name="Nettoyage Final", discipline="SecondŒuvre",
            sub_discipline="Revêtements", resource_type="Agent de netoyage", task_type="worker", base_duration=2,
            min_crews_needed=3, predecessors=["SO-09", "SO-10"], repeat_on_floor=True
        ),
    ]
}

# ... (rest of the configuration remains the same - ACCELERATION_FACTORS, CROSS_FLOOR_DEPENDENCIES, QUALITY_GATES, SHIFT_CONFIG, etc.)

acceleration = {
    "Terrassement": {
        "factor": 3.0, 
        "max_crews": 5, 
        "constraints": ["space_availability", "equipment_limits"]
    },
    "FondationsProfondes": {
        "factor": 2.0, 
        "max_crews": 4, 
        "constraints": ["curing_time", "sequential_work", "specialized_equipment"]
    },
    "GrosŒuvre": {
        "factor": 1.5, 
        "max_crews": 3, 
        "constraints": ["curing_time", "structural_sequence"]
    },
    "SecondŒuvre": {
        "factor": 1.2, 
        "max_crews": 4, 
        "constraints": ["space_limitation", "trade_coordination"]
    },
    "default": {
        "factor": 1.0, 
        "max_crews": 2, 
        "constraints": ["quality_requirements"]
    }
}

cross_floor_links= {
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

SHIFT_CONFIG = {
    "default": 1.0,
    "Terrassement": 2.0,
    "FondationsProfondes": 1.8,
    "GrosŒuvre": 1.5,
    "SecondŒuvre": 1.0,
}

# =======================
# HELPER FUNCTIONS
# =======================

def get_discipline_hierarchy() -> Dict[str, Any]:
    """Get the complete discipline hierarchy with sub-disciplines."""
    return VALID_DISCIPLINES.copy()

def get_resource_types() -> List[str]:
    """Get all valid resource types."""
    return VALID_RESOURCE_TYPES.copy()

def validate_task_configuration() -> Dict[str, Any]:
    """
    Validate the default task configuration for consistency.
    
    Returns:
        Dict with validation results and any issues found.
    """
    issues = []
    warnings = []
    
    # Check task ID uniqueness
    task_ids = []
    for discipline, tasks in BASE_TASKS.items():
        for task in tasks:
            if task.id in task_ids:
                issues.append(f"Duplicate task ID: {task.id}")
            task_ids.append(task.id)
    
    # Check resource type validity
    for discipline, tasks in BASE_TASKS.items():
        for task in tasks:
            if task.resource_type not in VALID_RESOURCE_TYPES:
                warnings.append(f"Unknown resource type '{task.resource_type}' in task {task.id}")
    
    # Check discipline validity
    for discipline in BASE_TASKS.keys():
        if discipline not in VALID_DISCIPLINES:
            warnings.append(f"Unknown discipline '{discipline}' in BASE_TASKS")
    
    return {
        "valid": len(issues) == 0,
        "task_count": len(task_ids),
        "issues": issues,
        "warnings": warnings,
        "disciplines_covered": list(BASE_TASKS.keys()),
        "resource_types_used": list(set(task.resource_type for tasks in BASE_TASKS.values() for task in tasks))
    }

# Auto-validate on import
_CONFIG_VALIDATION = validate_task_configuration()

if not _CONFIG_VALIDATION["valid"]:
    print("⚠️  Configuration validation issues found:")
    for issue in _CONFIG_VALIDATION["issues"]:
        print(f"   ❌ {issue}")

if _CONFIG_VALIDATION["warnings"]:
    print("ℹ️  Configuration warnings:")
    for warning in _CONFIG_VALIDATION["warnings"]:
        print(f"   ⚠️  {warning}")

# =======================
# MODULE EXPORTS
# =======================

__all__ = [
    # Resources
    'workers',
    'equipment',
    
    # Task definitions
    'BASE_TASKS',
    
    # Scheduling configuration
    'ACCELERATION_FACTORS',
    'CROSS_FLOOR_DEPENDENCIES',
    'QUALITY_GATES',
    'SHIFT_CONFIG',
    
    # Validation constants
    'VALID_DISCIPLINES',
    'VALID_RESOURCE_TYPES',
    
    # Helper functions
    'get_discipline_hierarchy',
    'get_resource_types',
    'validate_task_configuration',
    
    # Validation results
    '_CONFIG_VALIDATION'
]

print(f"✅ Defaults module loaded: {_CONFIG_VALIDATION['task_count']} tasks across {len(BASE_TASKS)} disciplines")
