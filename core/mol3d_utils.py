"""3D 分子建模工具 — RDKit 力场优化、能量计算、结构分析"""

import json
from rdkit import Chem
from rdkit.Chem import AllChem, rdDistGeom, rdMolDescriptors


def _parse_mol(data: str):
    """解析 MOL 块 (保留显式 H)"""
    if "\n" in data or "M  END" in data:
        return Chem.MolFromMolBlock(data, removeHs=False)
    return Chem.MolFromSmiles(data)


def smiles_to_3d_molfile(smiles: str) -> str:
    """SMILES → 3D 坐标 → MOL 格式"""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"无效 SMILES: {smiles}")
    mol = Chem.AddHs(mol)
    params = rdDistGeom.ETKDGv3()
    params.randomSeed = 42
    status = rdDistGeom.EmbedMolecule(mol, params)
    if status != 0:
        raise ValueError("3D 坐标生成失败")
    AllChem.MMFFOptimizeMolecule(mol)
    return Chem.MolToMolBlock(mol)


def optimize_geometry(molfile_or_smiles: str):
    """MMFF94 力场优化 → (molfile, energy, converged)"""
    mol = _parse_mol(molfile_or_smiles)
    if mol is None:
        raise ValueError("无法解析输入结构")

    # 确保有 H 和 3D 坐标
    if not _has_explicit_h(mol):
        mol = Chem.AddHs(mol)

    try:
        conf = mol.GetConformer()
        has_3d = conf.Is3D()
    except Exception:
        has_3d = False

    if not has_3d:
        params = rdDistGeom.ETKDGv3()
        params.randomSeed = 42
        rdDistGeom.EmbedMolecule(mol, params)

    ff = AllChem.MMFFGetMoleculeForceField(mol, AllChem.MMFFGetMoleculeProperties(mol))
    if ff is None:
        ff = AllChem.UFFGetMoleculeForceField(mol)

    if ff is None:
        raise ValueError("无法初始化力场 (MMFF94/UFF 均失败)")

    energy_before = ff.CalcEnergy()
    converged = ff.Minimize(maxIts=2000)
    energy_after = ff.CalcEnergy()

    molfile = Chem.MolToMolBlock(mol)

    return {
        "molfile": molfile,
        "energy_before": round(energy_before, 4),
        "energy_after": round(energy_after, 4),
        "energy": round(energy_after, 4),
        "converged": converged == 0,
        "num_atoms": mol.GetNumAtoms(),
        "num_bonds": mol.GetNumBonds(),
    }


def calculate_energy(molfile: str) -> dict:
    """计算分子能量"""
    mol = _parse_mol(molfile)
    if mol is None:
        return {"error": "无法解析结构"}
    if not _has_explicit_h(mol):
        mol = Chem.AddHs(mol)

    ff = AllChem.MMFFGetMoleculeForceField(mol, AllChem.MMFFGetMoleculeProperties(mol))
    if ff is None:
        ff = AllChem.UFFGetMoleculeForceField(mol)
    if ff is None:
        return {"error": "力场初始化失败"}

    return {
        "energy": round(ff.CalcEnergy(), 4),
        "num_atoms": mol.GetNumAtoms(),
    }


def detect_issues(molfile: str) -> dict:
    """检测结构问题"""
    mol = _parse_mol(molfile)
    if mol is None:
        return {"error": "无法解析结构"}
    if not _has_explicit_h(mol):
        mol = Chem.AddHs(mol)

    issues = []
    conf = mol.GetConformer()

    # 检查异常键长
    for bond in mol.GetBonds():
        i, j = bond.GetBeginAtomIdx(), bond.GetEndAtomIdx()
        pi = conf.GetAtomPosition(i)
        pj = conf.GetAtomPosition(j)
        dist = pi.Distance(pj)
        if dist > 3.0:
            issues.append(f"键 {bond.GetBeginAtom().GetSymbol()}-{bond.GetEndAtom().GetSymbol()} 过长 ({dist:.2f} Å)")
        elif dist < 0.7:
            issues.append(f"键 {bond.GetBeginAtom().GetSymbol()}-{bond.GetEndAtom().GetSymbol()} 过短 ({dist:.2f} Å)")

    # 检查近接触 (排除 H-H 和成键对)
    from itertools import combinations
    atom_list = list(range(mol.GetNumAtoms()))
    for i, j in combinations(atom_list, 2):
        bond = mol.GetBondBetweenAtoms(i, j)
        if bond is not None:
            continue
        a1 = mol.GetAtomWithIdx(i)
        a2 = mol.GetAtomWithIdx(j)
        if a1.GetAtomicNum() == 1 and a2.GetAtomicNum() == 1:
            continue
        pi = conf.GetAtomPosition(i)
        pj = conf.GetAtomPosition(j)
        dist = pi.Distance(pj)
        if dist < 0.65:
            issues.append(f"{a1.GetSymbol()}({i})-{a2.GetSymbol()}({j}) 过近 ({dist:.2f} Å)")

    # 力场能量
    try:
        ff = AllChem.MMFFGetMoleculeForceField(mol, AllChem.MMFFGetMoleculeProperties(mol))
    except Exception:
        ff = None
    if ff is None:
        ff = AllChem.UFFGetMoleculeForceField(mol)

    energy = round(ff.CalcEnergy(), 2) if ff else None

    return {
        "issues": issues,
        "is_stable": len(issues) == 0,
        "energy": energy,
        "num_issues": len(issues),
    }


def measure_bond(molfile: str, atom1: int, atom2: int) -> dict:
    """测量键长 (Å)"""
    mol = _parse_mol(molfile)
    if mol is None:
        return {"error": "无法解析"}
    conf = mol.GetConformer()
    p1 = conf.GetAtomPosition(atom1)
    p2 = conf.GetAtomPosition(atom2)
    return {
        "distance": round(p1.Distance(p2), 4),
        "atom1": mol.GetAtomWithIdx(atom1).GetSymbol(),
        "atom2": mol.GetAtomWithIdx(atom2).GetSymbol(),
    }


def measure_angle(molfile: str, atom1: int, atom2: int, atom3: int) -> dict:
    """测量键角 (度)"""
    import math
    mol = _parse_mol(molfile)
    if mol is None:
        return {"error": "无法解析"}
    conf = mol.GetConformer()
    p1 = conf.GetAtomPosition(atom1)
    p2 = conf.GetAtomPosition(atom2)
    p3 = conf.GetAtomPosition(atom3)
    v1 = p1 - p2
    v2 = p3 - p2
    dot = v1.DotProduct(v2)
    mag = v1.Length() * v2.Length()
    if mag == 0:
        return {"error": "原子位置重叠"}
    angle = math.acos(max(-1, min(1, dot / mag)))
    return {
        "angle": round(math.degrees(angle), 2),
        "atom1": mol.GetAtomWithIdx(atom1).GetSymbol(),
        "atom2": mol.GetAtomWithIdx(atom2).GetSymbol(),
        "atom3": mol.GetAtomWithIdx(atom3).GetSymbol(),
    }


def xyz_to_molfile(atoms: list) -> str:
    """从原子列表 [{elem, x, y, z}, ...] 生成 MOL 文件"""
    n = len(atoms)
    lines = ["", "  RDKit", "", f" {n:3d}  0  0  0  0  0  0  0  0999 V2000"]
    for a in atoms:
        elem = a.get("element", "C")
        x, y, z = a.get("x", 0), a.get("y", 0), a.get("z", 0)
        lines.append(f"{x:10.4f}{y:10.4f}{z:10.4f} {elem:<3s} 0  0  0  0  0  0  0  0  0  0  0  0")

    bonds = _auto_bond(atoms)
    for b in bonds:
        lines.append(f"{b['i'] + 1:3d}{b['j'] + 1:3d}{b['order']:3d}  0  0  0  0")

    lines.append("M  END")
    return "\n".join(lines)


def pdb_to_molfile(pdb_data: str) -> str:
    """PDB → MOL2 → MOL"""
    mol = Chem.MolFromPDBBlock(pdb_data, removeHs=False)
    if mol is None:
        raise ValueError("PDB 解析失败")
    return Chem.MolToMolBlock(mol)


def add_hydrogens(molfile_or_smiles: str) -> str:
    """给结构加氢 + 3D 嵌入 + 优化"""
    if "\n" in molfile_or_smiles or "M  END" in molfile_or_smiles:
        mol = Chem.MolFromMolBlock(molfile_or_smiles, removeHs=True)
    else:
        mol = Chem.MolFromSmiles(molfile_or_smiles)
    if mol is None:
        raise ValueError("无法解析结构")
    mol = Chem.AddHs(mol)
    rdDistGeom.EmbedMolecule(mol, randomSeed=42)
    AllChem.MMFFOptimizeMolecule(mol)
    return Chem.MolToMolBlock(mol)


def remove_hydrogens(molfile: str) -> str:
    """去除氢原子"""
    mol = _parse_mol(molfile)
    if mol is None:
        raise ValueError("无法解析结构")
    mol = Chem.RemoveHs(mol)
    return Chem.MolToMolBlock(mol)


# ── 内部工具 ────────────────────────────────────────────────────
COVALENT_RADII = {
    "H": 0.31, "He": 0.28, "Li": 1.28, "Be": 0.96, "B": 0.84,
    "C": 0.73, "N": 0.71, "O": 0.66, "F": 0.57, "Ne": 0.58,
    "Na": 1.66, "Mg": 1.41, "Al": 1.21, "Si": 1.11, "P": 1.07,
    "S": 1.05, "Cl": 1.02, "Ar": 1.06, "K": 2.03, "Ca": 1.76,
    "Sc": 1.70, "Ti": 1.60, "V": 1.53, "Cr": 1.39, "Mn": 1.39,
    "Fe": 1.32, "Co": 1.26, "Ni": 1.24, "Cu": 1.32, "Zn": 1.22,
    "Ga": 1.22, "Ge": 1.20, "As": 1.19, "Se": 1.20, "Br": 1.20,
    "Kr": 1.16, "Rb": 2.20, "I": 1.39,
}


def _auto_bond(atoms: list) -> list:
    """基于原子距离自动判定成键"""
    bonds = []
    n = len(atoms)
    for i in range(n):
        for j in range(i + 1, n):
            ae = atoms[i].get("element", "C")
            be = atoms[j].get("element", "C")
            r1 = COVALENT_RADII.get(ae, 0.7)
            r2 = COVALENT_RADII.get(be, 0.7)
            cutoff = (r1 + r2) * 1.15
            xi, yi, zi = atoms[i].get("x", 0), atoms[i].get("y", 0), atoms[i].get("z", 0)
            xj, yj, zj = atoms[j].get("x", 0), atoms[j].get("y", 0), atoms[j].get("z", 0)
            dist = ((xi - xj) ** 2 + (yi - yj) ** 2 + (zi - zj) ** 2) ** 0.5
            if dist <= cutoff:
                order = 1
                if dist < cutoff * 0.78:
                    order = 2
                if dist < cutoff * 0.65:
                    order = 3
                bonds.append({"i": i, "j": j, "order": order, "distance": round(dist, 3)})
    return bonds


def _has_explicit_h(mol):
    for atom in mol.GetAtoms():
        if atom.GetAtomicNum() == 1:
            return True
    return False
