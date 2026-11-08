import scpi


def test_portefeuille_par_defaut_complet():
    attendu = {
        "Pierval Santé",
        "Epargne Pierre",
        "Iroko Zen",
        "Transitions Europe",
        "Corum Origin",
        "Corum XL",
        "Corum Eurion",
        "Remake Live",
    }
    assert set(scpi.PORTEFEUILLE) == attendu


def test_prompt_mentionne_les_scpi():
    prompt = scpi._prompt(["Corum XL", "Remake Live"])
    assert "Corum XL" in prompt and "Remake Live" in prompt
    assert "[Sn]" in prompt