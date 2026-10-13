"""Database models.

Table and column names follow the project specification (user_id, item_id,
claim_id, ...). Only portable column types are used so the same models work on
SQLite (development) and MySQL (production).
"""
from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db


def utcnow():
    """Naive UTC timestamp (portable across SQLite and MySQL)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------
class Role:
    USER = "user"      # students, faculty and staff
    ADMIN = "admin"
    ALL = (USER, ADMIN)


class ItemType:
    LOST = "lost"
    FOUND = "found"
    ALL = (LOST, FOUND)


class ItemStatus:
    ACTIVE = "ACTIVE"
    CLAIM_REQUESTED = "CLAIM_REQUESTED"
    CLAIM_APPROVED = "CLAIM_APPROVED"
    RETURNED = "RETURNED"          # reserved: hand-over recorded, awaiting completion
    COMPLETED = "COMPLETED"
    CLOSED = "CLOSED"              # closed by the reporter without a return
    REMOVED = "REMOVED"            # removed by an administrator
    ALL = (ACTIVE, CLAIM_REQUESTED, CLAIM_APPROVED, RETURNED, COMPLETED, CLOSED, REMOVED)
    OPEN = (ACTIVE, CLAIM_REQUESTED, CLAIM_APPROVED)

    LABELS = {
        ACTIVE: "Active",
        CLAIM_REQUESTED: "Claim requested",
        CLAIM_APPROVED: "Claim approved",
        RETURNED: "Returned",
        COMPLETED: "Completed",
        CLOSED: "Closed",
        REMOVED: "Removed by admin",
    }


class ClaimStatus:
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    RETURNED = "returned"
    ALL = (PENDING, APPROVED, REJECTED, RETURNED)
    OPEN = (PENDING, APPROVED)


class ReportStatus:
    OPEN = "open"
    REVIEWED = "reviewed"
    ACTIONED = "actioned"
    DISMISSED = "dismissed"
    ALL = (OPEN, REVIEWED, ACTIONED, DISMISSED)


CATEGORIES = [
    "Phone", "Wallet", "Bag", "ID Card", "Keys", "Laptop",
    "Books", "Earphones", "Bottle", "Documents", "Other",
]

CATEGORY_ICONS = {
    "Phone": "📱", "Wallet": "👛", "Bag": "🎒", "ID Card": "🪪", "Keys": "🔑",
    "Laptop": "💻", "Books": "📚", "Earphones": "🎧", "Bottle": "🧴",
    "Documents": "📄", "Other": "📦",
}

REPORT_REASONS = [
    "Spam", "Harassment", "False claim", "Suspicious behavior",
    "Scam", "Unrelated conversation", "Inappropriate content", "Other",
]


# --------------------------------------------------------------------------
# Models
# --------------------------------------------------------------------------
class User(db.Model):
    __tablename__ = "users"

    user_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=Role.USER, index=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)      # False = blocked
    is_restricted = db.Column(db.Boolean, nullable=False, default=False)  # read-only
    email_verified = db.Column(db.Boolean, nullable=False, default=False)
    warning_count = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    last_login_at = db.Column(db.DateTime)

    items = db.relationship("Item", back_populates="owner", lazy="dynamic")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == Role.ADMIN

    @property
    def public_name(self):
        """First name + last initial, used wherever other students see a user."""
        parts = self.name.split()
        if len(parts) > 1:
            return f"{parts[0]} {parts[-1][0]}."
        return parts[0] if parts else "Student"

    def __repr__(self):
        return f"<User {self.user_id} {self.email}>"


class Item(db.Model):
    __tablename__ = "items"

    item_id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(40), nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    location_name = db.Column(db.String(120), nullable=False, index=True)
    location_details = db.Column(db.String(255))   # "near the back row", etc.
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    event_date = db.Column(db.Date, nullable=False, index=True)
    item_type = db.Column(db.String(10), nullable=False, index=True)
    image_path = db.Column(db.String(255))
    status = db.Column(db.String(20), nullable=False, default=ItemStatus.ACTIVE, index=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)
    completed_at = db.Column(db.DateTime)

    owner = db.relationship("User", back_populates="items")
    claims = db.relationship(
        "Claim", back_populates="item", foreign_keys="Claim.item_id",
        lazy="dynamic", order_by="Claim.created_at",
    )

    __table_args__ = (
        db.Index("ix_items_status_type_created", "status", "item_type", "created_at"),
    )

    @property
    def is_lost(self):
        return self.item_type == ItemType.LOST

    @property
    def is_found(self):
        return self.item_type == ItemType.FOUND

    @property
    def is_public(self):
        return self.status == ItemStatus.ACTIVE

    @property
    def icon(self):
        return CATEGORY_ICONS.get(self.category, "📦")

    @property
    def status_label(self):
        return ItemStatus.LABELS.get(self.status, self.status)

    def public_coords(self):
        """Coordinates rounded to ~100 m so exact spots are not published."""
        if self.latitude is None or self.longitude is None:
            return None
        return round(self.latitude, 3), round(self.longitude, 3)

    def __repr__(self):
        return f"<Item {self.item_id} {self.item_type} {self.title!r} {self.status}>"


class Claim(db.Model):
    __tablename__ = "claims"

    claim_id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey("items.item_id"), nullable=False, index=True)
    claimant_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False, index=True)
    proof = db.Column(db.Text, nullable=False)              # unique description / marks
    serial_number = db.Column(db.String(120))
    purchase_info = db.Column(db.String(255))
    unique_marks = db.Column(db.Text)
    extra_proof = db.Column(db.Text)                        # added later by claimant
    proof_image_path = db.Column(db.String(255))           # private storage
    lost_item_id = db.Column(db.Integer, db.ForeignKey("items.item_id"))  # claimant's own lost report
    status = db.Column(db.String(20), nullable=False, default=ClaimStatus.PENDING, index=True)
    decision_note = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    decided_at = db.Column(db.DateTime)
    returned_at = db.Column(db.DateTime)

    item = db.relationship("Item", back_populates="claims", foreign_keys=[item_id])
    lost_item = db.relationship("Item", foreign_keys=[lost_item_id])
    claimant = db.relationship("User", foreign_keys=[claimant_id])
    messages = db.relationship(
        "Message", back_populates="claim", lazy="dynamic", order_by="Message.message_id",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        db.UniqueConstraint("item_id", "claimant_id", name="uq_claim_item_claimant"),
    )

    @property
    def finder(self):
        return self.item.owner

    @property
    def chat_open(self):
        return self.status in ClaimStatus.OPEN

    def is_participant(self, user):
        return user is not None and user.user_id in (self.claimant_id, self.item.owner_id)

    def can_view(self, user):
        return user is not None and (user.is_admin or self.is_participant(user))

    def __repr__(self):
        return f"<Claim {self.claim_id} item={self.item_id} {self.status}>"


class Message(db.Model):
    __tablename__ = "messages"

    message_id = db.Column(db.Integer, primary_key=True)
    claim_id = db.Column(db.Integer, db.ForeignKey("claims.claim_id"), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey("users.user_id"))   # NULL = system message
    body = db.Column(db.Text, nullable=False)
    is_suggestion = db.Column(db.Boolean, nullable=False, default=False)
    is_flagged = db.Column(db.Boolean, nullable=False, default=False)
    flag_reason = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    claim = db.relationship("Claim", back_populates="messages")
    sender = db.relationship("User")

    __table_args__ = (db.Index("ix_messages_claim_created", "claim_id", "created_at"),)

    @property
    def is_system(self):
        return self.sender_id is None


class Report(db.Model):
    """A moderation report about an item or a claim conversation."""
    __tablename__ = "reports"

    report_id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey("items.item_id"), nullable=False, index=True)
    claim_id = db.Column(db.Integer, db.ForeignKey("claims.claim_id"), index=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    reported_user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"))
    reason = db.Column(db.String(40), nullable=False)
    details = db.Column(db.Text)
    status = db.Column(db.String(20), nullable=False, default=ReportStatus.OPEN, index=True)
    admin_note = db.Column(db.String(255))
    resolved_by_id = db.Column(db.Integer, db.ForeignKey("users.user_id"))
    resolved_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    item = db.relationship("Item")
    claim = db.relationship("Claim")
    reporter = db.relationship("User", foreign_keys=[reporter_id])
    reported_user = db.relationship("User", foreign_keys=[reported_user_id])
    resolved_by = db.relationship("User", foreign_keys=[resolved_by_id])


class Notification(db.Model):
    __tablename__ = "notifications"

    notification_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False, index=True)
    kind = db.Column(db.String(30), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    link = db.Column(db.String(255))
    is_read = db.Column(db.Boolean, nullable=False, default=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    user = db.relationship("User")


class CampusLocation(db.Model):
    __tablename__ = "campus_locations"

    location_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    is_handover_point = db.Column(db.Boolean, nullable=False, default=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    def to_dict(self):
        return {
            "id": self.location_id, "name": self.name,
            "lat": self.latitude, "lng": self.longitude,
            "handover": self.is_handover_point,
        }


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    log_id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("users.user_id"))
    action = db.Column(db.String(60), nullable=False, index=True)
    target_type = db.Column(db.String(30))
    target_id = db.Column(db.Integer)
    details = db.Column(db.String(255))
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)

    actor = db.relationship("User")


class AppSetting(db.Model):
    __tablename__ = "app_settings"

    key = db.Column(db.String(60), primary_key=True)
    value = db.Column(db.String(255), nullable=False)
