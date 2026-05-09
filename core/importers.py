"""化学数据导入器 — PubChem / PDB / ChemSpider / NIST / 文件导入"""

import json
import time
from urllib.parse import quote
import requests

from .chem_utils import smiles_to_mol, mol_to_smiles, inchi_to_smiles


# ===================== PubChem Import =====================

PUBCHEM_BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"


def pubchem_name_to_smiles(name: str) -> str:
    """化合物名称 → SMILES (中英文名/IUPAC名)"""
    url = f"{PUBCHEM_BASE}/compound/name/{quote(name)}/property/CanonicalSMILES/JSON"
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    props = data.get("PropertyTable", {}).get("Properties", [])
    if not props:
        raise ValueError(f"PubChem 未找到: {name}")
    return props[0]["CanonicalSMILES"]


def pubchem_cid_to_smiles(cid: int) -> str:
    """PubChem CID → SMILES"""
    url = f"{PUBCHEM_BASE}/compound/cid/{cid}/property/CanonicalSMILES/JSON"
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    props = data.get("PropertyTable", {}).get("Properties", [])
    if not props:
        raise ValueError(f"PMID not found: {cid}")
    return props[0]["CanonicalSMILES"]


def pubchem_cid_to_sdf(cid: int) -> str:
    """PubChem CID → SDF (3D structure)"""
    url = f"{PUBCHEM_BASE}/compound/cid/{cid}/SDF?record_type=3d"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.text


def pubchem_cid_to_properties(cid: int) -> dict:
    """PubChem CID → 性质数据"""
    url = (f"{PUBCHEM_BASE}/compound/cid/{cid}/property/"
           f"MolecularFormula,MolecularWeight,IUPACName,InChI,InChIKey,"
           f"HBondDonorCount,HBondAcceptorCount,RotatableBondCount,"
           f"XLogP,TPSA,Complexity/JSON")
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    props = data.get("PropertyTable", {}).get("Properties", [])
    return props[0] if props else {}


def pubchem_search(smiles: str, max_results: int = 20) -> list:
    """相似性搜索 PubChem 化合物"""
    url = (f"{PUBCHEM_BASE}/compound/fastsimilarity_2d/smiles/"
           f"{quote(smiles)}/cids/JSON?MaxRecords={max_results}")
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    cids = data.get("IdentifierList", {}).get("CID", [])
    return cids


# ===================== PDB Import =====================

PDB_DOWNLOAD = "https://files.rcsb.org/download"


def pdb_download(pdb_id: str) -> str:
    """PDB ID → PDB 文件内容"""
    pdb_id = pdb_id.strip().upper()
    url = f"{PDB_DOWNLOAD}/{pdb_id}.pdb"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.text


def pdb_download_cif(pdb_id: str) -> str:
    """PDB ID → mmCIF 文件内容"""
    pdb_id = pdb_id.strip().upper()
    url = f"{PDB_DOWNLOAD}/{pdb_id}.cif"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.text


def pdb_metadata(pdb_id: str) -> dict:
    """PDB ID → 元数据 (标题、来源、分辨率等)"""
    url = f"https://data.rcsb.org/rest/v1/core/entry/{pdb_id}"
    resp = requests.get(url, timeout=15)
    if resp.status_code != 200:
        return {}
    return resp.json()


# ===================== ChemSpider Import =====================

def chemspider_name_to_smiles(name: str, api_key: str = None) -> str:
    """ChemSpider 名称 → SMILES (需注册免费 API key)"""
    if not api_key:
        raise ValueError("需要 ChemSpider API key (注册: chemspider.com)")
    # Search by name
    search_url = f"https://api.rsc.org/compounds/v1/filter/name"
    headers = {"apikey": api_key, "Content-Type": "application/json"}
    resp = requests.post(search_url, json={"name": name}, headers=headers, timeout=15)
    resp.raise_for_status()
    results = resp.json().get("results", [])
    if not results:
        raise ValueError(f"ChemSpider 未找到: {name}")
    csid = results[0]
    # Get record
    record_url = f"https://api.rsc.org/compounds/v1/records/{csid}/details"
    resp = requests.get(record_url, headers=headers, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    return data.get("smiles", "")


# ===================== NIST WebBook Import =====================

def nist_webbook_search(name: str) -> dict:
    """NIST Chemistry WebBook 化合物搜索 → 热力学数据"""
    url = f"https://webbook.nist.gov/cgi/cbook.cgi"
    params = {"Name": name, "Units": "SI"}
    resp = requests.get(url, params=params, timeout=20)
    resp.raise_for_status()
    return {"html": resp.text, "url": resp.url}


# ===================== CIF / COD Import =====================

def cod_search(name: str) -> list:
    """Crystallography Open Database 搜索"""
    url = f"https://www.crystallography.net/cod/result.php"
    params = {"search": name, "format": "json"}
    resp = requests.get(url, params=params, timeout=20)
    try:
        data = resp.json()
        return data if isinstance(data, list) else []
    except Exception:
        return []


def cod_download_cif(cod_id: str) -> str:
    """COD ID → CIF 文件内容"""
    url = f"https://www.crystallography.net/cod/{cod_id}.cif"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.text


# ===================== 文件导入 =====================

def import_structure_file(filepath: str) -> dict:
    """导入结构文件 (自动识别格式)"""
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    result = {
        "format": None,
        "smiles": None,
        "molfile": None,
        "pdb_data": None,
        "cif_data": None,
        "error": None,
    }

    ext = filepath.lower()
    try:
        if ext.endswith((".mol", ".sdf")):
            result["format"] = "mol"
            result["molfile"] = content
            mol = Chem.MolFromMolBlock(content)
            if mol:
                result["smiles"] = Chem.MolToSmiles(mol)

        elif ext.endswith(".pdb"):
            result["format"] = "pdb"
            result["pdb_data"] = content

        elif ext.endswith(".cif"):
            result["format"] = "cif"
            result["cif_data"] = content

        elif ext.endswith((".xyz",)):
            result["format"] = "xyz"
            result["molfile"] = content

        elif ext.endswith((".smi", ".smiles")):
            result["format"] = "smiles"
            result["smiles"] = content.strip().split("\n")[0]

        else:
            # 尝试按 SMILES 解析
            test = content.strip().split("\n")[0][:200]
            mol = Chem.MolFromSmiles(test)
            if mol:
                result["format"] = "smiles"
                result["smiles"] = test
            else:
                result["error"] = f"无法识别文件格式: {ext}"

    except Exception as e:
        result["error"] = str(e)

    return result


# 延迟导入 RDKit (避免循环引用)
from rdkit import Chem
