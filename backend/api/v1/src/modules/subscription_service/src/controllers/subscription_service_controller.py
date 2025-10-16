from src.core.DAO.subscription_service_dao import SubscriptionServiceDAO


class SubscriptionServiceController:
   def __init__(self):
      self.subscription_service_dao = SubscriptionServiceDAO()

   def create_configuration(self, payload: dict):
      configuration_data = payload.get("configuration")
      return self.subscription_service_dao.create_configuration(configuration_data)

   def get_configuration(self, subscription_id: str):
      return self.subscription_service_dao.get_configuration(subscription_id)

   def update_configuration(self, subscription_id: str, updates: dict):
      return self.subscription_service_dao.update_configuration(subscription_id, updates)