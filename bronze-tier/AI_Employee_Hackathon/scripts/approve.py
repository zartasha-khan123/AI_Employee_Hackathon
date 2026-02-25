#!/usr/bin/env python3
"""Approve a pending plan.

This script approves a plan in Pending_Approval and moves it to Approved
for execution by the orchestrator.

Usage:
    python scripts/approve.py <plan-filename>

Example:
    python scripts/approve.py plan-email-test-20260215T143022.md
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.orchestrator.workflow_manager import WorkflowManager


def main() -> None:
    """Approve a pending plan."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/approve.py <plan-filename>")
        print("\nExample:")
        print("  python scripts/approve.py plan-email-test-20260215T143022.md")
        sys.exit(1)

    plan_filename = sys.argv[1]

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

    # Approve the plan
    try:
        approved_path = manager.approve_plan(plan_filename, approved_by="human")
        print(f"✅ Approved: {plan_filename}")
        print(f"   Moved to: {approved_path}")
        print("\nThe orchestrator will execute this plan on the next cycle.")
    except Exception as e:
        print(f"❌ Error approving plan: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
