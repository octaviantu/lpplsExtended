import csv
from collections import defaultdict


class CountMetrics:
    bubble_accepted = 0
    bubble_rejected = 0
    rejected_because_can_not_fit = 0
    rejected_reasons = {
        "price": 0,
        "D": 0,
        "O": 0,
        "lomb_test": 0,
        "ar1_test": 0,
    }
    rejected_reasons_per_t2 = {}
    bubble_accepted_per_t2 = defaultdict(int)
    bubble_rejected_per_t2 = defaultdict(int)

    @staticmethod
    def reset():
        CountMetrics.bubble_accepted = 0
        CountMetrics.bubble_rejected = 0
        CountMetrics.rejected_because_can_not_fit = 0
        CountMetrics.rejected_reasons = {
            "price": 0,
            "D": 0,
            "O": 0,
            "lomb_test": 0,
            "ar1_test": 0,
        }
        CountMetrics.rejected_reasons_per_t2 = {}
        CountMetrics.bubble_accepted_per_t2 = defaultdict(int)
        CountMetrics.bubble_rejected_per_t2 = defaultdict(int)

    @staticmethod
    def add_bubble_accepted():
        CountMetrics.bubble_accepted += 1

    @staticmethod
    def add_bubble_rejected_because_can_not_fit():
        CountMetrics.rejected_because_can_not_fit += 1
        CountMetrics.bubble_rejected += 1

    @staticmethod
    def add_bubble(conditions: dict, t2_index: int):
        is_accepted = all(conditions.values())
        if is_accepted:
            CountMetrics.bubble_accepted += 1
            CountMetrics.bubble_accepted_per_t2[t2_index] += 1
        else:
            CountMetrics.bubble_rejected += 1
            CountMetrics.bubble_rejected_per_t2[t2_index] += 1
            for key, value in conditions.items():
                if not value:
                    CountMetrics.rejected_reasons[key] += 1

            # Add or update rejected_reasons for the specific t2_index
            if t2_index not in CountMetrics.rejected_reasons_per_t2:
                CountMetrics.rejected_reasons_per_t2[t2_index] = {
                    k: 0 for k in CountMetrics.rejected_reasons.keys()
                }
            for key, value in conditions.items():
                if not value:
                    CountMetrics.rejected_reasons_per_t2[t2_index][key] += 1

    @staticmethod
    def print_metrics():
        total = CountMetrics.bubble_accepted + CountMetrics.bubble_rejected
        bubble_accepted_percentage = 100 * CountMetrics.bubble_accepted / total if total != 0 else 0
        bubble_rejected_percentage = 100 * CountMetrics.bubble_rejected / total if total != 0 else 0

        print(f"rejected_because_can_not_fit count: {CountMetrics.rejected_because_can_not_fit}")
        print(f"bubble_accepted: {bubble_accepted_percentage:.2f}%")
        print(f"bubble_rejected: {bubble_rejected_percentage:.2f}%")

        for reason, count in CountMetrics.rejected_reasons.items():
            percentage = 100 * count / total
            print(f"rejected_because_of_{reason}: {percentage:.2f}%")

        with open("./temp_out/metrics_per_turn.csv", "w", newline="") as csvfile:
            fieldnames = ["t2_index", "accepted", "rejected"] + list(
                CountMetrics.rejected_reasons.keys()
            )
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for t2_index, reasons in CountMetrics.rejected_reasons_per_t2.items():
                accepted_this_t2 = CountMetrics.bubble_accepted_per_t2[t2_index]
                rejected_this_t2 = CountMetrics.bubble_rejected_per_t2[t2_index]
                total_this_t2 = accepted_this_t2 + rejected_this_t2

                accepted_percentage = "{:.2f}".format(100 * accepted_this_t2 / total_this_t2)
                rejected_percentage = "{:.2f}".format(100 * rejected_this_t2 / total_this_t2)

                row = {
                    "t2_index": t2_index,
                    "accepted": accepted_percentage,
                    "rejected": rejected_percentage,
                }
                for reason, count in reasons.items():
                    percentage = 100 * count / total_this_t2
                    row[reason] = "{:.2f}".format(percentage)
                writer.writerow(row)
