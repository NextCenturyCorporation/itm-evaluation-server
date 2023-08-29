from swagger_server.models import Action
class Utility:
    def compare_actions(action1, action2: Action):
        check: bool = True
        #Action1 is being treated as a dict
        check = (action1.get("casualty_id") == action2.casualty_id and action1.get("scenario_id") == action2.scenario_id 
                 and action1.get("action_type") == action2.action_type and action1.get("unstructured") == action2.unstructured
                 and action1.get("justification") == action2.justification and action1.get("parameters") == action2.parameters)
        return check

