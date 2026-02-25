"""Email MCP Server - sends emails with safety controls.

This MCP server provides email sending capabilities with built-in safety features:
- DEV_MODE simulation
- Recipient allowlist
- Content scanning for sensitive data
- Rate limiting
- Approval requirements for risky emails

Protocol: stdio-based MCP server
Tools: send_email
"""

import json
import logging
import os
import sys
from typing import Any

from dotenv import load_dotenv

from backend.mcp_servers.email_server.email_sender import EmailSender
from backend.mcp_servers.email_server.safety import SafetyChecker

logger = logging.getLogger(__name__)


class EmailMCPServer:
    """MCP server for email operations."""

    def __init__(self):
        """Initialize the email MCP server."""
        load_dotenv()

        self.dev_mode = os.getenv("DEV_MODE", "true").lower() == "true"
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.allowed_recipients = os.getenv("ALLOWED_RECIPIENTS", "").split(",")

        self.email_sender = EmailSender(
            smtp_host=self.smtp_host,
            smtp_port=self.smtp_port,
            smtp_user=self.smtp_user,
            smtp_password=self.smtp_password,
            dev_mode=self.dev_mode,
        )

        self.safety_checker = SafetyChecker(
            allowed_recipients=self.allowed_recipients, dev_mode=self.dev_mode
        )

        self.logger = logging.getLogger(__name__)

    def handle_request(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle MCP protocol request.

        Args:
            request: MCP request dictionary.

        Returns:
            MCP response dictionary.
        """
        method = request.get("method")

        if method == "tools/list":
            return self._list_tools()
        elif method == "tools/call":
            return self._call_tool(request)
        else:
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {"code": -32601, "message": f"Method not found: {method}"},
            }

    def _list_tools(self) -> dict[str, Any]:
        """List available tools."""
        return {
            "jsonrpc": "2.0",
            "result": {
                "tools": [
                    {
                        "name": "send_email",
                        "description": "Send an email with safety controls and rate limiting",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "to": {
                                    "type": "string",
                                    "description": "Recipient email address",
                                },
                                "subject": {
                                    "type": "string",
                                    "description": "Email subject line",
                                },
                                "body": {
                                    "type": "string",
                                    "description": "Email body (plain text or HTML)",
                                },
                                "cc": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "CC recipients (optional)",
                                },
                            },
                            "required": ["to", "subject", "body"],
                        },
                    }
                ]
            },
        }

    def _call_tool(self, request: dict[str, Any]) -> dict[str, Any]:
        """Call a tool.

        Args:
            request: MCP tool call request.

        Returns:
            MCP response with tool result.
        """
        params = request.get("params", {})
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if tool_name == "send_email":
            return self._send_email(request.get("id"), arguments)
        else:
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {"code": -32602, "message": f"Unknown tool: {tool_name}"},
            }

    def _send_email(self, request_id: Any, arguments: dict[str, Any]) -> dict[str, Any]:
        """Send an email with safety checks.

        Args:
            request_id: MCP request ID.
            arguments: Tool arguments (to, subject, body, cc).

        Returns:
            MCP response with send result.
        """
        to = arguments.get("to")
        subject = arguments.get("subject")
        body = arguments.get("body")
        cc = arguments.get("cc", [])

        # Safety checks
        safety_result = self.safety_checker.check_email(to, subject, body, cc)

        if not safety_result["safe"]:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(
                                {
                                    "status": "blocked",
                                    "reason": safety_result["reason"],
                                    "details": safety_result.get("details", ""),
                                }
                            ),
                        }
                    ]
                },
            }

        # Send email
        try:
            result = self.email_sender.send(to, subject, body, cc)

            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(
                                {
                                    "status": "success" if result["success"] else "failed",
                                    "message_id": result.get("message_id"),
                                    "message": result.get("message", ""),
                                    "dev_mode": self.dev_mode,
                                }
                            ),
                        }
                    ]
                },
            }

        except Exception as e:
            self.logger.exception("Error sending email")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32000, "message": f"Email send failed: {str(e)}"},
            }

    def run(self) -> None:
        """Run the MCP server (stdio protocol)."""
        self.logger.info("Email MCP Server starting (dev_mode: %s)", self.dev_mode)

        try:
            for line in sys.stdin:
                if not line.strip():
                    continue

                try:
                    request = json.loads(line)
                    response = self.handle_request(request)
                    print(json.dumps(response), flush=True)

                except json.JSONDecodeError:
                    self.logger.error("Invalid JSON received: %s", line)
                    error_response = {
                        "jsonrpc": "2.0",
                        "error": {"code": -32700, "message": "Parse error"},
                    }
                    print(json.dumps(error_response), flush=True)

                except Exception as e:
                    self.logger.exception("Error handling request")
                    error_response = {
                        "jsonrpc": "2.0",
                        "error": {"code": -32603, "message": f"Internal error: {str(e)}"},
                    }
                    print(json.dumps(error_response), flush=True)

        except KeyboardInterrupt:
            self.logger.info("Email MCP Server stopped by user")


def main() -> None:
    """Entry point for the email MCP server."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stderr)],  # Log to stderr, not stdout
    )

    server = EmailMCPServer()
    server.run()


if __name__ == "__main__":
    main()
