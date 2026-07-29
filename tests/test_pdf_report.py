from reporting.pdf_report import build_match_pdf

_SUMMARY = {
    "teams": {"home": {"name": "Real Madrid"}, "away": {"name": "Paris SG"}},
    "goals": {"home": 3, "away": 1},
    "league": {"name": "Champions League"},
    "date": "2022-03-09T20:00:00+00:00",
}
_RANKED = [
    {"player_id": 1, "name": "Karim Benzema", "team_name": "Real Madrid",
     "position": "Attacker", "minutes": 90, "composite_score": 10.0},
    {"player_id": 2, "name": "Kylian Mbappé", "team_name": "Paris SG",
     "position": "Attacker", "minutes": 90, "composite_score": 6.7},
]
_REPORT = {
    "motm_report": "Benzema a signé un triplé décisif.",
    "player_reports": {"1": "Clinique.", "2": "Dangereux mais isolé."},
    "tactical_suggestions": {"Real Madrid": "Presser haut.", "Paris SG": "Sécuriser la relance."},
    "motm_player_id": 1,
}


def test_build_match_pdf_returns_pdf_bytes():
    pdf = build_match_pdf(_SUMMARY, _RANKED, _REPORT, lang="fr")
    assert isinstance(pdf, (bytes, bytearray))
    assert pdf[:5] == b"%PDF-"           # signature d'un fichier PDF
    assert len(pdf) > 1000               # un vrai document, pas un stub vide


def test_build_match_pdf_english_labels():
    pdf = build_match_pdf(_SUMMARY, _RANKED, _REPORT, lang="en")
    assert pdf[:5] == b"%PDF-"


def test_build_match_pdf_survives_special_characters():
    report = dict(_REPORT, motm_report="Buts & occasions <clés> à l'entrejeu")
    pdf = build_match_pdf(_SUMMARY, _RANKED, report, lang="fr")
    assert pdf[:5] == b"%PDF-"           # l'échappement XML ne casse pas la génération


def test_build_match_pdf_handles_empty_ranking():
    pdf = build_match_pdf(_SUMMARY, [], {"tactical_suggestions": {}}, lang="fr")
    assert pdf[:5] == b"%PDF-"
