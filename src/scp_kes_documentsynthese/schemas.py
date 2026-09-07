from __future__ import annotations

from typing import Any

STRING_FIELD = {"type": "string"}


def object_schema(properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties.keys()),
        "additionalProperties": False,
    }


JUSTICE_BLOCK = object_schema(
    {
        "gevolgen_draagvlak": STRING_FIELD,
        "gevolgen_vertrouwen": STRING_FIELD,
        "gevolgen_gedrag": STRING_FIELD,
        "elementen_indicatoren_meting": STRING_FIELD,
        "determinanten_onrechtvaardigheid": STRING_FIELD,
        "preventie_en_beleid": STRING_FIELD,
    }
)


PAPER_SCHEMA = {
    "type": "json_schema",
    "name": "climate_energy_justice_paper",
    "strict": True,
    "schema": object_schema(
        {
            "metadata": object_schema(
                {
                    "bronbestand": STRING_FIELD,
                    "titel": STRING_FIELD,
                    "auteurs": STRING_FIELD,
                    "jaar": STRING_FIELD,
                    "studietype": STRING_FIELD,
                    "land_of_context": STRING_FIELD,
                    "onderwerp_of_beleid": STRING_FIELD,
                }
            ),
            "q1_aandacht_en_onvrede": object_schema(
                {
                    "toegenomen_aandacht": STRING_FIELD,
                    "onvrede_burgers_of_groepen": STRING_FIELD,
                }
            ),
            "q2_gevolgen_algemeen": object_schema(
                {
                    "beleid_acceptatie_draagvlak": STRING_FIELD,
                    "duurzaam_gedrag": STRING_FIELD,
                    "vertrouwen": STRING_FIELD,
                }
            ),
            "q3_rechtvaardigheidsconcepten": object_schema(
                {
                    "beschrijving": STRING_FIELD,
                    "labels": {"type": "array", "items": {"type": "string"}},
                }
            ),
            "q4_distributieve_rechtvaardigheid": JUSTICE_BLOCK,
            "q5_procedurele_rechtvaardigheid": JUSTICE_BLOCK,
            "q6_erkennende_rechtvaardigheid": JUSTICE_BLOCK,
            "q7_herstellende_rechtvaardigheid": JUSTICE_BLOCK,
            "q8_overkoepelende_preventie": STRING_FIELD,
        }
    ),
}
