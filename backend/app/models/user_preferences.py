from beanie import Document


class UserPreferences(Document):
    user_id: str
    theme: str = "light"
    language: str = "en"
    units: str = "metric"
    report_template: str = "standard"
    
    class Settings:
        name = "user_preferences"
