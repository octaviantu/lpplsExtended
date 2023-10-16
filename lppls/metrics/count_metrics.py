class CountMetrics:
    bubble_accepted = 0
    bubble_rejected = 0
    rejected_reasons = {
        "price": 0,
        "D": 0,
        "O": 0,
        "lomb_test": 0,
        "ar1_test": 0,
    }


    @staticmethod
    def reset():
        CountMetrics.bubble_accepted = 0
        CountMetrics.bubble_rejected = 0
        CountMetrics.rejected_because_of_price = 0
        CountMetrics.rejected_because_of_D = 0
        CountMetrics.rejected_because_can_not_fit = 0


    @staticmethod
    def add_bubble_accepted():
        CountMetrics.bubble_accepted += 1


    @staticmethod
    def add_bubble_rejected_because_can_not_fit():
        CountMetrics.rejected_because_can_not_fit += 1
        CountMetrics.bubble_rejected += 1


    @staticmethod
    def add_bubble(conditions: dict):
        if all(conditions.values()):
            CountMetrics.bubble_accepted += 1
        else:
            CountMetrics.bubble_rejected += 1
            for key, value in conditions.items():
                if not value:
                    CountMetrics.rejected_reasons[key] += 1

    @staticmethod
    def print_metrics():
        total = CountMetrics.bubble_accepted + CountMetrics.bubble_rejected
        bubble_accepted_percentage = 100 * CountMetrics.bubble_accepted / total if total != 0 else 0
        bubble_rejected_percentage = 100 * CountMetrics.bubble_rejected / total if total != 0 else 0

        print(f'bubble_accepted: {bubble_accepted_percentage:.2f}%')
        print(f'bubble_rejected: {bubble_rejected_percentage:.2f}%')

        for reason, count in CountMetrics.rejected_reasons.items():
            percentage = 100 * count / CountMetrics.bubble_rejected if CountMetrics.bubble_rejected != 0 else 0
            print(f'rejected_because_of_{reason}: {percentage:.2f}%')
