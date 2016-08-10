"""init class"""
from trytond.pool import Pool
from .hshn import Hshn, HshnReport
from .user import User


def register():
    """Register the used Classes"""
    Pool.register(
        Hshn, User,
        module='hshn', type_='model')
    Pool.register(
        HshnReport,
        module='hshn', type_='report')
