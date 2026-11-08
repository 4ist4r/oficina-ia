"""Catálogo base de temas (dominio, título, artículo de Wikipedia para medir demanda, visual sugerido).
La oficina NO se limita a esta lista: Estrategia puede proponer temas nuevos con búsqueda web y las peticiones del público."""
DOMINIOS = ["robotica", "ingenieria", "espacio", "ciencia", "medicina"]

_RAW = """
robotica|How a robotic arm works|Robotic_arm|iso:brazo_robotico
robotica|How drones fly|Unmanned_aerial_vehicle|iso:dron
robotica|How servo motors work|Servomechanism|2d:engranajes
robotica|How a humanoid robot walks|Humanoid_robot|2d:engranajes
robotica|How self-driving cars see|Self-driving_car|iso:rover
robotica|How robot vacuum cleaners navigate|Robotic_vacuum_cleaner|iso:rover
robotica|How industrial robots build cars|Industrial_robot|iso:brazo_robotico
robotica|How exoskeletons work|Powered_exoskeleton|iso:brazo_robotico
robotica|How a stepper motor works|Stepper_motor|2d:engranajes
robotica|How Mars rovers drive|Mars_rover|iso:rover
robotica|How warehouse robots move packages|Automated_guided_vehicle|iso:cinta
robotica|How a robot gripper works|Robot_end_effector|iso:brazo_robotico
ingenieria|How a rotary engine works|Wankel_engine|2d:rotor
ingenieria|How a car engine works|Four-stroke_engine|iso:motor_abierto
ingenieria|How a jet engine works|Jet_engine|2d:turbina
ingenieria|How a ship engine works|Marine_propulsion|2d:piston
ingenieria|How gears work|Gear|iso:tren_engranajes
ingenieria|How a wind turbine works|Wind_turbine|iso:aerogenerador
ingenieria|How a tower crane works|Tower_crane|iso:grua
ingenieria|How a ferris wheel works|Ferris_wheel|iso:noria
ingenieria|How a camshaft works|Camshaft|2d:levas
ingenieria|How a conveyor belt works|Conveyor_belt|iso:cinta
ingenieria|How a hydraulic press works|Hydraulic_press|2d:flujo
ingenieria|How a dam makes electricity|Hydroelectricity|2d:flujo
ingenieria|How a diesel engine works|Diesel_engine|iso:motor_abierto
ingenieria|How a transmission works|Transmission_(mechanical_device)|iso:tren_engranajes
ingenieria|How suspension springs work|Suspension_(vehicle)|2d:resorte
ingenieria|How an electric motor works|Electric_motor|2d:circuito
ingenieria|How a nuclear reactor works|Nuclear_reactor|2d:flujo
ingenieria|How 3D printers work|3D_printing|iso:brazo_robotico
ingenieria|How bridges hold weight|Bridge|iso:grua
espacio|How rockets launch|Rocket_launch|iso:cohete
espacio|How the solar system moves|Solar_System|2d:orbitas
espacio|How satellites stay in orbit|Satellite|iso:satelite
espacio|How the International Space Station works|International_Space_Station|iso:estacion_espacial
espacio|How black holes work|Black_hole|2d:orbitas
espacio|How the Moon causes tides|Tide|2d:orbitas
espacio|How GPS works|Global_Positioning_System|iso:satelite
espacio|How spacesuits keep astronauts alive|Space_suit|2d:flujo
espacio|How a space telescope sees|James_Webb_Space_Telescope|iso:satelite
espacio|How rockets land themselves|Reusable_launch_vehicle|iso:cohete
espacio|How eclipses happen|Eclipse|2d:orbitas
espacio|How Mars missions work|Mars|iso:rover
espacio|How ion engines work|Ion_thruster|2d:flujo
espacio|How stars are born|Star_formation|2d:orbitas
espacio|How gravity assists work|Gravity_assist|2d:orbitas
ciencia|How atoms are built|Atom|iso:atomo
ciencia|How DNA stores information|DNA|iso:adn
ciencia|How electricity flows|Electric_current|2d:circuito
ciencia|How waves interfere|Wave_interference|2d:ondas
ciencia|How a pendulum swings|Pendulum|2d:pendulo
ciencia|How springs store energy|Hooke%27s_law|2d:resorte
ciencia|How volcanoes erupt|Volcano|iso:volcan
ciencia|How water molecules behave|Properties_of_water|iso:molecula_agua
ciencia|How sound travels|Sound|2d:ondas
ciencia|How light bends in a lens|Lens|2d:ondas
ciencia|How magnets work|Magnetism|2d:circuito
ciencia|How lightning forms|Lightning|2d:circuito
ciencia|How earthquakes happen|Earthquake|iso:volcan
ciencia|How batteries work|Battery_(electricity)|2d:circuito
ciencia|How chemical reactions release energy|Chemical_reaction|iso:molecula_agua
ciencia|How the water cycle works|Water_cycle|2d:flujo
ciencia|How nuclear fusion works|Nuclear_fusion|iso:atomo
medicina|How the heart pumps blood|Heart|2d:corazon
medicina|How neurons send signals|Neuron|2d:neurona
medicina|How lungs breathe|Lung|2d:pulmones
medicina|How viruses infect cells|Virus|iso:virus
medicina|How vaccines train the immune system|Vaccine|iso:virus
medicina|How DNA is copied|DNA_replication|iso:adn
medicina|How an MRI scanner works|Magnetic_resonance_imaging|iso:atomo
medicina|How blood flows through the body|Circulatory_system|2d:flujo
medicina|How antibiotics kill bacteria|Antibiotic|iso:virus
medicina|How the kidneys filter blood|Kidney|2d:flujo
medicina|How pacemakers work|Artificial_cardiac_pacemaker|2d:corazon
medicina|How CRISPR edits genes|CRISPR|iso:adn
medicina|How the brain controls movement|Motor_cortex|2d:neurona
medicina|How an ECG works|Electrocardiography|2d:corazon
medicina|How the immune system fights infection|Immune_system|iso:virus
"""

def catalogo():
    out = []
    for fila in _RAW.strip().splitlines():
        dom, tema, wiki, vis = fila.split("|")
        out.append({"dominio": dom, "tema": tema, "wiki": wiki, "visual": vis})
    return out
