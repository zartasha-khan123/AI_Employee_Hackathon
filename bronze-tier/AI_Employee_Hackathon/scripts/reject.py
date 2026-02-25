#!/usr/bin/env python3
"""Reject a pending plan.

This script rejects a plan in Pending_Approval and moves it to Rejected
with a reason for the rejection.

Usage:
    python scripts/reject.py <plan-filename> <reason>

Example:
    python scripts/reject.py plan-email-test-20260215T143022.md "Not appropriate"
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.orchestrator.workflow_manager import WorkflowManager


def main() -> None:
    """Reject a pending plan."""
    if len(sys.argv) < 3:
        print("Usage: python scripts/reject.py <plan-filename> <reason>")
        print("\nExample:")
        print('  python scripts/reject.py plan-email-test-20260215T143022.md "Not appropriate"')
        sys.exit(1)

    plan_filename = sys.argv[1]
    reason = sys.argv[2]

    # Initialize workflow manager
    vault_path = Path("./vault")
    if not vault_path.exists():
        print(f"❌ Error: Vault not found at {vault_path}")
        sys.exit(1)

    manager = WorkflowManager(vault_path=vault_path)

    # Check if plan exists
    pending_path = manager.pending_approval / plan_filename
    if not pending_path.exists():
        print(f"❌ Error: Plan not found in Pending_Approval: {plan_filename}")
        print("\nAvailable plans:")
        pending_plans = manager.get_pending_approvals()
        if pending_plans:
            for plan in pending_plans:
                print(f"  - {plan.name}")
        else:
            print("  (none)")
        sys.exit(1)

    # Reject the plan
    try:
        rejected_path = manager.reject_plan(plan_filename, reason=reason, rejected_by="human")
        print(f"❌ Rejected: {plan_filename}")
        print(f"   Reason: {reason}")
        print(f"   Moved to: {rejected_path}")
    except Exception as e:
        print(f"❌ Error rejecting plan: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
