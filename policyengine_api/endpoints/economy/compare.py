from microdf import MicroDataFrame, MicroSeries
import numpy as np
import sys
from policyengine_core.tools.hugging_face import download_huggingface_dataset
import pandas as pd
import h5py


def budgetary_impact(baseline: dict, reform: dict) -> dict:
    tax_revenue_impact = reform["total_tax"] - baseline["total_tax"]
    state_tax_revenue_impact = (
        reform["total_state_tax"] - baseline["total_state_tax"]
    )
    benefit_spending_impact = (
        reform["total_benefits"] - baseline["total_benefits"]
    )
    budgetary_impact = tax_revenue_impact - benefit_spending_impact
    return dict(
        budgetary_impact=budgetary_impact,
        tax_revenue_impact=tax_revenue_impact,
        state_tax_revenue_impact=state_tax_revenue_impact,
        benefit_spending_impact=benefit_spending_impact,
        households=sum(baseline["household_weight"]),
        baseline_net_income=baseline["total_net_income"],
    )


def labor_supply_response(baseline: dict, reform: dict) -> dict:
    substitution_lsr = (
        reform["substitution_lsr"] - baseline["substitution_lsr"]
    )
    income_lsr = reform["income_lsr"] - baseline["income_lsr"]
    total_change = substitution_lsr + income_lsr
    revenue_change = (
        reform["budgetary_impact_lsr"] - baseline["budgetary_impact_lsr"]
    )

    substitution_lsr_hh = np.array(reform["substitution_lsr_hh"]) - np.array(
        baseline["substitution_lsr_hh"]
    )
    income_lsr_hh = np.array(reform["income_lsr_hh"]) - np.array(
        baseline["income_lsr_hh"]
    )
    decile = np.array(baseline["household_income_decile"])
    household_weight = baseline["household_weight"]

    total_lsr_hh = substitution_lsr_hh + income_lsr_hh

    emp_income = MicroSeries(
        baseline["employment_income_hh"], weights=household_weight
    )
    self_emp_income = MicroSeries(
        baseline["self_employment_income_hh"], weights=household_weight
    )
    earnings = emp_income + self_emp_income
    original_earnings = earnings - total_lsr_hh
    substitution_lsr_hh = MicroSeries(
        substitution_lsr_hh, weights=household_weight
    )
    income_lsr_hh = MicroSeries(income_lsr_hh, weights=household_weight)

    decile_avg = dict(
        income=income_lsr_hh.groupby(decile).mean().to_dict(),
        substitution=substitution_lsr_hh.groupby(decile).mean().to_dict(),
    )
    decile_rel = dict(
        income=(
            income_lsr_hh.groupby(decile).sum()
            / original_earnings.groupby(decile).sum()
        ).to_dict(),
        substitution=(
            substitution_lsr_hh.groupby(decile).sum()
            / original_earnings.groupby(decile).sum()
        ).to_dict(),
    )

    relative_lsr = dict(
        income=(income_lsr_hh.sum() / original_earnings.sum()),
        substitution=(substitution_lsr_hh.sum() / original_earnings.sum()),
    )

    decile_rel["income"] = {
        int(k): v for k, v in decile_rel["income"].items() if k > 0
    }
    decile_rel["substitution"] = {
        int(k): v for k, v in decile_rel["substitution"].items() if k > 0
    }

    hours = dict(
        baseline=baseline["weekly_hours"],
        reform=reform["weekly_hours"],
        change=reform["weekly_hours"] - baseline["weekly_hours"],
        income_effect=reform["weekly_hours_income_effect"]
        - baseline["weekly_hours_income_effect"],
        substitution_effect=reform["weekly_hours_substitution_effect"]
        - baseline["weekly_hours_substitution_effect"],
    )

    return dict(
        substitution_lsr=substitution_lsr,
        income_lsr=income_lsr,
        relative_lsr=relative_lsr,
        total_change=total_change,
        revenue_change=revenue_change,
        decile=dict(
            average=decile_avg,
            relative=decile_rel,
        ),
        hours=hours,
    )


def detailed_budgetary_impact(
    baseline: dict, reform: dict, country_id: str
) -> dict:
    result = {}
    if country_id == "uk":
        for program in baseline["programs"]:
            # baseline[programs][program] = total budgetary impact of program
            result[program] = dict(
                baseline=baseline["programs"][program],
                reform=reform["programs"][program],
                difference=reform["programs"][program]
                - baseline["programs"][program],
            )
    return result


def decile_impact(baseline: dict, reform: dict) -> dict:
    """
    Compare the impact of a reform on the deciles of the population.

    Args:
        baseline (dict): The baseline economy.
        reform (dict): The reform economy.

    Returns:
        dict: The impact of the reform on the deciles of the population.
    """
    baseline_income = MicroSeries(
        baseline["household_net_income"], weights=baseline["household_weight"]
    )
    reform_income = MicroSeries(
        reform["household_net_income"], weights=baseline_income.weights
    )

    # Filter out negative decile values
    decile = MicroSeries(baseline["household_income_decile"])
    baseline_income_filtered = baseline_income[decile >= 0]
    reform_income_filtered = reform_income[decile >= 0]

    income_change = reform_income_filtered - baseline_income_filtered
    rel_income_change_by_decile = (
        income_change.groupby(decile).sum()
        / baseline_income_filtered.groupby(decile).sum()
    )

    avg_income_change_by_decile = (
        income_change.groupby(decile).sum()
        / baseline_income_filtered.groupby(decile).count()
    )
    rel_decile_dict = rel_income_change_by_decile.to_dict()
    avg_decile_dict = avg_income_change_by_decile.to_dict()
    result = dict(
        relative={int(k): v for k, v in rel_decile_dict.items()},
        average={int(k): v for k, v in avg_decile_dict.items()},
    )
    return result


def wealth_decile_impact(baseline: dict, reform: dict) -> dict:
    """
    Compare the impact of a reform on the deciles of the population.

    Args:
        baseline (dict): The baseline economy.
        reform (dict): The reform economy.

    Returns:
        dict: The impact of the reform on the deciles of the population.
    """
    baseline_income = MicroSeries(
        baseline["household_net_income"], weights=baseline["household_weight"]
    )
    reform_income = MicroSeries(
        reform["household_net_income"], weights=baseline_income.weights
    )

    # Filter out negative decile values
    decile = MicroSeries(baseline["household_wealth_decile"])
    baseline_income_filtered = baseline_income[decile >= 0]
    reform_income_filtered = reform_income[decile >= 0]

    income_change = reform_income_filtered - baseline_income_filtered
    rel_income_change_by_decile = (
        income_change.groupby(decile).sum()
        / baseline_income_filtered.groupby(decile).sum()
    )
    avg_income_change_by_decile = (
        income_change.groupby(decile).sum()
        / baseline_income_filtered.groupby(decile).count()
    )
    rel_decile_dict = rel_income_change_by_decile.to_dict()
    avg_decile_dict = avg_income_change_by_decile.to_dict()
    result = dict(
        relative={int(k): v for k, v in rel_decile_dict.items()},
        average={int(k): v for k, v in avg_decile_dict.items()},
    )
    return result


def inequality_impact(baseline: dict, reform: dict) -> dict:
    """
    Compare the impact of a reform on inequality.

    Args:
        baseline (dict): The baseline economy.
        reform (dict): The reform economy.

    Returns:
        dict: The impact of the reform on inequality.
    """

    return dict(
        gini=dict(
            baseline=baseline["gini"],
            reform=reform["gini"],
        ),
        top_10_pct_share=dict(
            baseline=baseline["top_10_percent_share"],
            reform=reform["top_10_percent_share"],
        ),
        top_1_pct_share=dict(
            baseline=baseline["top_1_percent_share"],
            reform=reform["top_1_percent_share"],
        ),
    )


def poverty_impact(baseline: dict, reform: dict) -> dict:
    """
    Compare the impact of a reform on poverty.

    Args:
        baseline (dict): The baseline economy.
        reform (dict): The reform economy.

    Returns:
        dict: The impact of the reform on poverty.
    """
    baseline_poverty = MicroSeries(
        baseline["person_in_poverty"], weights=baseline["person_weight"]
    )
    baseline_deep_poverty = MicroSeries(
        baseline["person_in_deep_poverty"], weights=baseline["person_weight"]
    )
    reform_poverty = MicroSeries(
        reform["person_in_poverty"], weights=baseline_poverty.weights
    )
    reform_deep_poverty = MicroSeries(
        reform["person_in_deep_poverty"], weights=baseline_poverty.weights
    )
    age = MicroSeries(baseline["age"])

    poverty = dict(
        child=dict(
            baseline=float(baseline_poverty[age < 18].mean()),
            reform=float(reform_poverty[age < 18].mean()),
        ),
        adult=dict(
            baseline=float(baseline_poverty[(age >= 18) & (age < 65)].mean()),
            reform=float(reform_poverty[(age >= 18) & (age < 65)].mean()),
        ),
        senior=dict(
            baseline=float(baseline_poverty[age >= 65].mean()),
            reform=float(reform_poverty[age >= 65].mean()),
        ),
        all=dict(
            baseline=float(baseline_poverty.mean()),
            reform=float(reform_poverty.mean()),
        ),
    )

    deep_poverty = dict(
        child=dict(
            baseline=float(baseline_deep_poverty[age < 18].mean()),
            reform=float(reform_deep_poverty[age < 18].mean()),
        ),
        adult=dict(
            baseline=float(
                baseline_deep_poverty[(age >= 18) & (age < 65)].mean()
            ),
            reform=float(reform_deep_poverty[(age >= 18) & (age < 65)].mean()),
        ),
        senior=dict(
            baseline=float(baseline_deep_poverty[age >= 65].mean()),
            reform=float(reform_deep_poverty[age >= 65].mean()),
        ),
        all=dict(
            baseline=float(baseline_deep_poverty.mean()),
            reform=float(reform_deep_poverty.mean()),
        ),
    )

    return dict(
        poverty=poverty,
        deep_poverty=deep_poverty,
    )


def intra_decile_impact(baseline: dict, reform: dict) -> dict:
    baseline_income = MicroSeries(
        baseline["household_net_income"], weights=baseline["household_weight"]
    )
    reform_income = MicroSeries(
        reform["household_net_income"], weights=baseline_income.weights
    )
    people = MicroSeries(
        baseline["household_count_people"], weights=baseline_income.weights
    )
    decile = MicroSeries(baseline["household_income_decile"]).values
    absolute_change = (reform_income - baseline_income).values
    capped_baseline_income = np.maximum(baseline_income.values, 1)
    capped_reform_income = (
        np.maximum(reform_income.values, 1) + absolute_change
    )
    income_change = (
        capped_reform_income - capped_baseline_income
    ) / capped_baseline_income

    # Within each decile, calculate the percentage of people who:
    # 1. Gained more than 5% of their income
    # 2. Gained between 0% and 5% of their income
    # 3. Had no change in income
    # 3. Lost between 0% and 5% of their income
    # 4. Lost more than 5% of their income

    outcome_groups = {}
    all_outcomes = {}
    BOUNDS = [-np.inf, -0.05, -1e-3, 1e-3, 0.05, np.inf]
    LABELS = [
        "Lose more than 5%",
        "Lose less than 5%",
        "No change",
        "Gain less than 5%",
        "Gain more than 5%",
    ]
    for lower, upper, label in zip(BOUNDS[:-1], BOUNDS[1:], LABELS):
        outcome_groups[label] = []
        for i in range(1, 11):

            in_decile: bool = decile == i
            in_group: bool = (income_change > lower) & (income_change <= upper)
            in_both: bool = in_decile & in_group

            people_in_both: np.float64 = people[in_both].sum()
            people_in_decile: np.float64 = people[in_decile].sum()

            # np.float64 does not raise ZeroDivisionError, instead returns NaN
            if people_in_decile == 0 and people_in_both == 0:
                people_in_proportion: float = 0.0
            else:
                people_in_proportion: float = float(
                    people_in_both / people_in_decile
                )

            outcome_groups[label].append(people_in_proportion)

        all_outcomes[label] = sum(outcome_groups[label]) / 10
    return dict(deciles=outcome_groups, all=all_outcomes)


def intra_wealth_decile_impact(baseline: dict, reform: dict) -> dict:
    baseline_income = MicroSeries(
        baseline["household_net_income"], weights=baseline["household_weight"]
    )
    reform_income = MicroSeries(
        reform["household_net_income"], weights=baseline_income.weights
    )
    people = MicroSeries(
        baseline["household_count_people"], weights=baseline_income.weights
    )
    decile = MicroSeries(baseline["household_wealth_decile"]).values
    absolute_change = (reform_income - baseline_income).values
    capped_baseline_income = np.maximum(baseline_income.values, 1)
    capped_reform_income = (
        np.maximum(reform_income.values, 1) + absolute_change
    )
    income_change = (
        capped_reform_income - capped_baseline_income
    ) / capped_baseline_income

    # Within each decile, calculate the percentage of people who:
    # 1. Gained more than 5% of their income
    # 2. Gained between 0% and 5% of their income
    # 3. Had no change in income
    # 3. Lost between 0% and 5% of their income
    # 4. Lost more than 5% of their income

    outcome_groups = {}
    all_outcomes = {}
    BOUNDS = [-np.inf, -0.05, -1e-3, 1e-3, 0.05, np.inf]
    LABELS = [
        "Lose more than 5%",
        "Lose less than 5%",
        "No change",
        "Gain less than 5%",
        "Gain more than 5%",
    ]
    for lower, upper, label in zip(BOUNDS[:-1], BOUNDS[1:], LABELS):
        outcome_groups[label] = []
        for i in range(1, 11):

            in_decile: bool = decile == i
            in_group: bool = (income_change > lower) & (income_change <= upper)
            in_both: bool = in_decile & in_group

            people_in_both: np.float64 = people[in_both].sum()
            people_in_decile: np.float64 = people[in_decile].sum()

            # np.float64 does not raise ZeroDivisionError, instead returns NaN
            if people_in_decile == 0 and people_in_both == 0:
                people_in_proportion = 0
            else:
                people_in_proportion: float = float(
                    people_in_both / people_in_decile
                )

            outcome_groups[label].append(people_in_proportion)

        all_outcomes[label] = sum(outcome_groups[label]) / 10
    return dict(deciles=outcome_groups, all=all_outcomes)


def poverty_gender_breakdown(baseline: dict, reform: dict) -> dict:
    """
    Compare the impact of a reform on poverty.

    Args:
        baseline (dict): The baseline economy.
        reform (dict): The reform economy.

    Returns:
        dict: The impact of the reform on poverty.
    """
    if baseline["is_male"] is None:
        return {}
    baseline_poverty = MicroSeries(
        baseline["person_in_poverty"], weights=baseline["person_weight"]
    )
    baseline_deep_poverty = MicroSeries(
        baseline["person_in_deep_poverty"], weights=baseline["person_weight"]
    )
    reform_poverty = MicroSeries(
        reform["person_in_poverty"], weights=baseline_poverty.weights
    )
    reform_deep_poverty = MicroSeries(
        reform["person_in_deep_poverty"], weights=baseline_poverty.weights
    )
    is_male = MicroSeries(baseline["is_male"])

    poverty = dict(
        male=dict(
            baseline=float(baseline_poverty[is_male].mean()),
            reform=float(reform_poverty[is_male].mean()),
        ),
        female=dict(
            baseline=float(baseline_poverty[~is_male].mean()),
            reform=float(reform_poverty[~is_male].mean()),
        ),
    )

    deep_poverty = dict(
        male=dict(
            baseline=float(baseline_deep_poverty[is_male].mean()),
            reform=float(reform_deep_poverty[is_male].mean()),
        ),
        female=dict(
            baseline=float(baseline_deep_poverty[~is_male].mean()),
            reform=float(reform_deep_poverty[~is_male].mean()),
        ),
    )

    return dict(
        poverty=poverty,
        deep_poverty=deep_poverty,
    )


def poverty_racial_breakdown(baseline: dict, reform: dict) -> dict:
    """
    Compare the impact of a reform on poverty.

    Args:
        baseline (dict): The baseline economy.
        reform (dict): The reform economy.

    Returns:
        dict: The impact of the reform on poverty.
    """
    if baseline["race"] is None:
        return {}
    baseline_poverty = MicroSeries(
        baseline["person_in_poverty"], weights=baseline["person_weight"]
    )
    reform_poverty = MicroSeries(
        reform["person_in_poverty"], weights=baseline_poverty.weights
    )
    race = MicroSeries(
        baseline["race"]
    )  # Can be WHITE, BLACK, HISPANIC, or OTHER.

    poverty = dict(
        white=dict(
            baseline=float(baseline_poverty[race == "WHITE"].mean()),
            reform=float(reform_poverty[race == "WHITE"].mean()),
        ),
        black=dict(
            baseline=float(baseline_poverty[race == "BLACK"].mean()),
            reform=float(reform_poverty[race == "BLACK"].mean()),
        ),
        hispanic=dict(
            baseline=float(baseline_poverty[race == "HISPANIC"].mean()),
            reform=float(reform_poverty[race == "HISPANIC"].mean()),
        ),
        other=dict(
            baseline=float(baseline_poverty[race == "OTHER"].mean()),
            reform=float(reform_poverty[race == "OTHER"].mean()),
        ),
    )

    return dict(
        poverty=poverty,
    )


def uk_constituency_breakdown(
    baseline: dict, reform: dict, country_id: str
) -> dict:
    if country_id != "uk":
        return {}

    output = {
        "by_constituency": {},
        "overall": {
            "Gain more than 5%": 0,
            "Gain less than 5%": 0,
            "No change": 0,
            "Lose less than 5%": 0,
            "Lose more than 5%": 0,
        },
    }
    baseline_hnet = baseline["household_net_income"]
    reform_hnet = reform["household_net_income"]

    constituency_weights_path = download_huggingface_dataset(
        repo="policyengine/policyengine-uk-data",
        repo_filename="parliamentary_constituency_weights.h5",
    )
    with h5py.File(constituency_weights_path, "r") as f:
        weights = f["2025"][...]

    constituency_names_path = download_huggingface_dataset(
        repo="policyengine/policyengine-uk-data",
        repo_filename="constituencies_2024.csv",
    )
    constituency_names = pd.read_csv(constituency_names_path)

    for i in range(len(constituency_names)):
        name = constituency_names.iloc[i]["name"]
        weight = weights[i]
        baseline_income = MicroSeries(baseline_hnet, weights=weight)
        reform_income = MicroSeries(reform_hnet, weights=weight)
        average_household_income_change = (
            reform_income.sum() - baseline_income.sum()
        ) / baseline_income.count()
        percent_household_income_change = (
            reform_income.sum() / baseline_income.sum() - 1
        )
        output["by_constituency"][name] = {
            "average_household_income_change": average_household_income_change,
            "relative_household_income_change": percent_household_income_change,
            "x": int(constituency_names.iloc[i]["x"]),
            "y": int(constituency_names.iloc[i]["y"]),
        }

        if percent_household_income_change > 0.05:
            output["overall"]["Gain more than 5%"] += 1
        elif percent_household_income_change > 1e-3:
            output["overall"]["Gain less than 5%"] += 1
        elif percent_household_income_change > -1e-3:
            output["overall"]["No change"] += 1
        elif percent_household_income_change > -0.05:
            output["overall"]["Lose less than 5%"] += 1
        else:
            output["overall"]["Lose more than 5%"] += 1

    return output


def compare_economic_outputs(
    baseline: dict, reform: dict, country_id: str = None
) -> dict:
    """
    Compare the economic outputs of two economies.

    Args:
        baseline (dict): The baseline economy.
        reform (dict): The reform economy.

    Returns:
        dict: The comparison of the two economies.
    """
    if baseline.get("type") == "general":
        budgetary_impact_data = budgetary_impact(baseline, reform)
        detailed_budgetary_impact_data = detailed_budgetary_impact(
            baseline, reform, country_id
        )
        decile_impact_data = decile_impact(baseline, reform)
        inequality_impact_data = inequality_impact(baseline, reform)
        poverty_impact_data = poverty_impact(baseline, reform)
        poverty_by_gender_data = poverty_gender_breakdown(baseline, reform)
        poverty_by_race_data = poverty_racial_breakdown(baseline, reform)
        intra_decile_impact_data = intra_decile_impact(baseline, reform)
        labor_supply_response_data = labor_supply_response(baseline, reform)
        constituency_impact_data = uk_constituency_breakdown(
            baseline, reform, country_id
        )
        try:
            wealth_decile_impact_data = wealth_decile_impact(baseline, reform)
            intra_wealth_decile_impact_data = intra_wealth_decile_impact(
                baseline, reform
            )
        except:
            wealth_decile_impact_data = {}
            intra_wealth_decile_impact_data = {}

        return dict(
            budget=budgetary_impact_data,
            detailed_budget=detailed_budgetary_impact_data,
            decile=decile_impact_data,
            inequality=inequality_impact_data,
            poverty=poverty_impact_data,
            poverty_by_gender=poverty_by_gender_data,
            poverty_by_race=poverty_by_race_data,
            intra_decile=intra_decile_impact_data,
            wealth_decile=wealth_decile_impact_data,
            intra_wealth_decile=intra_wealth_decile_impact_data,
            labor_supply_response=labor_supply_response_data,
            constituency_impact=constituency_impact_data,
        )
    elif baseline.get("type") == "cliff":
        return dict(
            baseline=dict(
                cliff_gap=baseline["cliff_gap"],
                cliff_share=baseline["cliff_share"],
            ),
            reform=dict(
                cliff_gap=reform["cliff_gap"],
                cliff_share=reform["cliff_share"],
            ),
        )
