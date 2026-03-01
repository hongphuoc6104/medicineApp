"""
Drug information service — 5 Free Online APIs + Local DB.

Online APIs (all free, no key required):
1. DDI Lab VN Search   — Vietnamese drug search (name, dosage form,
                         ingredients, manufacturer)
2. DDI Lab VN Interact — Drug-drug interactions (Vietnamese!)
3. OpenFDA NDC         — US drug: brand, generic, dosage_form
4. OpenFDA Label       — Usage, warnings, side effects
5. RxNorm (NIH)        — Generic name, RxCUI
6. DailyMed (NIH)      — FDA label link

Local DB:
- pill_information.csv — color, shape (VAIPE data)
- vaipe_drugs_kb.json  — VN drug names, brands
"""

import json
import logging
import re
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent.parent
DRUG_DB = ROOT / "server" / "data" / "drug_db.json"

# Free API endpoints (no key required)
DDI_VN_BASE = "https://ddi.lab.io.vn/api"
OPENFDA_BASE = "https://api.fda.gov/drug"
RXNORM_BASE = "https://rxnav.nlm.nih.gov/REST"
DAILYMED_BASE = (
    "https://dailymed.nlm.nih.gov/dailymed/services/v2"
)


class DrugService:
    """Hybrid drug lookup: local DB + free online APIs."""

    def __init__(self):
        self._db = {}
        self._cache = {}
        self._load_db()

    def _load_db(self):
        if DRUG_DB.exists():
            with open(DRUG_DB, encoding="utf-8") as f:
                self._db = json.load(f)
            logger.info(
                f"Drug DB loaded: {len(self._db)} entries")

    # ── Local lookup (fast, offline) ─────────────────

    def lookup(self, name: str) -> Optional[dict]:
        """Look up drug from local DB."""
        if name in self._db:
            return self._db[name]

        norm = self._normalize(name)
        for key, val in self._db.items():
            if self._normalize(key) == norm:
                return val

        for key, val in self._db.items():
            nk = self._normalize(key)
            if norm in nk or nk in norm:
                return val
        return None

    def search(self, query: str, limit: int = 10) -> list:
        """Search local DB by partial name."""
        q = self._normalize(query)
        results = []
        for key, val in self._db.items():
            k = self._normalize(key)
            brand = self._normalize(val.get("brand", ""))
            if q in k or q in brand:
                results.append(val)
                if len(results) >= limit:
                    break
        return results

    # ══════════════════════════════════════════════════
    #  ONLINE APIs
    # ══════════════════════════════════════════════════

    # ── 1. DDI Lab VN — Vietnamese drug search ───────

    async def search_vn(
        self, query: str, limit: int = 10
    ) -> list:
        """
        Search Vietnamese drugs via ddi.lab.io.vn.

        Returns: list of VN drugs with name, ingredients,
                 dosage form (shape), manufacturer.
        """
        try:
            async with httpx.AsyncClient(
                timeout=10.0
            ) as client:
                url = f"{DDI_VN_BASE}/drugs/search-detailed"
                resp = await client.get(url, params={
                    "q": query, "page": 1, "limit": limit
                })
                if resp.status_code != 200:
                    return []

                data = resp.json()
                results = []
                for d in data.get("drugs", []):
                    entry = {
                        "tenThuoc": d.get(
                            "tenThuoc", "").strip(),
                        "soDangKy": d.get("soDangKy", ""),
                        "hoatChat": [
                            {
                                "ten": h.get(
                                    "tenHoatChat", ""),
                                "nongDo": h.get(
                                    "nongDo", ""),
                            }
                            for h in d.get("hoatChat", [])
                        ],
                        "baoChe": d.get("baoChe", ""),
                        "dongGoi": d.get("dongGoi", ""),
                        "phanLoai": d.get("phanLoai", ""),
                        "congTySx": d.get("congTySx", ""),
                        "nuocSx": d.get("nuocSx", ""),
                        "nhomThuoc": d.get(
                            "nhomThuoc", ""),
                        "source": "ddi.lab.io.vn",
                    }
                    results.append(entry)
                return results
        except Exception as e:
            logger.warning(f"DDI VN search error: {e}")
            return []

    async def suggest_vn(self, query: str) -> list:
        """
        Drug name autocomplete from ddi.lab.io.vn.

        Returns: list of drug name strings.
        """
        try:
            async with httpx.AsyncClient(
                timeout=5.0
            ) as client:
                url = f"{DDI_VN_BASE}/drugs/search"
                resp = await client.get(
                    url, params={"q": query})
                if resp.status_code != 200:
                    return []
                return resp.json()
        except Exception as e:
            logger.warning(f"DDI VN suggest error: {e}")
            return []

    async def interactions(
        self, ingredient: str
    ) -> dict:
        """
        Get drug interactions from ddi.lab.io.vn.

        Args:
            ingredient: Active ingredient name
                        (e.g. "paracetamol")

        Returns: dict with interaction lists
                 grouped by severity.
        """
        try:
            async with httpx.AsyncClient(
                timeout=10.0
            ) as client:
                url = (
                    f"{DDI_VN_BASE}"
                    f"/interactions/by-active-ingredient"
                )
                resp = await client.get(url, params={
                    "ingredientName": ingredient
                })
                if resp.status_code != 200:
                    return {}
                data = resp.json()
                # Simplify the response
                interactions = data.get(
                    "interactions", {})
                simplified = {}
                for severity, items in interactions.items():
                    simplified[severity] = [
                        {
                            "thuoc1": i.get(
                                "hoatChat1", ""),
                            "thuoc2": i.get(
                                "hoatChat2", ""),
                            "canhBao": i.get(
                                "canhBao", ""),
                        }
                        for i in items[:20]
                    ]
                return {
                    "ingredient": ingredient,
                    "total": data.get(
                        "totalInteractions", 0),
                    "interactions": simplified,
                }
        except Exception as e:
            logger.warning(
                f"DDI VN interactions error: {e}")
            return {}

    # ── 2. OpenFDA — US drug info ────────────────────

    async def search_online(
        self, query: str, limit: int = 5
    ) -> list:
        """
        Search drugs online using OpenFDA NDC.

        Returns list of drug entries with brand, generic,
        dosage_form, active ingredients.
        """
        try:
            async with httpx.AsyncClient(
                timeout=10.0
            ) as client:
                clean = re.sub(r'[-_]', ' ', query)
                url = f"{OPENFDA_BASE}/ndc.json"
                resp = await client.get(url, params={
                    "search": (
                        f'brand_name:"{clean}"'
                        f'+generic_name:"{clean}"'
                    ),
                    "limit": limit,
                })
                if resp.status_code != 200:
                    resp = await client.get(url, params={
                        "search": (
                            f'brand_name:"{clean}"'
                        ),
                        "limit": limit,
                    })
                if resp.status_code != 200:
                    return []

                data = resp.json()
                results = []
                for item in data.get("results", []):
                    entry = {
                        "name": item.get(
                            "generic_name", ""),
                        "brand": item.get(
                            "brand_name", ""),
                        "dosage_form": item.get(
                            "dosage_form", ""),
                        "route": ", ".join(
                            item.get("route", [])),
                        "manufacturer": item.get(
                            "labeler_name", ""),
                        "source": "openfda",
                    }
                    ingredients = item.get(
                        "active_ingredients", [])
                    if ingredients:
                        entry["active_ingredients"] = [
                            {
                                "name": i.get("name"),
                                "strength": i.get(
                                    "strength"),
                            }
                            for i in ingredients
                        ]
                    openfda = item.get("openfda", {})
                    if "pharm_class" in openfda:
                        entry["pharm_class"] = openfda[
                            "pharm_class"]
                    results.append(entry)
                return results
        except Exception as e:
            logger.warning(
                f"OpenFDA search error: {e}")
            return []

    # ── 3. Full online lookup (all APIs) ─────────────

    async def lookup_online(self, name: str) -> dict:
        """
        Full online lookup using all APIs.

        Combines: local DB + OpenFDA + RxNorm + DailyMed.
        """
        cache_key = self._normalize(name)
        if cache_key in self._cache:
            return self._cache[cache_key]

        result = self.lookup(name) or {"name": name}

        async with httpx.AsyncClient(
            timeout=10.0
        ) as client:
            ndc = await self._openfda_ndc(client, name)
            if ndc:
                result.update(ndc)

            label = await self._openfda_label(
                client, name)
            if label:
                result.update(label)

            rxnorm = await self._rxnorm(client, name)
            if rxnorm:
                result.update(rxnorm)

            dailymed = await self._dailymed(
                client, name)
            if dailymed:
                result.update(dailymed)

        result["source_online"] = True
        self._cache[cache_key] = result
        return result

    # ── API helpers ──────────────────────────────────

    async def _openfda_ndc(self, client, name):
        """OpenFDA NDC: brand, generic, dosage_form."""
        try:
            clean = re.sub(r'[-_]', ' ', name)
            clean = re.sub(
                r'\d+\s*mg', '', clean,
                flags=re.I).strip()
            url = f"{OPENFDA_BASE}/ndc.json"
            resp = await client.get(url, params={
                "search": f'brand_name:"{clean}"',
                "limit": 1
            })
            if resp.status_code != 200:
                resp = await client.get(url, params={
                    "search": (
                        f'generic_name:"{clean}"'
                    ),
                    "limit": 1
                })
            if resp.status_code != 200:
                return {}

            items = resp.json().get("results", [])
            if not items:
                return {}

            item = items[0]
            result = {
                "fda_brand": item.get(
                    "brand_name", ""),
                "fda_generic": item.get(
                    "generic_name", ""),
                "dosage_form": item.get(
                    "dosage_form", ""),
                "route": ", ".join(
                    item.get("route", [])),
                "manufacturer": item.get(
                    "labeler_name", ""),
            }
            ingredients = item.get(
                "active_ingredients", [])
            if ingredients:
                result["active_ingredients"] = [
                    f"{i['name']} ({i['strength']})"
                    for i in ingredients
                ]
            openfda = item.get("openfda", {})
            if "pharm_class" in openfda:
                result["pharm_class"] = openfda[
                    "pharm_class"]
            return result
        except Exception as e:
            logger.warning(f"OpenFDA NDC err: {e}")
            return {}

    async def _openfda_label(self, client, name):
        """OpenFDA Label: usage, warnings, side_effects."""
        try:
            clean = re.sub(r'[-_]', ' ', name)
            clean = re.sub(
                r'\d+\s*mg', '', clean,
                flags=re.I).strip()
            url = f"{OPENFDA_BASE}/label.json"
            resp = await client.get(url, params={
                "search": (
                    f'openfda.brand_name:"{clean}"'
                ),
                "limit": 1
            })
            if resp.status_code != 200:
                resp = await client.get(url, params={
                    "search": (
                        f'openfda.generic_name:'
                        f'"{clean}"'
                    ),
                    "limit": 1
                })
            if resp.status_code != 200:
                return {}

            items = resp.json().get("results", [])
            if not items:
                return {}

            item = items[0]
            result = {}
            fields = {
                "purpose": "purpose",
                "indications_and_usage": "usage",
                "warnings": "warnings",
                "dosage_and_administration": (
                    "dosage_info"),
                "adverse_reactions": "side_effects",
            }
            for fda_key, our_key in fields.items():
                val = item.get(fda_key)
                if val and isinstance(val, list):
                    text = val[0]
                    text = re.sub(
                        r'\s+', ' ', text).strip()
                    if len(text) > 500:
                        text = text[:497] + "..."
                    result[our_key] = text
            return result
        except Exception as e:
            logger.warning(
                f"OpenFDA Label err: {e}")
            return {}

    async def _rxnorm(self, client, name):
        """RxNorm: generic name, RxCUI."""
        try:
            clean = re.sub(r'[-_]', ' ', name)
            clean = re.sub(
                r'\d+\s*mg', '', clean,
                flags=re.I).strip()
            url = f"{RXNORM_BASE}/drugs.json"
            resp = await client.get(
                url, params={"name": clean})
            if resp.status_code != 200:
                return {}

            groups = resp.json().get(
                "drugGroup", {}).get(
                "conceptGroup", [])
            for group in groups:
                if group.get("tty") == "SCD":
                    props = group.get(
                        "conceptProperties", [])
                    if props:
                        return {
                            "rxcui": props[0].get(
                                "rxcui"),
                            "rxnorm_name": props[0].get(
                                "name"),
                        }
            return {}
        except Exception as e:
            logger.warning(f"RxNorm err: {e}")
            return {}

    async def _dailymed(self, client, name):
        """DailyMed: FDA label link."""
        try:
            clean = re.sub(r'[-_]', ' ', name)
            url = f"{DAILYMED_BASE}/spls.json"
            resp = await client.get(url, params={
                "drug_name": clean, "pagesize": 1
            })
            if resp.status_code != 200:
                return {}

            spls = resp.json().get("data", [])
            if not spls:
                return {}

            setid = spls[0].get("setid")
            return {
                "dailymed_url": (
                    "https://dailymed.nlm.nih.gov/"
                    "dailymed/drugInfo.cfm"
                    f"?setid={setid}"
                ),
            }
        except Exception as e:
            logger.warning(f"DailyMed err: {e}")
            return {}

    # ── Utilities ────────────────────────────────────

    @staticmethod
    def _normalize(s: str) -> str:
        return re.sub(
            r'[^a-z0-9]', '', s.lower().strip())

    def get_all(self) -> dict:
        return self._db

    def count(self) -> int:
        return len(self._db)
