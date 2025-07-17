from validate import validate_config
import yaml
from fractions import Fraction
from contextlib import contextmanager
import sys
import builtins
import random
import numpy as np
import matplotlib.pyplot as plt
import statistics


def classify(grade: float, classifications: list[dict]) -> str:
    if classifications:
        sorted_classifications = sorted(classifications, key=lambda c: c["threshold"], reverse=True)
        for classification in sorted_classifications:
            if grade >= classification["threshold"]:
                return f"{grade:.2f} ({classification["name"]})"
    return f"{grade:.2f}"

@contextmanager
def section(title, indent="  "):
    print(f"{title}")
    original_print = builtins.print

    def indented_print(*args, **kwargs):
        if args:
            args = (indent + str(args[0]), *args[1:])
        original_print(*args, **kwargs)

    builtins.print = indented_print
    try:
        yield
    finally:
        builtins.print = original_print

def probability_exclusive(final_grades, classifications):
    sorted_classes = sorted(classifications, key=lambda c: c["threshold"])
    counts = {c["name"]: 0 for c in sorted_classes}
    for grade in final_grades:
        for cls in reversed(sorted_classes):
            if grade >= cls["threshold"]:
                counts[cls["name"]] += 1
                break
    total = len(final_grades)
    return {name: count / total for name, count in counts.items()}

def simulate_final_grade(units, classifications, simulations=10000, stddev=None):
    unit_grades = []
    unit_credits = []
    for _, credit, assessments in yield_unit_data(units):
        grade = predict_unit_grade(assessments)
        if grade is not None:
            unit_grades.append(grade)
            unit_credits.append(credit)
    if len(unit_grades) < 2:
        print("Not enough data to simulate grades")
        return

    mean_grade = np.average(unit_grades, weights=unit_credits)
    variance = np.average((np.array(unit_grades) - mean_grade) ** 2, weights=unit_credits)
    stddev = np.sqrt(variance)
    final_grades = []
    total_credits = sum(unit_credits)

    for _ in range(simulations):
        simulated_grades = []
        for grade in unit_grades:
            simulated_grades.append(max(0, min(100, random.gauss(grade, stddev))))
        weighted_grade = sum(g * c for g, c in zip(simulated_grades, unit_credits)) / total_credits
        final_grades.append(weighted_grade)

    median = np.percentile(final_grades, 50)
    low = np.percentile(final_grades, 5)
    high = np.percentile(final_grades, 95)
    print(f"Median (predicted final grade): {classify(median, classifications)}")
    print(f"5th percentile: {classify(low, classifications)}")
    print(f"95th percentile: {classify(high, classifications)}")
    if classifications:
        probs = probability_exclusive(final_grades, classifications)
        for name, prob in probs.items():
            print(f"Simulated probability of {name}: {prob:.2f}")

    # histogram
    plt.figure(figsize=(10,6))
    plt.hist(final_grades, bins=50, color="skyblue", edgecolor="black", alpha=0.7)
    x_min, x_max = plt.xlim()
    if classifications:
        for c in classifications:
            threshold = c["threshold"]
            if x_min <= threshold <= x_max:
                plt.axvline(
                    threshold,
                    color="black",
                    linestyle=":",
                    alpha=0.6,
                    linewidth=1.2,
                    label=f"{c["name"].capitalize()} threshold ({threshold}%)"
                )
    plt.axvline(median, color="red", linestyle="--", label=f"Median: {classify(median, classifications)}")
    plt.axvline(low, color="orange", linestyle="--", label=f"5th percentile: {classify(low, classifications)}")
    plt.axvline(high, color="green", linestyle="--", label=f"95th percentile: {classify(high, classifications)}")
    plt.title("Monte Carlo Simulated Final Grade Distribution")
    plt.xlabel("Final Grade (%)")
    plt.ylabel("Frequency")
    plt.legend()
    plt.grid(True)
    plt.savefig("final_grade_distribution.png")
    print("Saved histogram to 'final_grade_distribution.png'")

def iter_units(units):
    for unit in units:
        unit_name = unit["name"]
        credit = unit["credits"]
        assessments = []
        for a in unit["assessments"]:
            name = a["name"]
            weight = a["weight"] / 100
            mark = a["mark"]
            assessments.append((name, weight, mark))
        yield unit_name, credit, assessments

def compute_weighted_assessments(assessments, maximum=False):
    total_weight = 0
    total_score = 0

    for name, weight, mark in assessments:
        if mark is not None:
            total_score += mark * weight
            total_weight += weight
        elif maximum is True:
            total_score += 100 * weight
            total_weight += weight

    return total_score, total_weight

def predict_unit_grade(assessments):
    total_score, total_weight = compute_weighted_assessments(assessments)
    if total_weight == 0:
        return None
    return total_score / total_weight

def yield_unit_data(units):
    for unit in units:
        assessments = [
            (a["name"], a["weight"] / 100, a["mark"])
            for a in unit["assessments"]
        ]
        yield unit["name"], unit["credits"], assessments

from fractions import Fraction

def calc_predicted_grade(units, classifications):
    units_registry = {}
    credit_total = 0

    for unit_name, credit, assessments in yield_unit_data(units):
        predicted_grade = predict_unit_grade(assessments)

        if predicted_grade is not None:
            total_score, total_weight = compute_weighted_assessments(assessments)
            status = "Final" if total_weight == 1 else "Predicted"
            print(f"{status} unit grade for '{unit_name}': {classify(predicted_grade, classifications)}")
        
        units_registry[unit_name] = {
            "credit": credit,
            "grade": predicted_grade
        }

        credit_total += credit

    credit_accounted_for = 0
    weighted_total = 0

    for unit in units_registry.values():
        if unit["grade"] is not None:
            credit_accounted_for += unit["credit"]
            weight = Fraction(unit["credit"], credit_total)
            weighted_total += unit["grade"] * weight

    if credit_accounted_for != 0:
        print(f"Predicted final degree grade: {classify(weighted_total * (credit_total / credit_accounted_for), classifications)}")
    else:
        print(f"Unable to calculate predicted grade; not enough data")

def calc_minimum_grade(units, classifications):
    credit_total = 0

    units_registry = {}

    for unit_name, credit, assessments in yield_unit_data(units):
        unit_grade = 0
        total_score, total_weight = compute_weighted_assessments(assessments)
        units_registry[unit_name] = {
            "credit": credit,
            "grade": total_score
        }
        credit_total += credit

    weighted_total = 0

    for unit in units_registry.values():
        weight = Fraction(unit["credit"], credit_total)
        weighted_total += unit["grade"] * weight

    print(f"Minimum/actual degree grade: {classify(weighted_total, classifications)}")

def calc_maximum_grade(units, classifications):
    credit_total = 0

    units_registry = {}

    for unit_name, credit, assessments in yield_unit_data(units):
        unit_grade = 0
        total_score, total_weight = compute_weighted_assessments(assessments, maximum=True)

        units_registry[unit_name] = {
            "credit": credit,
            "grade": total_score
        }
        credit_total += credit

    weighted_total = 0

    for unit in units_registry.values():
        weight = Fraction(unit["credit"], credit_total)
        weighted_total += unit["grade"] * weight

    print(f"Maximum possible degree grade: {classify(weighted_total, classifications)}")

CALCS = (("WEIGHTED AVERAGE PREDICTION:", calc_predicted_grade,),("MINIMUM/ACTUAL",calc_minimum_grade),("MAXIMUM",calc_maximum_grade),("PROBABILISTIC PREDICTION", simulate_final_grade),)

def main():
    # read YAML file
    with open("units.yml", "r") as f:
        units = yaml.safe_load(f)
    # validate unit data structure
    validate_config(units)
    for calc in CALCS:
        with section(calc[0]):
            calc[1](units["units"], units.get("classifications"))

if __name__ == "__main__":
    main()