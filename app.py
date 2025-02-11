from flask import Flask, request, jsonify
from collections import defaultdict
import time
import ast

app = Flask(__name__)

def attribuer_logements(presences_alternant, logements):
    # Initialisation des dictionnaires pour stocker les résultats
    resultat = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))
    taux_remplissage = {}
    taux_satisfaction = {}
    
    # Pour chaque alternant, on initialise les résultats et on calcule le nombre total de demandes
    for alternant, annees in presences_alternant.items():
        total_demandes = sum(len(semaines) for (annee, etat), semaines in annees.items() if etat == "En attente")
        total_attribuees = 0
        
        # Pour chaque année et état, on initialise les demandes et les logements disponibles
        for (annee, etat), demandes in annees.items():
            if etat == "En attente":
                demandes = set(demandes)
                logements_disponibles = {logement: set(logements[logement].get((annee, "En attente"), [])) for logement in logements}
                
                # Trier les logements en fonction du nombre de semaines disponibles et de l'attribution existante
                logements_tries = sorted(logements_disponibles.items(), key=lambda x: (-len(x[1]), x[0] in resultat[alternant][annee]["Attribué"]))
                
                # Essayer d'attribuer les logements en une seule passe
                for logement, disponibilites in logements_tries:
                    if not demandes:
                        break
                    
                    # Attribuer les semaines disponibles dans le logement
                    semaines_attribuees = disponibilites & demandes
                    if semaines_attribuees:
                        if not resultat[alternant][annee]["Attribué"].get(logement):
                            resultat[alternant][annee]["Attribué"][logement] = []
                        resultat[alternant][annee]["Attribué"][logement].extend(semaines_attribuees)
                        
                        # Mettre à jour les demandes et les disponibilités des logements
                        demandes -= semaines_attribuees
                        logements[logement][(annee, "En attente")] = list(disponibilites - semaines_attribuees)
                        
                        # Mettre à jour les logements attribués
                        if not isinstance(logements[logement][(annee, "Attribué")], dict):
                            logements[logement][(annee, "Attribué")] = {}
                        if not logements[logement][(annee, "Attribué")].get(alternant):
                            logements[logement][(annee, "Attribué")][alternant] = []
                        logements[logement][(annee, "Attribué")][alternant].extend(semaines_attribuees)
                        
                        # Mettre à jour le nombre total de semaines attribuées
                        total_attribuees += len(semaines_attribuees)
                        
                        # Debugging output
                        print(f"Alternant: {alternant}, Année: {annee}, Logement: {logement}, Semaines attribuées: {semaines_attribuees}")
        
        # Calculer le taux de satisfaction pour l'alternant
        taux_satisfaction[alternant] = (total_attribuees / total_demandes) * 100 if total_demandes else 100
    
    # Calculer le taux de remplissage pour chaque logement et chaque année
    for annee in set(k[0] for logement in logements.values() for k in logement.keys()):
        taux_remplissage[annee] = {}
        for logement, data in logements.items():
            if isinstance(data.get((annee, "Attribué")), dict):
                total_occupees = sum(len(semaines) for semaines in data.get((annee, "Attribué"), {}).values())
            else:
                total_occupees = len(data.get((annee, "Attribué"), []))
            total_semaines = total_occupees + len(data.get((annee, "En attente"), []))
            taux_remplissage[annee][logement] = (total_occupees / total_semaines) * 100 if total_semaines else 0
    
    # Retourner les résultats, les taux de remplissage et les taux de satisfaction
    return resultat, taux_remplissage, taux_satisfaction

def main(presences_alternant, logements):
    # Démarrer le compteur de temps
    start_time = time.time()

    # Appel de la fonction pour attribuer les logements
    resultat, taux_remplissage, taux_satisfaction = attribuer_logements(presences_alternant, logements)

    # Arrêter le compteur de temps
    end_time = time.time()

    # Préparer les résultats pour l'affichage
    result = {
        "attributions_alternants": resultat,
        "taux_remplissage": taux_remplissage,
        "taux_satisfaction": taux_satisfaction,
        "execution_time": end_time - start_time
    }

    return result

@app.route('/attribuer_logements', methods=['POST'])
def attribuer_logements_route():
    data = request.get_json()
    presences_alternant = data.get('presences_alternant')
    logements = data.get('logements')
    
    if not presences_alternant or not logements:
        return jsonify({"error": "Invalid input data"}), 400
    
    # Convertir les clés des dictionnaires en tuples
    presences_alternant = {k: {ast.literal_eval(key): value for key, value in v.items()} for k, v in presences_alternant.items()}
    logements = {k: {ast.literal_eval(key): value for key, value in v.items()} for k, v in logements.items()}
    
    result = main(presences_alternant, logements)
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)