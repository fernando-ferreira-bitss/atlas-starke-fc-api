"""Audit service for logging user actions."""

from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy.orm import Session

from starke.infrastructure.database.patrimony.audit_log import PatAuditLog


class AuditAction:
    """Audit action types."""

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXPORT = "export"
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    PASSWORD_RESET = "password_reset"
    PERMISSION_DENIED = "permission_denied"


class AuditService:
    """Service for recording audit logs."""

    def __init__(self, db: Session):
        self.db = db

    def log(
        self,
        action: str,
        user_id: Optional[int] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> PatAuditLog:
        """Record an audit log entry.

        Args:
            action: The action performed (create, read, update, delete, etc.)
            user_id: ID of the user who performed the action
            entity_type: Type of entity affected (e.g., 'pat_clients', 'pat_assets')
            entity_id: ID of the entity affected
            ip_address: IP address of the request
            user_agent: User agent string
            details: Additional details (old_values, new_values, etc.)

        Returns:
            The created audit log entry
        """
        audit_log = PatAuditLog(
            id=str(uuid4()),
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details,
            created_at=datetime.utcnow(),
        )
        self.db.add(audit_log)
        # Don't commit here - let the caller manage the transaction
        return audit_log

    def log_create(
        self,
        entity_type: str,
        entity_id: str,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        new_values: Optional[dict] = None,
    ) -> PatAuditLog:
        """Log a create action."""
        return self.log(
            action=AuditAction.CREATE,
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"new_values": new_values} if new_values else None,
        )

    def log_read(
        self,
        entity_type: str,
        entity_id: str,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        fields_accessed: Optional[list[str]] = None,
    ) -> PatAuditLog:
        """Log a read action."""
        return self.log(
            action=AuditAction.READ,
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"fields_accessed": fields_accessed} if fields_accessed else None,
        )

    def log_update(
        self,
        entity_type: str,
        entity_id: str,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        old_values: Optional[dict] = None,
        new_values: Optional[dict] = None,
    ) -> PatAuditLog:
        """Log an update action."""
        details = {}
        if old_values:
            details["old_values"] = old_values
        if new_values:
            details["new_values"] = new_values
        return self.log(
            action=AuditAction.UPDATE,
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details if details else None,
        )

    def log_delete(
        self,
        entity_type: str,
        entity_id: str,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        old_values: Optional[dict] = None,
    ) -> PatAuditLog:
        """Log a delete action."""
        return self.log(
            action=AuditAction.DELETE,
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"old_values": old_values} if old_values else None,
        )

    def log_export(
        self,
        entity_type: str,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        export_format: Optional[str] = None,
        record_count: Optional[int] = None,
        filters: Optional[dict] = None,
    ) -> PatAuditLog:
        """Log an export action."""
        details = {}
        if export_format:
            details["export_format"] = export_format
        if record_count is not None:
            details["record_count"] = record_count
        if filters:
            details["filters"] = filters
        return self.log(
            action=AuditAction.EXPORT,
            user_id=user_id,
            entity_type=entity_type,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details if details else None,
        )

    def log_login(
        self,
        user_id: int,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        email: Optional[str] = None,
    ) -> PatAuditLog:
        """Log a successful login."""
        return self.log(
            action=AuditAction.LOGIN,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"email": email} if email else None,
        )

    def log_login_failed(
        self,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        email: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> PatAuditLog:
        """Log a failed login attempt."""
        details = {}
        if email:
            details["email"] = email
        if reason:
            details["reason"] = reason
        return self.log(
            action=AuditAction.LOGIN_FAILED,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details if details else None,
        )

    def log_logout(
        self,
        user_id: int,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> PatAuditLog:
        """Log a logout."""
        return self.log(
            action=AuditAction.LOGOUT,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    def log_permission_denied(
        self,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        resource: Optional[str] = None,
        action_attempted: Optional[str] = None,
    ) -> PatAuditLog:
        """Log a permission denied event."""
        details = {}
        if resource:
            details["resource"] = resource
        if action_attempted:
            details["action_attempted"] = action_attempted
        return self.log(
            action=AuditAction.PERMISSION_DENIED,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details if details else None,
        )

    def log_sensitive_data_access(
        self,
        entity_type: str,
        entity_id: str,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        field_name: Optional[str] = None,
    ) -> PatAuditLog:
        """Log access to sensitive data (e.g., CPF/CNPJ decryption)."""
        return self.log(
            action=AuditAction.READ,
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={
                "sensitive_access": True,
                "field_name": field_name,
            },
        )
