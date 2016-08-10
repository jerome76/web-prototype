"""defines the business logic"""
from trytond.model import ModelView, ModelSQL, fields
from trytond.pyson import Eval, Bool, Not
from trytond.pool import Pool
from trytond.tools import get_smtp_server
from trytond.transaction import Transaction
import datetime


__all__ = ['Hshn']


class Hshn(ModelSQL, ModelView):
    """ Class for business logic of the module hshn.
        The used fields, set deafult values,
        button actions and special logic for sending a mail are defined in the Class """
    __name__ = "hshn.hshn"

    topic = fields.Char('Topic', required=True, help='Please enter your topic')
    project_study_spo3 = fields.Selection([
        ('None', ''),
        ('SEPS', 'SEPS'),
        ('PSBWL', 'PSBWL'),
        ('PSWIN', 'PSWIN'),
        ('PSIT', 'PSIT'),
    ], 'Project study SPO3', states={
        'readonly': Eval('spo_selection') != 'SPO3',
        'required': Bool(Eval('spo_selection') != 'SPO4')
    }, help='Please select the project study for which you will submit the proposal'+
        '\n SEPS  = Project Study Software development EDV-No: 281531'+
        '\n PSBWL = Project Study BWL EDV-No:281542'+
        '\n PSWIN = Project Study economic computer science EDV-No: 281560'+
        '\n PSIT  = Project Study IT-Systems EDV-No:281584')
    project_study_spo4 = fields.Selection([
        ('None', ''),
        ('PSEIS', 'PSEIS'),
        ('PSEMU', 'PSEMU'),
        ('PSIT', 'PSIT'),
        ('PSAIS', 'PSAIS'),
        ('PSIM', 'PSIM'),
        ('PSSMU', 'PSSMU'),
        ('PSSMM', 'PSSMM'),
        ('PSSRM', 'PSSRM'),
    ], 'Project study SPO4', states={
        'readonly': Eval('spo_selection') != 'SPO4',
        'required': Bool(Eval('spo_selection') != 'SPO3')
    }, help='Please select the project study for which you will submit the proposal' +
        '\n PSEIS = Project Study Enterprise Information Systems EDV-No: 281761' +
        '\n PSEMU = Project Study Development mobile Enterprise Applications EDV-No:281760' +
        '\n PSIT  = Project Study IT-Systems EDV-No: 281765' +
        '\n PSAIS = Project Study Analytic Information Systems and Data Science EDV-No:281784' +
        '\n PSIM  = Project Study Information Management EDV-No: 281780' +
        '\n PSSMU = Project Study Social Media in enterprise context' +
        '\n PSSMM = Project Study Social Media Management and Audiovisual Communication EDV-No:281796' +
        '\n PSSRM = Project Study Social Relationship Management EDV-No:281790')
    description = fields.Text('Description', required=True, help='Please enter a detailed ' +
                                                                 'description of the topic \n Note: You can also add attachments')
    input_date = fields.Date('Date', readonly=True)
    like_count = fields.Integer('Like count', readonly=True)
    lecturer = fields.Many2One('party.party', 'Lecturer', required=True, select=True, )
    mail = fields.Boolean('Mail to lecturer', states={
        'readonly': Not(Bool(Eval('lecturer'))),
    }, help='Select the lecturer which you want to assign')
    spo_selection = fields.Selection([
        ('SPO3', 'SPO3'),
        ('SPO4', 'SPO4')
    ], 'SPO', help='Please select the SPO for which you will submit the proposal')

    @classmethod
    def default_like_count(cls):
        """Set the default value of the like_count field to 0.
        Because a new topic doesn't has likes"""
        return 0

    @classmethod
    def default_input_date(cls):
        """Set the default value of the input_date fied to the current date"""
        return datetime.date.today()

    @classmethod
    def default_spo_selection(cls):
        """Set the default value of the spo_selection fied to SPO3"""
        return 'SPO3'

    @classmethod
    def default_project_study_spo3(cls):
        """Set the default value of the project_study_spo3 fied to None.
        This is necessary because this field is required  and doesn't can be undefined"""
        return 'None'

    @classmethod
    def default_project_study_spo4(cls):
        """Set the default value of the project_study_spo4 fied to None.
        This is necessary because this field is required  and doesn't can be undefined"""
        return 'None'

    @classmethod
    def default_like_state(cls):
        """Set the default value of the state field to false"""
        return 'like'

    @classmethod
    def __setup__(cls):
        super(Hshn, cls).__setup__()
        """Initialize the like_btn"""
        cls._buttons.update({
            'like_btn': {
            }
            })

    @fields.depends('spo_selection')
    def on_change_spo_selection(self):
        """Change the value of the fields project_study_spo3 and project_study_spo4 to ''
        and None depending on which SPO was selectet in the spo_selection field.
        This is necessary for the required fields logic"""
        if self.spo_selection == 'SPO3':
            self.project_study_spo3 = ''
            self.project_study_spo4 = 'None'
        else:
            self.project_study_spo4 = ''
            self.project_study_spo3 = 'None'

    @classmethod
    @ModelView.button
    def like_btn(cls, records):
        """Defines the logic by clicking on the Button.
        Count up the field like_count by one and save the changes into the database.
        It also insets a row in the table hshn_user to save which user liked which topic.
        This will be needed for deactivating the like button and activation the dislike button"""

        pool = Pool()
        model_hshn = pool.get('hshn.hshn')

        # get the current user ID
        user_id = Transaction().user

        model_user = pool.get('hshn.user')

        for row in records:

            # check if user already liked the topic
            user_list = model_user.search([('create_uid', '=', user_id)])

            for user in user_list:
                if user.hshn_id is not None:
                    if row.id is user.hshn_id.id:
                        # topic already liked
                        return

            # save the liked topic to the user
            values2 = [{'id':user_id, 'hshn_id':row.id}]
            model_user.create(values2)

            # count up the likes
            if row.like_count is None:
                row.like_count = 1
            else:
                row.like_count += 1

        # Save the updatet record
        model_hshn.save(records)

        return 'reload'


    @classmethod
    def validate(cls, records_mail):
        """Check before saving if the field mail is selected(True) and send in this case the entered
        values via mail to the lecturer.
        The email will be send to all email addresses which are saved for the lecturer in
        party.contact_mechanism"""
        super(Hshn, cls)

        pool = Pool()
        model = pool.get('party.contact_mechanism')
        try:
            server = get_smtp_server()
        except :
            pass

        # get the record
        row = records_mail

        # Read in the mail content
        mail_content = {}
        file = open('../trytond/modules/hshn/mail.txt')
        for line in file:
            try:
                name, var = line.partition('=')
            except ValueError:
                continue
            mail_content[name.strip()] = var

        return
        # send a mail
        if row.mail is True:

            # set the spo
            if row.spo_selection == 'SPO3':
                project_study = row.project_study_spo3
            else:
                project_study = row.project_study_spo4

            # get the party of the selected lecturer
            records_contact = model.search([('party', '=', row.lecturer)])

            # send a mail to each mail address which is saved for the lecturer
            for row2 in records_contact:
                if row2.type == 'email':
                    try:
                        server.sendmail(mail_content['mail_address'], row2.value, mail_content['mail_message1'] +
                            str(row.lecturer.name) +
                            mail_content['mail_message2'] +
                            '\n'+cls.topic.string+': ' + str(row.topic) + '\n'+cls.description.string+': ' +
                            str(row.description) + '\n' + str(row.spo_selection) + mail_content['mail_message3'] +
                            str(project_study))
                    except:
                        pass

        # set mail to false
        row.mail = False
