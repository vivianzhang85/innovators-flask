# model/transactions.py
from __init__ import db
from datetime import datetime, timezone
import json

class MuseumVisitTransaction(db.Model):
    """
    TRANSACTIONAL table for museum visit reservations.
    Each reservation is an atomic transaction that can be:
    - Created (with payment simulation)
    - Cancelled (with rollback)
    - Completed (locked in)
    """
    __tablename__ = 'museum_visit_transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.String(50), unique=True, nullable=False)  # UUID format
    museum_name = db.Column(db.String(100), nullable=False)  # 'MET', 'Ice Cream', etc.
    visitor_name = db.Column(db.String(100), nullable=False)
    visit_date = db.Column(db.String(20), nullable=False)  # '2026-06-15'
    visit_time = db.Column(db.String(10), nullable=False)  # '10:00 AM'
    party_size = db.Column(db.Integer, nullable=False, default=1)
    total_price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, confirmed, cancelled, completed
    transaction_type = db.Column(db.String(20), nullable=False, default='reservation')
    
    # Transaction metadata
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    confirmed_at = db.Column(db.DateTime, nullable=True)
    cancelled_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # Scraped data snapshot at time of transaction
    scraped_hours = db.Column(db.JSON, nullable=True)  # Store what hours were when they booked
    scraped_address = db.Column(db.String(200), nullable=True)
    scraped_phone = db.Column(db.String(20), nullable=True)
    
    # Payment simulation fields
    payment_method = db.Column(db.String(20), nullable=True)  # 'credit_card', 'paypal'
    payment_id = db.Column(db.String(100), nullable=True)  # Simulated payment ID
    
    # Audit fields for rollback tracking
    original_status = db.Column(db.String(20), nullable=True)
    cancellation_reason = db.Column(db.String(200), nullable=True)
    
    def __init__(self, museum_name, visitor_name, visit_date, visit_time, party_size=1, scraped_data=None):
        import uuid
        self.transaction_id = f"MV-{uuid.uuid4().hex[:8].upper()}"
        self.museum_name = museum_name
        self.visitor_name = visitor_name
        self.visit_date = visit_date
        self.visit_time = visit_time
        self.party_size = party_size
        
        # Calculate price based on museum
        self.total_price = self._calculate_price(museum_name, party_size)
        
        # Store scraped data snapshot
        if scraped_data:
            self.scraped_hours = json.dumps(scraped_data.get('hours_data', {}))
            self.scraped_address = scraped_data.get('address', '')
            self.scraped_phone = scraped_data.get('phone', '')
    
    def _calculate_price(self, museum_name, party_size):
        """Calculate price based on museum and party size"""
        prices = {
            'MET Museum': 30.00,
            'Museum of Ice Cream': 39.00,
            'Ukrainian Museum': 12.00,
            'Empire State Building': 44.00
        }
        base_price = prices.get(museum_name, 25.00)
        return round(base_price * party_size, 2)
    
    @property
    def is_active(self):
        """Check if transaction is still active (not cancelled/completed)"""
        return self.status in ['pending', 'confirmed']
    
    @property
    def can_cancel(self):
        """Check if transaction can be cancelled"""
        return self.status in ['pending', 'confirmed']
    
    @property
    def can_complete(self):
        """Check if transaction can be marked as completed"""
        return self.status == 'confirmed'
    
    # TRANSACTIONAL METHODS - ATOMIC OPERATIONS
    
    def confirm_transaction(self):
        """Atomic confirmation - either succeeds or fails completely"""
        try:
            if self.status != 'pending':
                raise ValueError(f"Cannot confirm transaction in status: {self.status}")
            
            # Start transaction
            db.session.begin_nested()
            
            # 1. Update status
            self.status = 'confirmed'
            self.confirmed_at = datetime.now(timezone.utc)
            
            # 2. Simulate payment processing (in real app, would call payment API)
            self.payment_method = 'credit_card'
            self.payment_id = f"PAY-{self.transaction_id}"
            
            # 3. Create audit log (would be separate table in production)
            print(f"🎫 Transaction {self.transaction_id} confirmed - ${self.total_price} paid")
            
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Transaction confirmation failed: {e}")
            return False
    
    def cancel_transaction(self, reason="User requested"):
        """Atomic cancellation with rollback simulation"""
        try:
            if not self.can_cancel:
                raise ValueError(f"Cannot cancel transaction in status: {self.status}")
            
            # Start transaction
            db.session.begin_nested()
            
            # 1. Store original status for audit
            self.original_status = self.status
            
            # 2. Update status
            self.status = 'cancelled'
            self.cancelled_at = datetime.now(timezone.utc)
            self.cancellation_reason = reason
            
            # 3. Simulate refund (in real app, would call payment API)
            print(f"💸 Refunding ${self.total_price} for transaction {self.transaction_id}")
            
            # 4. Release "reserved slot" (in production, would update availability)
            
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Transaction cancellation failed: {e}")
            return False
    
    def complete_transaction(self):
        """Mark visit as completed (after actual visit)"""
        try:
            if not self.can_complete:
                raise ValueError(f"Cannot complete transaction in status: {self.status}")
            
            db.session.begin_nested()
            
            self.status = 'completed'
            self.completed_at = datetime.now(timezone.utc)
            
            # In production: Update analytics, send feedback email, etc.
            
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            return False
    
    def read(self):
        """Return transaction data as dict"""
        return {
            'transaction_id': self.transaction_id,
            'museum': self.museum_name,
            'visitor': self.visitor_name,
            'date': self.visit_date,
            'time': self.visit_time,
            'party_size': self.party_size,
            'total': self.total_price,
            'status': self.status,
            'created': self.created_at.isoformat() if self.created_at else None,
            'confirmed': self.confirmed_at.isoformat() if self.confirmed_at else None,
            'cancelled': self.cancelled_at.isoformat() if self.cancelled_at else None,
            'completed': self.completed_at.isoformat() if self.completed_at else None,
            'can_cancel': self.can_cancel,
            'can_complete': self.can_complete,
            'scraped_hours': json.loads(self.scraped_hours) if self.scraped_hours else None,
            'scraped_address': self.scraped_address,
            'scraped_phone': self.scraped_phone
        }

# Initialize database tables
def init_transactions():
    with app.app_context():
        db.create_all()
        print("✅ Transaction tables created")