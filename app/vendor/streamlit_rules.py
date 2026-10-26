"""Extracted unchanged functions. See provenance.json; do not edit optimizer rules here."""
from __future__ import annotations
from itertools import combinations
import pandas as pd
POSITION_ORDER = ["GK","DEF","MID","FWD"]
BEAM_WIDTH = 10
BUYS_PER_SELLER = 3

def is_free_hit_chip_name(chip_name: object) -> bool:
    normalized = str(chip_name or "").strip().lower().replace("_", "").replace("-", "").replace(" ", "")
    return normalized == "freehit"

def free_hit_events_from_entry_history(entry_history_data: dict) -> set[int]:
    free_hit_events: set[int] = set()
    for chip in entry_history_data.get("chips", []) or []:
        if is_free_hit_chip_name(chip.get("name")) and chip.get("event") is not None:
            free_hit_events.add(int(chip["event"]))
    return free_hit_events

def squad_ids_from_picks_data(picks_data: dict) -> set[int]:
    return {
        int(pick["element"])
        for pick in picks_data.get("picks", [])
        if pick.get("element") is not None
    }

def bank_from_picks_data(picks_data: dict) -> float:
    entry_history = picks_data.get("entry_history") or {}
    return float(entry_history.get("bank", 0) or 0) / 10

def get_permanent_squad_before_gw(team_id: int, target_gameweek: int) -> dict:
    previous_gameweek = max(int(target_gameweek) - 1, 1)
    entry_history_data = fetch_entry_history(team_id)
    free_hit_events = free_hit_events_from_entry_history(entry_history_data)
    ignored_free_hit_gameweeks: list[int] = []

    for source_gameweek in range(previous_gameweek, 0, -1):
        if source_gameweek in free_hit_events:
            ignored_free_hit_gameweeks.append(source_gameweek)
            continue

        picks_data = fetch_entry_picks(team_id, source_gameweek)
        squad_player_ids = squad_ids_from_picks_data(picks_data)
        return {
            "squad_player_ids": squad_player_ids,
            "bank": bank_from_picks_data(picks_data),
            "source_gameweek": source_gameweek,
            "target_gameweek": int(target_gameweek),
            "previous_gameweek": previous_gameweek,
            "previous_gameweek_chip": "Free Hit" if previous_gameweek in free_hit_events else "None",
            "ignored_free_hit_gameweeks": ignored_free_hit_gameweeks,
            "squad_source_note": (
                f"Free Hit detected in GW{ignored_free_hit_gameweeks[0]}. "
                f"Using your GW{source_gameweek} squad as the returning squad for GW{int(target_gameweek)}."
                if ignored_free_hit_gameweeks
                else ""
            ),
            "chip_history_available": True,
        }

    picks_data = fetch_entry_picks(team_id, previous_gameweek)
    return {
        "squad_player_ids": squad_ids_from_picks_data(picks_data),
        "bank": bank_from_picks_data(picks_data),
        "source_gameweek": previous_gameweek,
        "target_gameweek": int(target_gameweek),
        "previous_gameweek": previous_gameweek,
        "previous_gameweek_chip": "Free Hit" if previous_gameweek in free_hit_events else "None",
        "ignored_free_hit_gameweeks": ignored_free_hit_gameweeks,
        "squad_source_note": "",
        "chip_history_available": True,
    }

def is_valid_starting_xi(players: pd.DataFrame) -> bool:
    position_counts = players["Position"].value_counts()
    return (
        len(players) == 11
        and int(position_counts.get("GK", 0)) == 1
        and int(position_counts.get("DEF", 0)) >= 3
        and int(position_counts.get("MID", 0)) >= 2
        and int(position_counts.get("FWD", 0)) >= 1
        and int(position_counts.get("DEF", 0))
        + int(position_counts.get("MID", 0))
        + int(position_counts.get("FWD", 0))
        == 10
    )

def optimize_starting_xi(
    squad: pd.DataFrame,
    gameweek_column: str,
    captain_multiplier: int,
) -> tuple[pd.DataFrame | None, pd.Series | None, float]:
    best_indexes: tuple[int, ...] | None = None
    best_score = -1.0

    for indexes in combinations(tuple(squad.index), 11):
        candidate = squad.loc[list(indexes)]
        if not is_valid_starting_xi(candidate):
            continue
        points = pd.to_numeric(candidate[gameweek_column], errors="coerce").fillna(0)
        score = float(points.sum() + ((captain_multiplier - 1) * points.max()))
        if score > best_score:
            best_score = score
            best_indexes = indexes

    if best_indexes is None:
        return None, None, 0.0

    starting_xi = squad.loc[list(best_indexes)].copy()
    captain = starting_xi.loc[starting_xi[gameweek_column].idxmax()]
    return starting_xi, captain, best_score

def formation_text(starting_xi: pd.DataFrame | None, chip: str) -> str:
    if starting_xi is None:
        return "N/A"
    counts = starting_xi["Position"].value_counts()
    return f"{int(counts.get('DEF', 0))}-{int(counts.get('MID', 0))}-{int(counts.get('FWD', 0))}"

def round_table_values(dataframe: pd.DataFrame, numeric_columns: list[str]) -> pd.DataFrame:
    rounded = dataframe.copy()
    for column in numeric_columns:
        if column in rounded.columns:
            rounded[column] = pd.to_numeric(rounded[column], errors="coerce").fillna(0).round(2)
    return rounded

def calculate_team_sheet(
    squad: pd.DataFrame,
    gameweek_column: str,
    chip: str,
) -> dict | None:
    squad = squad.copy()
    squad["GW Projection"] = pd.to_numeric(squad[gameweek_column], errors="coerce").fillna(0)

    captain_multiplier = 3 if chip == "Triple Captain" else 2
    starting_xi, captain, starting_total = optimize_starting_xi(
        squad,
        "GW Projection",
        captain_multiplier,
    )
    if starting_xi is None or captain is None:
        return None

    squad["Role"] = "Bench"
    squad.loc[starting_xi.index, "Role"] = "Starter"
    squad.loc[captain.name, "Role"] = "Captain"
    bench_total = float(squad.loc[squad["Role"] == "Bench", "GW Projection"].sum())

    if chip == "Bench Boost":
        squad.loc[squad["Role"] == "Bench", "Role"] = "Bench Boost Player"
        projected_total = starting_total + bench_total
    else:
        projected_total = starting_total

    full_squad_total = starting_total + bench_total
    role_order = ["Captain", "Starter", "Bench Boost Player", "Bench"]
    squad["Role Sort"] = pd.Categorical(squad["Role"], categories=role_order, ordered=True)
    squad["Position Sort"] = pd.Categorical(squad["Position"], categories=POSITION_ORDER, ordered=True)
    table = squad.sort_values(
        ["Role Sort", "Position Sort", "GW Projection"],
        ascending=[True, True, False],
    )
    table = table.rename(columns={"Position": "Pos", "GW Projection": "GW"})
    display_table = round_table_values(table[["Name", "Club", "Pos", "GW", "Role"]], ["GW"])

    return {
        "captain": captain,
        "captain_multiplier": captain_multiplier,
        "starting_xi": starting_xi,
        "projected_total": float(projected_total),
        "bench_total": float(bench_total),
        "full_squad_total": float(full_squad_total),
        "display_table": display_table,
    }

def calculate_multi_gw_team_sheets(
    squad: pd.DataFrame,
    gameweek_columns: list[str],
    chip_plan: dict[str, str] | None = None,
    free_hit_squads: dict[str, pd.DataFrame] | None = None,
) -> list[dict]:
    """Build an independent, legal team sheet for each GW from one fixed squad."""
    chip_plan = chip_plan or {}
    free_hit_squads = free_hit_squads or {}
    team_sheets = []
    for gameweek_column in gameweek_columns:
        chip = chip_plan.get(gameweek_column, "None")
        weekly_squad = (
            free_hit_squads[gameweek_column]
            if chip == "Free Hit" and gameweek_column in free_hit_squads
            else squad
        )
        calculation_chip = chip if chip in {"Bench Boost", "Triple Captain"} else "None"
        team_sheet = calculate_team_sheet(weekly_squad, gameweek_column, calculation_chip)
        if team_sheet is None:
            continue
        team_sheet["gameweek"] = gameweek_column
        team_sheet["chip"] = chip
        team_sheet["squad"] = weekly_squad
        team_sheet["formation"] = formation_text(team_sheet["starting_xi"], "None")
        captain_projection = float(team_sheet["captain"]["GW Projection"])
        team_sheet["captain_bonus"] = float(
            (team_sheet["captain_multiplier"] - 1) * captain_projection
        )
        team_sheet["starting_xi_base"] = float(
            pd.to_numeric(
                team_sheet["starting_xi"][gameweek_column],
                errors="coerce",
            ).fillna(0).sum()
        )
        team_sheet["bench_points_counted"] = (
            float(team_sheet["bench_total"]) if chip == "Bench Boost" else 0.0
        )
        team_sheet["chip_points_added"] = (
            float(team_sheet["bench_total"])
            if chip == "Bench Boost"
            else captain_projection if chip == "Triple Captain" else 0.0
        )
        team_sheets.append(team_sheet)
    return team_sheets

def club_rule_allows_transfer(
    current_squad: pd.DataFrame,
    sold_player_id: int,
    buy_player: pd.Series,
    player_id_column: str,
) -> bool:
    post_transfer = current_squad[current_squad[player_id_column] != sold_player_id].copy()
    post_transfer = pd.concat([post_transfer, buy_player.to_frame().T], ignore_index=True)
    return int(post_transfer["Club"].value_counts().max()) <= 3

def get_valid_buy_options(
    projections: pd.DataFrame,
    current_squad: pd.DataFrame,
    sold_player: pd.Series,
    bank: float,
    player_id_column: str,
    excluded_buy_ids: set[int] | None = None,
) -> pd.DataFrame:
    current_ids = set(current_squad[player_id_column].astype(int))
    sold_player_id = int(sold_player[player_id_column])
    max_buy_price = float(sold_player["Price"]) + bank
    excluded_buy_ids = excluded_buy_ids or set()

    candidates = projections[
        (projections["Position"] == sold_player["Position"])
        & (~projections[player_id_column].astype(int).isin(current_ids))
        & (~projections[player_id_column].astype(int).isin(excluded_buy_ids))
        & (projections["Price"] <= max_buy_price)
    ].copy()
    candidates = candidates[
        candidates.apply(
            lambda player: club_rule_allows_transfer(
                current_squad,
                sold_player_id,
                player,
                player_id_column,
            ),
            axis=1,
        )
    ]
    return candidates.sort_values("Predicted Total", ascending=False)

def get_projection_score(row: pd.Series, gw_columns: list[str], mode: str) -> float:
    if not gw_columns:
        return 0.0
    if mode == "Next GW":
        return float(pd.to_numeric(row.get(gw_columns[0], 0), errors="coerce"))
    return float(pd.to_numeric(row[gw_columns], errors="coerce").fillna(0).sum())

def add_transfer_upgrade_scores(
    candidates: pd.DataFrame,
    sold_player: pd.Series,
    gw_columns: list[str],
    gameweek_mode: str,
) -> pd.DataFrame:
    scored = candidates.copy()
    sell_projection = get_projection_score(sold_player, gw_columns, gameweek_mode)
    scored["Transfer Projection"] = scored.apply(
        lambda player: get_projection_score(player, gw_columns, gameweek_mode),
        axis=1,
    )
    scored["Upgrade Score"] = scored["Transfer Projection"] - sell_projection
    return scored.sort_values(["Upgrade Score", "Predicted Total"], ascending=[False, False])

def calculate_transfer_projection_total(
    squad: pd.DataFrame,
    gw_columns: list[str],
    mode: str,
) -> float:
    return float(
        squad.apply(
            lambda player: get_projection_score(player, gw_columns, mode),
            axis=1,
        ).sum()
    )
