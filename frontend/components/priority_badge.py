from PySide6.QtWidgets import QLabel


class PriorityBadge(QLabel):

    def __init__(self, priority="Green"):
        super().__init__()

        self.setAlignment(
            self.alignment()
        )

        self.setMinimumWidth(
            80
        )

        self.set_priority(
            priority
        )

    # ====================================
    # SET PRIORITY
    # ====================================

    def set_priority(self, priority):

        self.priority = priority or "Medium"

        self.setText(
            self.priority
        )

        if priority == "Red":

            self.setStyleSheet("""
                QLabel {
                    background-color: #FEE2E2;
                    color: #991B1B;
                    border-radius: 6px;
                    padding: 5px 10px;
                    font-weight: bold;
                }
            """)

        elif priority == "Orange":

            self.setStyleSheet("""
                QLabel {
                    background-color: #FFEDD5;
                    color: #9A3412;
                    border-radius: 6px;
                    padding: 5px 10px;
                    font-weight: bold;
                }
            """)

        elif priority == "Yellow":

            self.setStyleSheet("""
                QLabel {
                    background-color: #FEF3C7;
                    color: #92400E;
                    border-radius: 6px;
                    padding: 5px 10px;
                    font-weight: bold;
                }
            """)

        else:

            self.setStyleSheet("""
                QLabel {
                    background-color: #DCFCE7;
                    color: #166534;
                    border-radius: 6px;
                    padding: 5px 10px;
                    font-weight: bold;
                }
            """)