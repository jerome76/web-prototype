from trytond.model import ModelView, ModelSQL, fields

all = ['User']


class User(ModelSQL, ModelView):
    """Defines a field, in which is saved, which user liked which topic.
    Note: The associated user is saved by default in each row"""
    __name__ = "hshn.user"

    hshn_id = fields.Many2One('hshn.hshn', 'hshnID')
