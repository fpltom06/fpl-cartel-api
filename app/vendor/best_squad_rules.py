"""Unchanged Best Squad functions extracted from the original Streamlit app."""
import pandas as pd
POSITION_ORDER=["GK","DEF","MID","FWD"]

def solve_squad_with_scipy(candidates: pd.DataFrame, objective_column: str, budget: float) -> pd.DataFrame | None:
    try:
        import numpy as np
        from scipy.optimize import Bounds, LinearConstraint, milp
    except ImportError:
        return None

    candidate_count = len(candidates)
    points = candidates[objective_column].to_numpy(dtype=float)
    prices = candidates["Price"].to_numpy(dtype=float)

    equality_rows = [np.ones(candidate_count)]
    equality_targets = [15]
    for position, count in {"GK": 2, "DEF": 5, "MID": 5, "FWD": 3}.items():
        equality_rows.append((candidates["Position"].to_numpy() == position).astype(float))
        equality_targets.append(count)

    inequality_rows = [prices]
    inequality_limits = [budget]
    for club in sorted(candidates["Club"].dropna().unique()):
        inequality_rows.append((candidates["Club"].to_numpy() == club).astype(float))
        inequality_limits.append(3)

    constraints = [
        LinearConstraint(
            np.vstack(equality_rows),
            np.array(equality_targets, dtype=float),
            np.array(equality_targets, dtype=float),
        ),
        LinearConstraint(
            np.vstack(inequality_rows),
            -np.inf,
            np.array(inequality_limits, dtype=float),
        ),
    ]

    result = milp(
        c=-points,
        integrality=np.ones(candidate_count),
        bounds=Bounds(0, 1),
        constraints=constraints,
    )
    if not result.success:
        return None

    selected = result.x >= 0.5
    return candidates.loc[selected].copy()

def solve_squad_with_pulp(candidates: pd.DataFrame, objective_column: str, budget: float) -> pd.DataFrame | None:
    try:
        import pulp
    except ImportError:
        return None

    model = pulp.LpProblem("Best_FPL_Squad", pulp.LpMaximize)
    player_vars = {
        index: pulp.LpVariable(f"player_{index}", lowBound=0, upBound=1, cat="Binary")
        for index in candidates.index
    }

    model += pulp.lpSum(
        candidates.at[index, objective_column] * player_vars[index]
        for index in candidates.index
    )
    model += pulp.lpSum(player_vars.values()) == 15
    model += pulp.lpSum(
        candidates.at[index, "Price"] * player_vars[index]
        for index in candidates.index
    ) <= budget

    for position, count in {"GK": 2, "DEF": 5, "MID": 5, "FWD": 3}.items():
        model += (
            pulp.lpSum(
                player_vars[index]
                for index in candidates.index
                if candidates.at[index, "Position"] == position
            )
            == count
        )

    for club in candidates["Club"].dropna().unique():
        model += (
            pulp.lpSum(
                player_vars[index]
                for index in candidates.index
                if candidates.at[index, "Club"] == club
            )
            <= 3
        )

    solver = pulp.PULP_CBC_CMD(msg=False)
    status = model.solve(solver)
    if pulp.LpStatus[status] != "Optimal":
        return None

    selected_indexes = [
        index
        for index, variable in player_vars.items()
        if variable.value() is not None and variable.value() >= 0.5
    ]
    return candidates.loc[selected_indexes].copy()

def build_best_squad(candidates: pd.DataFrame, objective_column: str, budget: float) -> pd.DataFrame | None:
    squad = solve_squad_with_scipy(candidates, objective_column, budget)
    if squad is not None:
        return squad
    return solve_squad_with_pulp(candidates, objective_column, budget)

def normalize_squad_position(value: object) -> str:
    position = str(value or "").strip().upper()
    return {
        "GOALKEEPER": "GK",
        "GKP": "GK",
        "KEEPER": "GK",
        "DEFENDER": "DEF",
        "DEFENCE": "DEF",
        "MIDFIELDER": "MID",
        "FORWARD": "FWD",
        "STRIKER": "FWD",
    }.get(position, position)

def get_squad_candidates(filtered: pd.DataFrame, projection_columns: list[str]) -> pd.DataFrame:
    candidates = filtered.copy()
    candidates["Name"] = candidates["Name"].fillna("").astype(str).str.strip()
    candidates["Club"] = candidates["Club"].fillna("").astype(str).str.strip()
    candidates["Position"] = candidates["Position"].map(normalize_squad_position)
    candidates["Price"] = pd.to_numeric(candidates["Price"], errors="coerce")
    if candidates["Price"].dropna().gt(30).any():
        candidates.loc[candidates["Price"] > 30, "Price"] = candidates.loc[
            candidates["Price"] > 30,
            "Price",
        ] / 10
    candidates = candidates[
        candidates["Name"].ne("")
        & candidates["Club"].ne("")
        & candidates["Position"].isin(POSITION_ORDER)
        & candidates["Price"].notna()
        & (candidates["Price"] > 0)
    ].copy()
    for column in projection_columns:
        if column in candidates.columns:
            candidates[column] = pd.to_numeric(candidates[column], errors="coerce").fillna(0)
    return candidates
