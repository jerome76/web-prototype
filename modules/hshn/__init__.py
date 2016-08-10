"""init class"""
from trytond.pool import Pool
from .hshn import Hshn
from .user import User



def register():
    """Register the used Classes"""
    Pool.register(
        Hshn, User,
        module='hshn', type_='model')
