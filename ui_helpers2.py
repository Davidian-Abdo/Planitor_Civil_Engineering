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
            sub_discipline="PréparationTerrain", resource_type="Topographe", task_type="supervision", predecessors=["PRE-01"], 
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
