from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    String,
    Table,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

# Промежуточная таблица M:N между заявками и тегами
ticket_tags = Table(
    "ticket_tags",
    Base.metadata,
    Column(
        "ticket_id",
        ForeignKey("tickets.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "tag_id",
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class UserModel(Base):
    """Пользователь системы (клиент, оператор или администратор)."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # 1:N Связи
    created_tickets: Mapped[list["TicketModel"]] = relationship(
        back_populates="client",
        foreign_keys="TicketModel.client_id",
    )
    assigned_tickets: Mapped[list["TicketModel"]] = relationship(
        back_populates="operator",
        foreign_keys="TicketModel.operator_id",
    )


class TagModel(Base):
    """Тег/категория для классификации обращений."""

    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)

    # M:N Связь
    tickets: Mapped[list["TicketModel"]] = relationship(
        secondary=ticket_tags,
        back_populates="tags",
    )


class TicketModel(Base):
    """Клиентская заявка."""

    __tablename__ = "tickets"
    __table_args__ = (
        CheckConstraint(
            "confidence_score >= 0.0 AND confidence_score <= 1.0",
            name="confidence_score_range",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(50))
    confidence_score: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(50), default="Новая")
    manual_priority_override: Mapped[bool] = mapped_column(default=False)

    client_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    operator_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Связи 1:N
    client: Mapped["UserModel"] = relationship(
        back_populates="created_tickets",
        foreign_keys=[client_id],
    )
    operator: Mapped["UserModel | None"] = relationship(
        back_populates="assigned_tickets",
        foreign_keys=[operator_id],
    )
    audit_logs: Mapped[list["TicketAuditLogModel"]] = relationship(
        back_populates="ticket",
        cascade="all, delete-orphan",
    )

    # Связь M:N
    tags: Mapped[list["TagModel"]] = relationship(
        secondary=ticket_tags,
        back_populates="tickets",
    )


class TicketAuditLogModel(Base):
    """Журнал аудита ручных изменений приоритета."""

    __tablename__ = "ticket_audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id", ondelete="CASCADE"))
    changed_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    old_priority: Mapped[str] = mapped_column(String(50))
    new_priority: Mapped[str] = mapped_column(String(50))
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    ticket: Mapped["TicketModel"] = relationship(back_populates="audit_logs")
