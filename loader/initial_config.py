# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import datetime

from dateutil.relativedelta import relativedelta
from decimal import Decimal
from proteus import config, Model, Wizard

from trytond.modules.company.tests.tools import get_company

__all__ = ['create_fiscalyear', 'create_chart', 'get_accounts',
    'create_tax', 'set_tax_code']
CONFIG = "../tryton.conf"
DATABASE_NAME = "milliondog"
ACCOUNT_STOCK_METHOD = 'anglo_saxon'
POST_MOVE_SEQ = 'ACCN'
CUSTOMER_INVOICE_SEQ = 'CINV'
CUSTOMER_CREDIT_NOTE_SEQ = 'CCNO'
SUPPLIER_INVOICE_SEQ = 'SINV'
SUPPLIER_CREDIT_NOTE_SEQ = 'SCNO'
CHART_OF_ACCOUNT_NAME = 'Minimal Account Chart'
DEFAULT_VAT_TAX_PERCENTAGE = '0.08'
DEFAULT_VAT_TAX_NAME = 'VAT0'
DEFAULT_PARTY_SUPPLIER = 'Supplier'
DEFAULT_PAYMENT_TERM_NAME = 'cash'
DEFAULT_PRODUCT_CATEGORY = 'stockable'


def create_fiscalyear(company=None, today=None, config=None):
    """Create a fiscal year for the company on today"""
    FiscalYear = Model.get('account.fiscalyear', config=config)
    Sequence = Model.get('ir.sequence', config=config)
    SequenceStrict = Model.get('ir.sequence.strict', config=config)

    if not company:
        company = get_company()

    if not today:
        today = datetime.date.today()

    existing_fy = FiscalYear.find([('name', '=', str(today.year))], limit=1)
    if existing_fy:
        print("Warning: Fiscal year " + str(today.year) + " already exists!")
        return existing_fy[0]

    fiscalyear = FiscalYear(name=str(today.year))
    fiscalyear.start_date = today + relativedelta(month=1, day=1)
    fiscalyear.end_date = today + relativedelta(month=12, day=31)
    fiscalyear.company = company
    fiscalyear.account_stock_method = ACCOUNT_STOCK_METHOD

    post_move_sequence = Sequence(name=POST_MOVE_SEQ, code='account.move', number_next=10000,
        company=company)
    customer_invoice_sequence = SequenceStrict(name=CUSTOMER_INVOICE_SEQ, code='account.invoice', number_next=200000,
        company=company)
    customer_credit_note_sequence = SequenceStrict(name=CUSTOMER_CREDIT_NOTE_SEQ, code='account.invoice', number_next=100000,
        company=company)
    supplier_invoice_sequence = SequenceStrict(name=SUPPLIER_INVOICE_SEQ, code='account.invoice', number_next=600000,
        company=company)
    supplier_credit_note_sequence = SequenceStrict(name=SUPPLIER_CREDIT_NOTE_SEQ, code='account.invoice', number_next=500000,
        company=company)
    post_move_sequence.save()
    customer_invoice_sequence.save()
    customer_credit_note_sequence.save()
    supplier_invoice_sequence.save()
    supplier_credit_note_sequence.save()
    fiscalyear.post_move_sequence = post_move_sequence
    fiscalyear.out_invoice_sequence = customer_invoice_sequence
    fiscalyear.out_credit_note_sequence = customer_credit_note_sequence
    fiscalyear.in_invoice_sequence = supplier_invoice_sequence
    fiscalyear.in_credit_note_sequence = supplier_credit_note_sequence
    fiscalyear.save()
    fiscalyear.click('create_period')
    period = fiscalyear.periods[0]
    print("Success: Fiscal year " + str(today.year) + "' created!")
    return fiscalyear


def create_chart(company=None, config=None):
    """Create chart of accounts"""
    AccountTemplate = Model.get('account.account.template', config=config)
    ModelData = Model.get('ir.model.data')
    AccountChart = Model.get('account.account', config=config)

    existing_chart = AccountChart.find([('name', '=', CHART_OF_ACCOUNT_NAME)], limit=1)
    if existing_chart:
        print("Warning: Account Chart '" + CHART_OF_ACCOUNT_NAME + "' already exists!")
        return existing_chart[0]

    if not company:
        company = get_company()
    data, = ModelData.find([
            ('module', '=', 'account'),
            ('fs_id', '=', 'account_template_root_en'),
            ], limit=1)

    account_template = AccountTemplate(data.db_id)

    create_chart = Wizard('account.create_chart')
    create_chart.execute('account')
    create_chart.form.account_template = account_template
    create_chart.form.company = company
    create_chart.execute('create_account')

    accounts = get_accounts(company, config=config)

    create_chart.form.account_receivable = accounts['receivable']
    create_chart.form.account_payable = accounts['payable']
    create_chart.execute('create_properties')
    print("Success: Account Chart '" + CHART_OF_ACCOUNT_NAME + "' created!")
    return create_chart


def get_accounts(company=None, config=None):
    """Return accounts per kind"""
    Account = Model.get('account.account', config=config)

    if not company:
        company = get_company()

    accounts = Account.find([
            ('kind', 'in', ['receivable', 'payable', 'revenue', 'expense']),
            ('company', '=', company.id),
            ])
    accounts = {a.kind: a for a in accounts}
    cash, = Account.find([
            ('kind', '=', 'other'),
            ('company', '=', company.id),
            ('name', '=', 'Main Cash'),
            ])
    accounts['cash'] = cash
    tax, = Account.find([
            ('kind', '=', 'other'),
            ('company', '=', company.id),
            ('name', '=', 'Main Tax'),
            ])
    accounts['tax'] = tax
    cogs, = Account.find([
            ('kind', '=', 'other'),
            ('company', '=', company.id),
            ('name', '=', 'COGS'),
            ])
    accounts['cogs'] = cogs
    return accounts


def create_tax(rate, company=None, config=None):
    """Create a tax of rate"""
    Tax = Model.get('account.tax', config=config)

    existing_tax = Tax.find([('name', '=', DEFAULT_VAT_TAX_NAME)], limit=1)
    if existing_tax:
        print("Warning: Tax '" + DEFAULT_VAT_TAX_NAME + "' already exists!")
        return existing_tax[0]

    if not company:
        company = get_company()

    accounts = get_accounts(company)

    tax = Tax()
    tax.name = DEFAULT_VAT_TAX_NAME
    tax.description = tax.name
    tax.type = 'percentage'
    tax.rate = rate
    tax.invoice_account = accounts['tax']
    tax.credit_note_account = accounts['tax']
    tax.save()
    set_tax_code(tax)
    print("Success: Tax '" + DEFAULT_VAT_TAX_NAME + "' created!")
    return tax


def set_tax_code(tax, config=None):
    """Set code on tax"""
    TaxCode = Model.get('account.tax.code', config=config)
    invoice_base_code = TaxCode(name='Invoice Base')
    invoice_base_code.save()
    invoice_tax_code = TaxCode(name='Invoice Tax')
    invoice_tax_code.save()
    credit_note_base_code = TaxCode(name='Credit Note Base')
    credit_note_base_code.save()
    credit_note_tax_code = TaxCode(name='Credit Note Tax')
    credit_note_tax_code.save()

    tax.invoice_base_code = invoice_base_code
    tax.invoice_tax_code = invoice_tax_code
    tax.credit_note_base_code = credit_note_base_code
    tax.credit_note_tax_code = credit_note_tax_code
    tax.save()
    return tax


def create_supplier():
    Party = Model.get('party.party')
    existing_supplier = Party.find([('name', '=', DEFAULT_PARTY_SUPPLIER)], limit=1)
    if existing_supplier:
        print("Warning: Supplier '" + DEFAULT_PARTY_SUPPLIER + "' already exists!")
        return existing_supplier[0]
    else:
        supplier = Party(name=DEFAULT_PARTY_SUPPLIER)
        supplier.save()
        print("Success: Supplier '" + DEFAULT_PARTY_SUPPLIER + "' created!")
    return supplier

def create_payment_terms():
    PaymentTerm = Model.get('account.invoice.payment_term')
    existing_payment_term = PaymentTerm.find([('name', '=', DEFAULT_PAYMENT_TERM_NAME)], limit=1)
    if existing_payment_term:
        print("Warning: PaymentTerm '" + DEFAULT_PAYMENT_TERM_NAME + "' already exists!")
        return existing_payment_term[0]
    else:
        paymentterm = PaymentTerm(name=DEFAULT_PAYMENT_TERM_NAME)
        paymentterm.description = ''
        paymenttermline = paymentterm.lines.new()
        #PaymentTermLine = Model.get('account.invoice.payment_term.line')
        #paymenttermline = PaymentTermLine()
        paymenttermline.divisor = Decimal(0.0000000000000)
        paymenttermline.sequence = 1
        paymenttermline.amount = Decimal(0.0000)
        paymenttermline.ratio = Decimal(0.0000000)
        paymenttermline.type = 'remainder'
        paymenttermlinedeltas = paymenttermline.relativedeltas.new()
        paymenttermlinedeltas.days = 0
        paymenttermlinedeltas.weeks = 0
        paymenttermlinedeltas.months = 0
        paymentterm.save()
        print("Success: PaymentTerm '" + DEFAULT_PAYMENT_TERM_NAME + "' created!")
    return paymentterm


def create_product_config():
    ProductConfig = Model.get('product.configuration')
    existing_product_config = ProductConfig.find([('id', '>=', 0)], limit=1)
    if existing_product_config:
        print("Warning: ProductConfig '" + str(existing_product_config[0].id) + "' already exists!")
        return
    else:
        product_config = ProductConfig()
        product_config.default_accounts_category = True
        product_config.default_taxes_category = True
        product_config.default_cost_price_method = 'fixed'
        product_config.save()
        '''
        ModelField = Model.get('ir.model.field')
        modelfield = ModelField.find([('name', '=', 'cost_price_method')])
        if modelfield:
            Property = Model.get('ir.property')
            property = Property.find([('field', '=', modelfield[0].id)])
            if property:
                property[0].value = ',fixed'
                property[0].save()
            else:
                property = Property()
                property.field = modelfield[0].id
                property.value = ',fixed'
                property.save()
        '''


def create_account_configuration(accounts=None, company=None):
    if not company:
        company = get_company()
    # account.configuration
    Sequence = Model.get('ir.sequence')
    sequence = Sequence.find([('code', '=', 'account.payment.group')])
    ACModel = Model.get('ir.model')
    acmodel = ACModel.find([('model', '=', 'account.configuration')])
    ACModelField = Model.get('ir.model.field')
    acmodelfield = ACModelField.find([('name', '=', 'payment_group_sequence'), ('model', '=', acmodel[0].id)])
    AccountConfiguration = Model.get('account.configuration')
    existing = AccountConfiguration.find([('id', '>', '0')])
    if existing:
        print('Warning: Account configuration already exists!')
        return
    else:
        print('Creating account configuration.')
        accountconfiguration = AccountConfiguration()
        accountconfiguration.save()
        Property = Model.get('ir.property')
        acproperty = Property()
        acproperty.res = accountconfiguration
        acproperty.value = sequence[0]
        acproperty.field = acmodelfield[0]
        acproperty.save()
        acproperty = Property()
        ACModelField = Model.get('ir.model.field')
        acmodelfield = ACModelField.find([('name', '=', 'cost_price_counterpart_account'), ('model', '=', acmodel[0].id)])
        acproperty.res = accountconfiguration
        acproperty.value = accounts['cogs']
        acproperty.field = acmodelfield[0]
        acproperty.save()
        acproperty = Property()
        ACModelField = Model.get('ir.model.field')
        acmodelfield = ACModelField.find([('name', '=', 'stock_journal'), ('model', '=', acmodel[0].id)])
        acproperty.res = accountconfiguration
        acproperty.value = accounts['expense']
        acproperty.field = acmodelfield[0]
        acproperty.save()

    ModelField = Model.get('ir.model.field')
    modelfield = ModelField.find([('name', '=', 'cost_price_counterpart_account')])
    if modelfield:
        Property = Model.get('ir.property')
        property = Property.find([('field', '=', modelfield[0].id), ('value', 'like', 'account.account,%')])
        if len(property) == 0:
            property = Property()
            # property.rec_name = 'account.account'
            property.field = modelfield[0]
            property.value = accounts['cogs']
            property.company = company
            property.save()
    RootModel = Model.get('ir.model')
    rootmodel = RootModel.find([('model', '=', 'product.template')])
    modelfield = ModelField.find([('name', '=', 'account_revenue'), ('model', '=', rootmodel[0].id)])
    if modelfield:
        Property = Model.get('ir.property')
        property = Property.find([('field', '=', modelfield[0].id), ('value', 'like', 'account.account,%')])
        if len(property) == 0:
            property = Property()
            # property.rec_name = 'account.account'
            property.field = modelfield[0]
            property.value = accounts['revenue']
            property.company = company
            property.save()
    modelfield = ModelField.find([('name', '=', 'account_expense'), ('model', '=', rootmodel[0].id)])
    if modelfield:
        Property = Model.get('ir.property')
        property = Property.find([('field', '=', modelfield[0].id), ('value', 'like', 'account.account,%')])
        if len(property) == 0:
            property = Property()
            # property.rec_name = 'account.account'
            property.field = modelfield[0]
            property.value = accounts['expense']
            property.company = company
            property.save()
    rootmodel = RootModel.find([('model', '=', 'product.category')])
    modelfield = ModelField.find([('name', '=', 'account_revenue'), ('model', '=', rootmodel[0].id)])
    if modelfield:
        Property = Model.get('ir.property')
        property = Property.find([('field', '=', modelfield[0].id), ('value', 'like', 'account.account,%')])
        if len(property) == 0:
            property = Property()
            # property.rec_name = 'account.account'
            property.field = modelfield[0]
            property.value = accounts['revenue']
            property.company = company
            property.save()
    modelfield = ModelField.find([('name', '=', 'account_expense'), ('model', '=', rootmodel[0].id)])
    if modelfield:
        Property = Model.get('ir.property')
        property = Property.find([('field', '=', modelfield[0].id), ('value', 'like', 'account.account,%')])
        if len(property) == 0:
            property = Property()
            # property.rec_name = 'account.account'
            property.field = modelfield[0]
            property.value = accounts['expense']
            property.company = company
            property.save()
    rootmodel = RootModel.find([('model', '=', 'party.party')])
    modelfield = ModelField.find([('name', '=', 'account_payable'), ('model', '=', rootmodel[0].id)])
    if modelfield:
        Property = Model.get('ir.property')
        property = Property.find([('field', '=', modelfield[0].id), ('res', 'not like', 'party.party,%')])
        if len(property) == 0:
            property = Property()
            # property.rec_name = 'account.account'
            property.field = modelfield[0]
            property.value = accounts['payable']
            property.company = company
            property.save()
    modelfield = ModelField.find([('name', '=', 'account_receivable'), ('model', '=', rootmodel[0].id)])
    if modelfield:
        Property = Model.get('ir.property')
        property = Property.find([('field', '=', modelfield[0].id), ('res', 'not like', 'party.party,%')])
        if len(property) == 0:
            property = Property()
            # property.rec_name = 'account.account'
            property.field = modelfield[0]
            property.value = accounts['receivable']
            property.company = company
            property.save()


def get_account(accountlist, name):
    for i in accountlist:
        if name == i.name:
            return i
    return None

def create_product_category(accounts):
    Category = Model.get('product.category')
    duplicate = Category.find([('name', '=', DEFAULT_PRODUCT_CATEGORY)])
    if duplicate:
        print('Warning: category ' + duplicate[0].name + ' already exists!')
    else:
        category = Category()
        category.name = DEFAULT_PRODUCT_CATEGORY
        category.accounting = True
        category.taxes_parent = False
        category.account_parent = False
        Tax = Model.get('account.tax')
        tax = Tax.find([('name', '=', DEFAULT_VAT_TAX_NAME)], limit=1)
        category.supplier_taxes.append(tax[0])
        tax = Tax.find([('name', '=', DEFAULT_VAT_TAX_NAME)], limit=1)
        category.customer_taxes.append(tax[0])
        category.save()
        print("Success: Product category '" + DEFAULT_PRODUCT_CATEGORY + "' created!")
        Account = Model.get('account.account')
        stockaccountlist = Account.find([('kind', '=', 'stock')])
        PCModel = Model.get('ir.model')
        pcmodel = PCModel.find([('model', '=', 'product.category')])
        ModelField = Model.get('ir.model.field')
        modelfield = ModelField.find([('name', '=', 'account_expense'), ('model', '=', pcmodel[0].id)])
        Property = Model.get('ir.property')
        property = Property.find([('field', '=', modelfield[0].id), ('res', 'not like', 'product.category,%')])
        if len(property) == 0:
            property = Property()
            # property.rec_name = 'account.account'
            property.field = modelfield[0]
            property.value = accounts['expense']
            property.company = get_company()
            property.save()
        else:
            return
        modelfield = ModelField.find([('name', '=', 'account_revenue'), ('model', '=', pcmodel[0].id)])
        property = Property()
        property.field = modelfield[0]
        property.value = accounts['revenue']
        property.company = get_company()
        property.save()
        modelfield = ModelField.find([('name', '=', 'account_stock'), ('model', '=', pcmodel[0].id)])
        property = Property()
        property.field = modelfield[0]
        property.value = get_account(stockaccountlist, 'Stock')
        property.company = get_company()
        property.save()
        modelfield = ModelField.find([('name', '=', 'account_cogs'), ('model', '=', pcmodel[0].id)])
        property = Property()
        property.field = modelfield[0]
        property.value = accounts['cogs']
        property.company = get_company()
        property.save()
        modelfield = ModelField.find([('name', '=', 'account_stock_lost_found'), ('model', '=', pcmodel[0].id)])
        property = Property()
        property.field = modelfield[0]
        property.value = get_account(stockaccountlist, 'Stock Lost and Found')
        property.company = get_company()
        property.save()
        modelfield = ModelField.find([('name', '=', 'account_stock_supplier'), ('model', '=', pcmodel[0].id)])
        property = Property()
        property.field = modelfield[0]
        property.value = get_account(stockaccountlist, 'Stock Supplier')
        property.company = get_company()
        property.save()
        modelfield = ModelField.find([('name', '=', 'account_stock_production'), ('model', '=', pcmodel[0].id)])
        property = Property()
        property.field = modelfield[0]
        property.value = get_account(stockaccountlist, 'Stock Production')
        property.company = get_company()
        property.save()
        modelfield = ModelField.find([('name', '=', 'account_stock_customer'), ('model', '=', pcmodel[0].id)])
        property = Property()
        property.field = modelfield[0]
        property.value = get_account(stockaccountlist, 'Stock Customer')
        property.company = get_company()


def main():
    company = get_company()
    fiscalyear = create_fiscalyear(company)
    _ = create_chart(company)
    accounts = get_accounts(company)
    payable = accounts['payable']
    expense = accounts['expense']
    tax = accounts['tax']
    tax = create_tax(Decimal(DEFAULT_VAT_TAX_PERCENTAGE))
    create_account_configuration(accounts, company)
    create_payment_terms()
    supplier = create_supplier()
    # create product config
    create_product_config()
    create_product_category(accounts)


if __name__ == '__main__':
    config.set_trytond(DATABASE_NAME, config_file=CONFIG)
    main()
