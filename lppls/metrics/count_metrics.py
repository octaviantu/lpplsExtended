class CountMetrics:
    bubble_accepted = 0
    bubble_rejected = 0
    rejected_because_of_price = 0
    rejected_because_of_D = 0
    rejected_because_can_not_fit = 0

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
    def add_rejected_because_of_price():
        CountMetrics.rejected_because_of_price += 1
        CountMetrics.bubble_rejected += 1


    @staticmethod
    def add_rejected_because_of_D():
        CountMetrics.rejected_because_of_D += 1
        CountMetrics.bubble_rejected += 1


    @staticmethod
    def print_metrics():
        total = CountMetrics.bubble_accepted + CountMetrics.bubble_rejected
        bubble_accepted_percentage = 100 * CountMetrics.bubble_accepted / total if total != 0 else 0
        bubble_rejected_percentage = 100 * CountMetrics.bubble_rejected / total if total != 0 else 0
        
        rejected_because_of_price_percentage = 100 * CountMetrics.rejected_because_of_price / CountMetrics.bubble_rejected if CountMetrics.bubble_rejected != 0 else 0
        rejected_because_of_D_percentage = 100 * CountMetrics.rejected_because_of_D / CountMetrics.bubble_rejected if CountMetrics.bubble_rejected != 0 else 0
        rejected_because_can_not_fit_percentage = 100 * CountMetrics.rejected_because_can_not_fit / CountMetrics.bubble_rejected if CountMetrics.bubble_rejected != 0 else 0
        
        print(f'bubble_accepted: {bubble_accepted_percentage:.2f}%')
        print(f'bubble_rejected: {bubble_rejected_percentage:.2f}%')
        print(f'add_bubble_rejected_because_can_not_fit: {rejected_because_can_not_fit_percentage:.2f}%')
        print(f'rejected_because_of_price: {rejected_because_of_price_percentage:.2f}%')
        print(f'rejected_because_of_D: {rejected_because_of_D_percentage:.2f}%')
