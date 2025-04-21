from knowledge_base.embedchain.helpers.json_serializable import JSONSerializable


class BaseLoader(JSONSerializable):
    def __init__(self):
        pass

    def load_data(self):
        """
        Implemented by child classes
        """
        pass
