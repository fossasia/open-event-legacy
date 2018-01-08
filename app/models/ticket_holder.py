import base64
from StringIO import StringIO

import qrcode

from app.models import db


class TicketHolder(db.Model):
    __tablename__ = "ticket_holders"

    id = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String)
    lastname = db.Column(db.String)
    email = db.Column(db.String)
    address = db.Column(db.String)
    city = db.Column(db.String)
    state = db.Column(db.String)
    country = db.Column(db.String)
    ticket_id = db.Column(db.Integer, db.ForeignKey('ticket.id', ondelete='CASCADE'))
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id', ondelete='CASCADE'))
    order = db.relationship('Order', backref='ticket_holders')
    ticket = db.relationship('Ticket', backref='ticket_holders')
    checked_in = db.Column(db.Boolean, default=False)
    occupation = db.Column(db.String)
    occupation_detail = db.Column(db.String)
    expertise = db.Column(db.String)
    gender = db.Column(db.String)
    welcome_reception = db.Column(db.String)
    recruitment = db.Column(db.String)

    def __init__(self,
                 firstname=None,
                 lastname=None,
                 email=None,
                 address=None,
                 city=None,
                 state=None,
                 country=None,
                 occupation=None,
                 occupation_detail=None,
                 expertise=None,
                 gender=None,
                 welcome_reception=None,
                 recruitment=None,
                 ticket_id=None,
                 checked_in=False,
                 order_id=None):
        self.firstname = firstname
        self.lastname = lastname
        self.email = email
        self.city = city
        self.address = address
        self.state = state
        self.occupation = occupation
        self.occupation_detail = occupation_detail
        self.expertise = expertise
        self.gender = gender
        self.welcome_reception = welcome_reception
        self.recruitment = recruitment
        self.ticket_id = ticket_id
        self.country = country
        self.order_id = order_id
        self.checked_in = checked_in

    def __repr__(self):
        return '<TicketHolder %r>' % self.id

    def __str__(self):
        return '<TicketHolder %r>' % self.id

    def __unicode__(self):
        return '<TicketHolder %r>' % self.id

    @property
    def name(self):
        firstname = self.firstname if self.firstname else ''
        lastname = self.lastname if self.lastname else ''
        if firstname and lastname:
            return u'{} {}'.format(firstname, lastname)
        else:
            return ''

    @property
    def qr_code(self):
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=0,
        )
        qr.add_data(self.order.identifier + "-" + str(self.id))
        qr.make(fit=True)
        img = qr.make_image()

        buffer = StringIO()
        img.save(buffer, format="JPEG")
        img_str = base64.b64encode(buffer.getvalue())
        return img_str

    @property
    def serialize(self):
        """Return object data in easily serializable format"""
        return {'id': self.id,
                'firstname': self.firstname,
                'lastname': self.lastname,
                'email': self.email,
                'city': self.city,
                'address': self.address,
                'state': self.state,
                'occupation': self.occupation,
                'occupation_detail': self.occupation_detail,
                'expertise': self.expertise,
                'gender': self.gender,
                'welcome_reception': self.welcome_reception,
                'recruitment': self.recruitment,
                'country': self.country}
