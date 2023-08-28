from swagger_server.models import Action
class Utility:
    def compare_actions(action1: Action, action2: Action):
        check: bool = True
        check = (action1.casualty_id == action2.casualty_id and action1.scenario_id == action2.scenario_id 
                 and action1.action_type == action2.action_type and action1.unstructured == action2.unstructured
                 and action1.justification == action2.justification and action1.parameters == action2.parameters)
        return check

