"""RDKit 化学工具函数"""

from rdkit import Chem
from rdkit.Chem import AllChem, Descriptors, Draw
from rdkit.Chem.Draw import IPythonConsole


def smiles_to_mol(smiles: str):
    """SMILES → RDKit Mol 对象"""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"无法解析 SMILES: {smiles}")
    return mol


def mol_to_smiles(mol) -> str:
    """Mol → 规范 SMILES"""
    return Chem.MolToSmiles(mol, canonical=True)


def mol_to_molfile(mol) -> str:
    """Mol → Molfile"""
    return Chem.MolToMolBlock(mol)


def molfile_to_mol(molfile: str):
    """Molfile → Mol"""
    return Chem.MolFromMolBlock(molfile)


def smiles_to_3d_molfile(smiles: str) -> str:
    """SMILES → 3D 构象 Molfile"""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"无法解析 SMILES: {smiles}")
    mol = Chem.AddHs(mol)
    AllChem.EmbedMolecule(mol, randomSeed=42)
    AllChem.MMFFOptimizeMolecule(mol)
    return Chem.MolToMolBlock(mol)


def inchi_to_smiles(inchi: str) -> str:
    """InChI → SMILES"""
    mol = Chem.MolFromInchi(inchi)
    if mol is None:
        raise ValueError(f"无法解析 InChI: {inchi}")
    return Chem.MolToSmiles(mol)


def smiles_to_inchi(smiles: str) -> str:
    """SMILES → InChI"""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"无法解析 SMILES: {smiles}")
    return Chem.MolToInchi(mol)


def molecular_formula(smiles: str) -> str:
    """SMILES → 分子式"""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return ""
    return Chem.rdMolDescriptors.CalcMolFormula(mol)


def molecular_weight(smiles: str) -> float:
    """SMILES → 分子量"""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return 0.0
    return Descriptors.MolWt(mol)


def detect_functional_groups(smiles: str) -> list:
    """检测分子中的官能团"""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return []

    groups = {
        "醇 (-OH)": "[OX2H]",
        "醛 (-CHO)": "[CX3H1](=O)",
        "酮 (>C=O)": "[CX3](=O)[#6]",
        "羧酸 (-COOH)": "[CX3](=O)[OX2H1]",
        "酯 (-COOR)": "[CX3](=O)[OX2][#6]",
        "酰胺 (-CONH2)": "[CX3](=O)[NX3H2]",
        "胺 (-NH2)": "[NX3H2]",
        "硝基 (-NO2)": "[NX3](=O)=O",
        "腈 (-CN)": "[CX2]#N",
        "苯环": "c1ccccc1",
        "醚 (-O-)": "[OD2]([#6])[#6]",
        "烯烃 (C=C)": "[CX3]=[CX3]",
        "炔烃 (C≡C)": "[CX2]#[CX2]",
    }

    found = []
    for name, smarts in groups.items():
        pattern = Chem.MolFromSmarts(smarts)
        if pattern and mol.HasSubstructMatch(pattern):
            found.append(name)

    return found
