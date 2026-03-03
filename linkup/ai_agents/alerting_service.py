"""
Alerting service for AI Agents platform.

This module provides alerting functionality for system health monitoring,
including support for multiple notification channels (email, Slack, webhooks, etc.).

Requirements: 20.7
"""
import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
import requests

logger = logging.getLogger('ai_agents.alerting')


class AlertingService:
    """
    Service for triggering and managing alerts for threshold violations.
    
    This service supports multiple notification channels:
    - Logging (always enabled)
    - Email notifications
    - Slack notifications
    - Custom webhook notifications
    
    Requirements: 20.7
    """
    
    @classmethod
    def trigger_alerts(cls, violations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Trigger alerts for threshold violations across all configured channels.
        
        Args:
            violations: List of violation dictionaries containing:
                - metric: Name of the metric that violated threshold
                - current_value: Current value of the metric
                - threshold: Threshold value that was exceeded
                - severity: Severity level ('warning', 'critical')
                - message: Human-readable description
        
        Returns:
            Dictionary with alert results:
                - status: 'SUCCESS' or 'FAILED'
                - alerts_sent: Number of alerts successfully sent
                - channels_used: List of channels that received alerts
                - errors: List of any errors encountered
        
        Requirements: 20.7
        """
        if not violations:
            return {
                'status': 'SUCCESS',
                'alerts_sent': 0,
                'channels_used': [],
                'message': 'No violations to alert'
            }
        
        # Get alert configuration
        alert_config = getattr(settings, 'AI_AGENT_ALERT_CONFIG', {})
        
        # Check if alerting is enabled
        if not alert_config.get('enabled', True):
            logger.info('Alerting is disabled in configuration')
            return {
                'status': 'SUCCESS',
                'alerts_sent': 0,
                'channels_used': [],
                'message': 'Alerting disabled'
            }
        
        channels_used = []
        errors = []
        alerts_sent = 0
        
        # Always log violations
        cls._log_violations(violations)
        channels_used.append('log')
        alerts_sent += len(violations)
        
        # Get configured notification channels
        notification_channels = alert_config.get('notification_channels', ['log'])
        
        # Send email alerts if configured
        if 'email' in notification_channels:
            result = cls._send_email_alerts(violations, alert_config.get('email', {}))
            if result['status'] == 'SUCCESS':
                channels_used.append('email')
                alerts_sent += result['sent']
            else:
                errors.append(f"Email: {result.get('error', 'Unknown error')}")
        
        # Send Slack alerts if configured
        if 'slack' in notification_channels:
            result = cls._send_slack_alerts(violations, alert_config.get('slack', {}))
            if result['status'] == 'SUCCESS':
                channels_used.append('slack')
                alerts_sent += result['sent']
            else:
                errors.append(f"Slack: {result.get('error', 'Unknown error')}")
        
        # Send webhook alerts if configured
        if 'webhook' in notification_channels:
            result = cls._send_webhook_alerts(violations, alert_config.get('webhook', {}))
            if result['status'] == 'SUCCESS':
                channels_used.append('webhook')
                alerts_sent += result['sent']
            else:
                errors.append(f"Webhook: {result.get('error', 'Unknown error')}")
        
        return {
            'status': 'SUCCESS' if not errors or channels_used else 'PARTIAL',
            'alerts_sent': alerts_sent,
            'channels_used': channels_used,
            'errors': errors if errors else None,
            'timestamp': timezone.now().isoformat()
        }
    
    @classmethod
    def _log_violations(cls, violations: List[Dict[str, Any]]) -> None:
        """
        Log violations to the application log.
        
        Args:
            violations: List of violation dictionaries
        """
        for violation in violations:
            severity = violation.get('severity', 'warning')
            message = violation.get('message', 'Unknown violation')
            metric = violation.get('metric', 'unknown')
            current_value = violation.get('current_value', 'N/A')
            threshold = violation.get('threshold', 'N/A')
            
            log_message = (
                f"THRESHOLD VIOLATION - {metric}: {message} "
                f"(current: {current_value}, threshold: {threshold})"
            )
            
            if severity == 'critical':
                logger.critical(log_message)
            elif severity == 'warning':
                logger.warning(log_message)
            else:
                logger.info(log_message)
    
    @classmethod
    def _send_email_alerts(cls, violations: List[Dict[str, Any]], 
                          email_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send email alerts for violations.
        
        Args:
            violations: List of violation dictionaries
            email_config: Email configuration dictionary
        
        Returns:
            Dictionary with send result
        """
        try:
            if not email_config.get('enabled', False):
                return {
                    'status': 'SKIPPED',
                    'sent': 0,
                    'message': 'Email alerts not enabled'
                }
            
            recipients = email_config.get('recipients', [])
            if not recipients:
                return {
                    'status': 'FAILED',
                    'sent': 0,
                    'error': 'No email recipients configured'
                }
            
            # Build email content
            subject_prefix = email_config.get('subject_prefix', '[AI Agent Platform Alert]')
            subject = f"{subject_prefix} {len(violations)} Threshold Violation(s) Detected"
            
            # Create email body
            body_lines = [
                "AI Agent Platform Health Alert",
                "=" * 50,
                f"Timestamp: {timezone.now().isoformat()}",
                f"Total Violations: {len(violations)}",
                "",
                "Violations:",
                ""
            ]
            
            for i, violation in enumerate(violations, 1):
                body_lines.extend([
                    f"{i}. {violation.get('metric', 'Unknown')}",
                    f"   Severity: {violation.get('severity', 'unknown').upper()}",
                    f"   Current Value: {violation.get('current_value', 'N/A')}",
                    f"   Threshold: {violation.get('threshold', 'N/A')}",
                    f"   Message: {violation.get('message', 'No details')}",
                    ""
                ])
            
            body = "\n".join(body_lines)
            
            # Send email
            send_mail(
                subject=subject,
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=recipients,
                fail_silently=False
            )
            
            logger.info(f"Email alerts sent to {len(recipients)} recipient(s)")
            
            return {
                'status': 'SUCCESS',
                'sent': len(violations),
                'recipients': len(recipients)
            }
            
        except Exception as e:
            logger.error(f"Error sending email alerts: {str(e)}", exc_info=True)
            return {
                'status': 'FAILED',
                'sent': 0,
                'error': str(e)
            }
    
    @classmethod
    def _send_slack_alerts(cls, violations: List[Dict[str, Any]], 
                          slack_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send Slack alerts for violations.
        
        Args:
            violations: List of violation dictionaries
            slack_config: Slack configuration dictionary
        
        Returns:
            Dictionary with send result
        """
        try:
            if not slack_config.get('enabled', False):
                return {
                    'status': 'SKIPPED',
                    'sent': 0,
                    'message': 'Slack alerts not enabled'
                }
            
            webhook_url = slack_config.get('webhook_url', '')
            if not webhook_url:
                return {
                    'status': 'FAILED',
                    'sent': 0,
                    'error': 'No Slack webhook URL configured'
                }
            
            # Build Slack message
            channel = slack_config.get('channel', '#alerts')
            
            # Create message blocks
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"🚨 AI Agent Platform Alert: {len(violations)} Violation(s)"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Timestamp:* {timezone.now().isoformat()}"
                    }
                },
                {
                    "type": "divider"
                }
            ]
            
            # Add violation details
            for violation in violations:
                severity_emoji = "🔴" if violation.get('severity') == 'critical' else "⚠️"
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f"{severity_emoji} *{violation.get('metric', 'Unknown')}*\n"
                            f"*Severity:* {violation.get('severity', 'unknown').upper()}\n"
                            f"*Current:* {violation.get('current_value', 'N/A')}\n"
                            f"*Threshold:* {violation.get('threshold', 'N/A')}\n"
                            f"*Message:* {violation.get('message', 'No details')}"
                        )
                    }
                })
            
            # Send to Slack
            payload = {
                "channel": channel,
                "blocks": blocks
            }
            
            response = requests.post(
                webhook_url,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Slack alerts sent successfully to {channel}")
                return {
                    'status': 'SUCCESS',
                    'sent': len(violations)
                }
            else:
                logger.error(f"Slack API error: {response.status_code} - {response.text}")
                return {
                    'status': 'FAILED',
                    'sent': 0,
                    'error': f"Slack API returned {response.status_code}"
                }
            
        except Exception as e:
            logger.error(f"Error sending Slack alerts: {str(e)}", exc_info=True)
            return {
                'status': 'FAILED',
                'sent': 0,
                'error': str(e)
            }
    
    @classmethod
    def _send_webhook_alerts(cls, violations: List[Dict[str, Any]], 
                            webhook_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send webhook alerts for violations.
        
        Args:
            violations: List of violation dictionaries
            webhook_config: Webhook configuration dictionary
        
        Returns:
            Dictionary with send result
        """
        try:
            if not webhook_config.get('enabled', False):
                return {
                    'status': 'SKIPPED',
                    'sent': 0,
                    'message': 'Webhook alerts not enabled'
                }
            
            webhook_url = webhook_config.get('url', '')
            if not webhook_url:
                return {
                    'status': 'FAILED',
                    'sent': 0,
                    'error': 'No webhook URL configured'
                }
            
            # Build webhook payload
            payload = {
                'event': 'threshold_violation',
                'timestamp': timezone.now().isoformat(),
                'violation_count': len(violations),
                'violations': violations
            }
            
            # Get HTTP method and headers
            method = webhook_config.get('method', 'POST').upper()
            headers = webhook_config.get('headers', {})
            headers.setdefault('Content-Type', 'application/json')
            
            # Send webhook request
            if method == 'POST':
                response = requests.post(
                    webhook_url,
                    json=payload,
                    headers=headers,
                    timeout=10
                )
            elif method == 'PUT':
                response = requests.put(
                    webhook_url,
                    json=payload,
                    headers=headers,
                    timeout=10
                )
            else:
                return {
                    'status': 'FAILED',
                    'sent': 0,
                    'error': f"Unsupported HTTP method: {method}"
                }
            
            if 200 <= response.status_code < 300:
                logger.info(f"Webhook alerts sent successfully to {webhook_url}")
                return {
                    'status': 'SUCCESS',
                    'sent': len(violations)
                }
            else:
                logger.error(f"Webhook error: {response.status_code} - {response.text}")
                return {
                    'status': 'FAILED',
                    'sent': 0,
                    'error': f"Webhook returned {response.status_code}"
                }
            
        except Exception as e:
            logger.error(f"Error sending webhook alerts: {str(e)}", exc_info=True)
            return {
                'status': 'FAILED',
                'sent': 0,
                'error': str(e)
            }
    
    @classmethod
    def format_alert_message(cls, violations: List[Dict[str, Any]]) -> str:
        """
        Format violations into a human-readable alert message.
        
        Args:
            violations: List of violation dictionaries
        
        Returns:
            Formatted alert message string
        """
        if not violations:
            return "No violations detected"
        
        lines = [
            "AI Agent Platform Health Alert",
            "=" * 50,
            f"Timestamp: {timezone.now().isoformat()}",
            f"Total Violations: {len(violations)}",
            "",
            "Violations:",
            ""
        ]
        
        for i, violation in enumerate(violations, 1):
            lines.extend([
                f"{i}. {violation.get('metric', 'Unknown')}",
                f"   Severity: {violation.get('severity', 'unknown').upper()}",
                f"   Current Value: {violation.get('current_value', 'N/A')}",
                f"   Threshold: {violation.get('threshold', 'N/A')}",
                f"   Message: {violation.get('message', 'No details')}",
                ""
            ])
        
        return "\n".join(lines)
