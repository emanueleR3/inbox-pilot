from src.core.DAO.subscription_service_dao import SubscriptionServiceDAO


class SubscriptionServiceController:
     def __init__(self):
        self.subscription_service_dao = SubscriptionServiceDAO()

     def create_configuration(self, payload: dict):
        configuration_data = payload.get("configuration")

        return self.subscription_service_dao.create_configuration(configuration_data)