"""Notification service for email notifications."""

import asyncio
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from app.config import settings


class NotificationService:
    """Service for sending notifications."""

    @staticmethod
    def _create_email_message(
        to_email: str, subject: str, html_content: str
    ) -> MIMEMultipart:
        """Create an email message.

        Args:
            to_email: Recipient email
            subject: Email subject
            html_content: HTML content

        Returns:
            MIMEMultipart: Email message
        """
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = f"{settings.email_from_name} <{settings.email_from}>"
        message["To"] = to_email

        html_part = MIMEText(html_content, "html")
        message.attach(html_part)

        return message

    @staticmethod
    def send_email_sync(to_email: str, subject: str, html_content: str) -> bool:
        """Send an email synchronously (for Celery tasks).

        Args:
            to_email: Recipient email
            subject: Email subject
            html_content: HTML content

        Returns:
            bool: True if sent successfully
        """
        try:
            message = NotificationService._create_email_message(
                to_email, subject, html_content
            )

            # Connect to SMTP server
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
                server.starttls()
                if settings.smtp_user and settings.smtp_password:
                    server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(message)

            return True
        except Exception as e:
            print(f"Failed to send email to {to_email}: {str(e)}")
            return False

    @staticmethod
    async def send_email_async(
        to_email: str, subject: str, html_content: str
    ) -> bool:
        """Send an email asynchronously.

        Args:
            to_email: Recipient email
            subject: Email subject
            html_content: HTML content

        Returns:
            bool: True if sent successfully
        """
        return await asyncio.to_thread(
            NotificationService.send_email_sync, to_email, subject, html_content
        )

    @staticmethod
    def get_incident_created_email(incident_data: dict[str, Any]) -> tuple[str, str]:
        """Generate incident created email content.

        Args:
            incident_data: Incident data

        Returns:
            tuple: (subject, html_content)
        """
        subject = f"New Incident Created: {incident_data['title']}"

        html_content = f"""
        <html>
        <body>
            <h2>New Incident Created</h2>
            <p>A new incident has been created and assigned to you.</p>

            <h3>Incident Details:</h3>
            <ul>
                <li><strong>Title:</strong> {incident_data['title']}</li>
                <li><strong>Priority:</strong> {incident_data['priority']}</li>
                <li><strong>Status:</strong> {incident_data['status']}</li>
                <li><strong>Description:</strong> {incident_data['description']}</li>
            </ul>

            <h3>SLA Information:</h3>
            <ul>
                <li><strong>Response Deadline:</strong> {incident_data.get('response_deadline', 'N/A')}</li>
                <li><strong>Resolution Deadline:</strong> {incident_data.get('resolution_deadline', 'N/A')}</li>
            </ul>

            <p>Please review and respond to this incident as soon as possible.</p>
        </body>
        </html>
        """

        return subject, html_content

    @staticmethod
    def get_sla_breach_email(incident_data: dict[str, Any]) -> tuple[str, str]:
        """Generate SLA breach email content.

        Args:
            incident_data: Incident data

        Returns:
            tuple: (subject, html_content)
        """
        subject = f"⚠️ SLA BREACH: {incident_data['title']}"

        html_content = f"""
        <html>
        <body>
            <h2 style="color: red;">⚠️ SLA Breach Notification</h2>
            <p>An SLA breach has been detected for the following incident:</p>

            <h3>Incident Details:</h3>
            <ul>
                <li><strong>Title:</strong> {incident_data['title']}</li>
                <li><strong>Priority:</strong> {incident_data['priority']}</li>
                <li><strong>Status:</strong> {incident_data['status']}</li>
                <li><strong>Breach Type:</strong> {incident_data.get('breach_type', 'Resolution')}</li>
            </ul>

            <h3>SLA Information:</h3>
            <ul>
                <li><strong>Response Deadline:</strong> {incident_data.get('response_deadline', 'N/A')}</li>
                <li><strong>Resolution Deadline:</strong> {incident_data.get('resolution_deadline', 'N/A')}</li>
                <li><strong>Time Breached:</strong> {incident_data.get('time_breached', 'N/A')}</li>
            </ul>

            <p style="color: red;"><strong>IMMEDIATE ACTION REQUIRED!</strong></p>
        </body>
        </html>
        """

        return subject, html_content

    @staticmethod
    def get_approaching_deadline_email(
        incident_data: dict[str, Any]
    ) -> tuple[str, str]:
        """Generate approaching deadline email content.

        Args:
            incident_data: Incident data

        Returns:
            tuple: (subject, html_content)
        """
        subject = f"⏰ SLA Deadline Approaching: {incident_data['title']}"

        html_content = f"""
        <html>
        <body>
            <h2 style="color: orange;">⏰ SLA Deadline Approaching</h2>
            <p>An SLA deadline is approaching for the following incident:</p>

            <h3>Incident Details:</h3>
            <ul>
                <li><strong>Title:</strong> {incident_data['title']}</li>
                <li><strong>Priority:</strong> {incident_data['priority']}</li>
                <li><strong>Status:</strong> {incident_data['status']}</li>
            </ul>

            <h3>SLA Information:</h3>
            <ul>
                <li><strong>Resolution Deadline:</strong> {incident_data.get('resolution_deadline', 'N/A')}</li>
                <li><strong>Time Remaining:</strong> {incident_data.get('time_remaining', 'N/A')}</li>
            </ul>

            <p><strong>Please prioritize this incident to avoid SLA breach.</strong></p>
        </body>
        </html>
        """

        return subject, html_content

    @staticmethod
    def get_incident_resolved_email(incident_data: dict[str, Any]) -> tuple[str, str]:
        """Generate incident resolved email content.

        Args:
            incident_data: Incident data

        Returns:
            tuple: (subject, html_content)
        """
        subject = f"✅ Incident Resolved: {incident_data['title']}"

        html_content = f"""
        <html>
        <body>
            <h2 style="color: green;">✅ Incident Resolved</h2>
            <p>The following incident has been resolved:</p>

            <h3>Incident Details:</h3>
            <ul>
                <li><strong>Title:</strong> {incident_data['title']}</li>
                <li><strong>Priority:</strong> {incident_data['priority']}</li>
                <li><strong>Resolution Time:</strong> {incident_data.get('resolution_time', 'N/A')}</li>
            </ul>

            <h3>SLA Status:</h3>
            <ul>
                <li><strong>SLA Met:</strong> {incident_data.get('sla_met', 'Yes')}</li>
                <li><strong>Resolution Deadline:</strong> {incident_data.get('resolution_deadline', 'N/A')}</li>
            </ul>

            <p>Thank you for your prompt resolution of this incident.</p>
        </body>
        </html>
        """

        return subject, html_content
