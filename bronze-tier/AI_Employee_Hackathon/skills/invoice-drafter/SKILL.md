# Invoice Drafter Skill

**Version:** 1.0.0
**Type:** Document Generation
**Trigger:** Email with "invoice request" or manual invocation
**Requires Approval:** Yes (for sending, not for drafting)

---

## Purpose

Draft professional invoices based on email requests or manual input, using company billing rates and payment terms from Company_Handbook.md.

---

## Capabilities

- Parse invoice requests from emails
- Extract client details, line items, and amounts
- Apply standard billing rates from Company_Handbook.md
- Calculate subtotals, taxes, and totals
- Generate formatted invoice in markdown
- Save draft to vault/Accounting/drafts/

---

## Trigger Conditions

**Automatic:**
- Email subject contains: "invoice", "billing", "payment request"
- Email body mentions: "please invoice", "send invoice", "bill for"

**Manual:**
- User creates action file in vault/Needs_Action/ with type: invoice_request
- User invokes via orchestrator

---

## Input Context

**Required:**
- Client name and contact information
- Line items (description, quantity, rate)
- Invoice date and due date

**Optional:**
- Purchase order number
- Project reference
- Special terms or notes

**Company Context (from Company_Handbook.md):**
- Standard billing rates
- Payment terms (e.g., Net 30)
- Company details (name, address, tax ID)
- Bank account information

---

## Output Format

Creates markdown invoice in `vault/Accounting/drafts/invoice-YYYY-MM-DD-{client}.md`:

```markdown
---
type: invoice
status: draft
client: Acme Corp
invoice_number: INV-2026-001
invoice_date: 2026-02-22
due_date: 2026-03-24
subtotal: 5000.00
tax: 500.00
total: 5500.00
currency: USD
---

# Invoice INV-2026-001

**From:**
Your Company Name
123 Business St
City, State 12345
Tax ID: 12-3456789

**To:**
Acme Corp
456 Client Ave
City, State 67890

**Invoice Date:** February 22, 2026
**Due Date:** March 24, 2026 (Net 30)
**PO Number:** PO-12345

---

## Line Items

| Description | Quantity | Rate | Amount |
|-------------|----------|------|--------|
| Consulting Services - Week 1 | 40 hrs | $100/hr | $4,000.00 |
| Project Management | 10 hrs | $100/hr | $1,000.00 |

**Subtotal:** $5,000.00
**Tax (10%):** $500.00
**Total Due:** $5,500.00

---

## Payment Terms

Payment is due within 30 days of invoice date.

**Payment Methods:**
- Bank Transfer: [Account details]
- Check: Payable to [Company Name]

**Late Payment:** 1.5% monthly interest on overdue amounts.

---

## Notes

Thank you for your business!

For questions about this invoice, please contact: billing@yourcompany.com
```

---

## Decision Logic

**When to draft invoice:**
1. Email explicitly requests invoice
2. Work has been completed and logged
3. Client is in approved clients list

**When to escalate:**
1. Client not in system (new client)
2. Amount exceeds $10,000 (requires review)
3. Special terms requested
4. Unclear scope or pricing

---

## Workflow

1. **Parse Request**
   - Extract client details
   - Identify line items and amounts
   - Determine invoice date and due date

2. **Validate**
   - Check client exists in Company_Handbook.md
   - Verify billing rates are standard
   - Confirm work was completed

3. **Calculate**
   - Apply billing rates
   - Calculate subtotal
   - Add applicable taxes
   - Calculate total

4. **Generate Draft**
   - Create markdown invoice
   - Save to vault/Accounting/drafts/
   - Create action file for review

5. **Human Review**
   - User reviews draft in Obsidian
   - User approves or requests changes
   - Approved invoice moves to vault/Accounting/invoices/

6. **Send (Optional)**
   - If Odoo integration enabled, create in Odoo
   - If email requested, draft email with invoice attached
   - Requires separate approval for sending

---

## Safety & Permissions

- **DEV_MODE:** Not applicable (drafting only, no external actions)
- **Approval Required:** No for drafting, Yes for sending
- **Rate Limiting:** None (drafting is local operation)
- **Data Access:** Read Company_Handbook.md, write to vault/Accounting/

---

## Configuration

**Company_Handbook.md should include:**
```markdown
## Billing Information

**Standard Rates:**
- Consulting: $100/hour
- Development: $150/hour
- Project Management: $100/hour

**Payment Terms:**
- Net 30 (payment due within 30 days)
- Late fee: 1.5% per month on overdue amounts

**Company Details:**
- Legal Name: Your Company LLC
- Address: 123 Business St, City, State 12345
- Tax ID: 12-3456789
- Bank: First National Bank
- Account: 1234567890
- Routing: 987654321

**Approved Clients:**
- Acme Corp (contact: john@acme.com)
- Beta Industries (contact: jane@beta.com)
```

---

## Error Handling

**Missing Client Information:**
- Create draft with placeholder: [CLIENT NAME NEEDED]
- Flag for human review

**Unclear Line Items:**
- List all mentioned items with [VERIFY] tag
- Request clarification in action file

**Invalid Amounts:**
- Use $0.00 and flag for review
- Log warning in vault/Logs/errors/

---

## Testing

**Unit Tests:**
```bash
uv run pytest tests/test_invoice_drafter.py
```

**Manual Test:**
1. Create test email in vault/Needs_Action/
2. Run orchestrator
3. Check vault/Accounting/drafts/ for generated invoice
4. Verify calculations are correct
5. Confirm formatting is professional

---

## Integration

**Email Watcher:**
- Detects invoice requests in emails
- Creates action file with type: invoice_request

**Orchestrator:**
- Invokes invoice drafter skill
- Creates draft invoice
- Moves to Pending_Approval if amount > threshold

**Odoo Integration (Future):**
- Draft can be imported to Odoo
- Odoo invoice ID linked back to vault

---

## Future Enhancements

- Automatic invoice numbering (sequential)
- Multi-currency support
- Recurring invoice templates
- Time tracking integration
- Expense inclusion (billable expenses)
- PDF generation from markdown
- Email delivery with PDF attachment
- Payment tracking and reminders

---

## Examples

**Example 1: Simple Consulting Invoice**
```
Input: Email from client requesting invoice for 40 hours of consulting
Output: Invoice with 40 hrs × $100/hr = $4,000 + tax
```

**Example 2: Multi-Item Invoice**
```
Input: Email requesting invoice for development (20 hrs) and PM (5 hrs)
Output: Invoice with two line items, subtotal, tax, total
```

**Example 3: Recurring Monthly Invoice**
```
Input: Manual action file for monthly retainer
Output: Standard retainer invoice with fixed amount
```

---

## Dependencies

- `backend.utils.frontmatter` - Markdown file handling
- `backend.utils.timestamps` - Date formatting
- Company_Handbook.md - Billing rates and company info

---

## Version History

- **1.0.0** (2026-02-22) - Initial implementation
  - Basic invoice drafting
  - Standard rate calculation
  - Markdown output format
