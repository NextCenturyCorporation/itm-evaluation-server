from connexion.frameworks import flask as flask_utils
import six

from swagger_server.models.base_model_ import Model


class JSONEncoder(flask_utils.FlaskJSONProvider):
    include_nulls = False

    def default(self, o):
        if isinstance(o, Model):
            dikt = {}
            for attr, _ in six.iteritems(o.swagger_types):
                value = getattr(o, attr)
                if value is None and not self.include_nulls:
                    continue
                attr = o.attribute_map[attr]
                dikt[attr] = value
            return dikt
        return flask_utils.FlaskJSONProvider.default(self, o)
