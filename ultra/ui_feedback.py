"""Messages de parcours, sans masquer une erreur derrière une interruption."""

CANCELLATIONS = frozenset({
    "Transfert interrompu ; les fichiers partiels sont conservés.",
    "Vérification interrompue ; reprise possible.",
    "Transfert delta interrompu ; reprise possible.",
})


def outcome(errors, stop_requested=False):
    if not errors:
        return "done"
    if stop_requested and all(text in CANCELLATIONS for text in errors):
        return "stopped"
    return "error"


def error_action(message):
    text = message.casefold()
    if "espace insuffisant" in text or "no space left" in text:
        return "Libérez de l'espace sur la destination, puis reprenez avec les mêmes dossiers."
    if "verrouill" in text:
        return "Vérifiez qu'aucune autre copie n'est active. Après un arrêt brutal, consultez le README avant de retirer le verrou."
    if any(word in text for word in ("conflit", "écrasement", "non prévu", "inventaire différent", "se contenir")):
        return "Choisissez une autre destination vide. Aucun fichier différent ne sera écrasé."
    if any(word in text for word in ("permission", "access is denied", "accès refusé")):
        return "Choisissez un dossier auquel votre compte a accès, ou faites vérifier ses droits."
    if any(word in text for word in ("certificate", "certificat", "ssl")):
        return "Vérifiez l'adresse et le certificat public fourni par l'émetteur. La validation TLS reste obligatoire."
    return "Vérifiez la source et la connexion, puis reprenez avec les mêmes chemins. Consultez le rapport s'il est disponible."
