"""化学计算器集合"""

from rdkit import Chem
from rdkit.Chem import Descriptors


def calc_molecular_weight(formula_or_smiles: str) -> float:
    """分子量计算 (分子式或SMILES)"""
    mol = Chem.MolFromSmiles(formula_or_smiles)
    if mol is None:
        # 尝试分子式
        mol = Chem.MolFromSmiles(formula_or_smiles)
    if mol is None:
        raise ValueError(f"无法解析: {formula_or_smiles}")
    return Descriptors.MolWt(mol)


def calc_elemental_analysis(formula_or_smiles: str) -> dict:
    """元素分析 (各元素百分比)"""
    mol = Chem.MolFromSmiles(formula_or_smiles)
    if mol is None:
        raise ValueError(f"无法解析: {formula_or_smiles}")

    formula = Chem.rdMolDescriptors.CalcMolFormula(mol)
    mw = Descriptors.MolWt(mol)

    # 解析分子式
    import re
    elements = {}
    for match in re.finditer(r'([A-Z][a-z]?)(\d*)', formula):
        symbol = match.group(1)
        count = int(match.group(2)) if match.group(2) else 1
        elements[symbol] = count

    pt = Chem.GetPeriodicTable()
    result = {}
    for sym, count in elements.items():
        atomic_mass = pt.GetAtomicWeight(sym)
        mass = atomic_mass * count
        result[sym] = {
            "count": count,
            "mass": round(mass, 4),
            "percent": round(mass / mw * 100, 2),
        }

    return {"formula": formula, "mw": round(mw, 4), "elements": result}


def calc_solution(mass: float = None, volume: float = None,
                  concentration: float = None, mw: float = None) -> dict:
    """溶液配制计算 (m/v/c/MW 四选三)"""
    # c = n/V, n = m/MW, c = m/(MW*V)
    if mass is not None and volume is not None and mw is not None:
        n = mass / mw
        c = n / volume
        return {"moles": round(n, 4), "concentration": round(c, 4)}
    if concentration is not None and volume is not None and mw is not None:
        n = concentration * volume
        mass = n * mw
        return {"moles": round(n, 4), "mass": round(mass, 4)}
    if mass is not None and concentration is not None and mw is not None:
        n = mass / mw
        volume = n / concentration
        return {"moles": round(n, 4), "volume": round(volume, 4)}
    raise ValueError("需要四个参数中的三个: mass, volume, concentration, mw")


def calc_ph(hplus: float = None, poh: float = None, ka: float = None,
            c_acid: float = None, kb: float = None, c_base: float = None) -> dict:
    """pH 计算"""
    if hplus is not None:
        ph = -__import__("math").log10(hplus)
        return {"pH": round(ph, 2), "[H+]": hplus}
    if poh is not None:
        ph = 14 - poh
        return {"pH": round(ph, 2), "pOH": poh}
    # 弱酸近似
    if ka is not None and c_acid is not None:
        import math
        hplus = math.sqrt(ka * c_acid)
        ph = -math.log10(hplus)
        return {"pH": round(ph, 2), "[H+]": round(hplus, 6), "近似": True}
    # 弱碱近似
    if kb is not None and c_base is not None:
        import math
        oh = math.sqrt(kb * c_base)
        poh = -math.log10(oh)
        ph = 14 - poh
        return {"pH": round(ph, 2), "pOH": round(poh, 2), "近似": True}
    raise ValueError("需要 [H+], pOH, (Ka+C_acid) 或 (Kb+C_base)")


def calc_yield(theoretical: float, actual: float) -> dict:
    """产率计算"""
    if theoretical == 0:
        raise ValueError("理论产量不能为 0")
    pct = actual / theoretical * 100
    return {
        "theoretical": theoretical,
        "actual": actual,
        "yield_percent": round(pct, 2),
    }


def calc_dilution(c1: float, v1: float, c2: float = None, v2: float = None) -> dict:
    """稀释计算 c1*v1 = c2*v2"""
    if c2 is None and v2 is not None:
        c2 = c1 * v1 / v2
    elif v2 is None and c2 is not None:
        v2 = c1 * v1 / c2
    else:
        raise ValueError("需要 c2 或 v2")
    return {"c1": c1, "v1": v1, "c2": round(c2, 4), "v2": round(v2, 4)}
