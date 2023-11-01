class CustomException(Exception):
    def __init__(self, user_message, tech_message):
        super().__init__(tech_message)
        self.user_message = user_message
        self.tech_message = tech_message
