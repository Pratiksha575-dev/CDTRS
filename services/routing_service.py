class RoutingService:

    def suggest_routing(self, text):
        """
        Analyse extracted document text
        and suggest department / employee.

        Later:
        Regex → explicit indicators
        spaCy → entity extraction
        RapidFuzz → database matching
        """

        print("Mock routing analysis")

        return {
            "department": None,
            "employee": None,
            "confidence": 0.0
        }


routing_service = RoutingService()