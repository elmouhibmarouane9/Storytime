"""Document renderers — invoices as Markdown and as print-ready HTML."""

from __future__ import annotations

from typing import Any

from .finance import invoice_balance, invoice_discount, invoice_paid, invoice_subtotal, invoice_tax, invoice_total
from .models import CURRENCY_SYMBOLS, money

BRAND = "MEM Digital"


def _agency(settings: dict) -> dict:
    return settings.get("agency") or {}


def invoice_markdown(invoice: dict, client: dict | None, settings: dict) -> str:
    agency = _agency(settings)
    currency = invoice.get("currency", "USD")
    client = client or {}
    lines = [
        f"# INVOICE {invoice.get('id', '')}",
        "",
        f"**{agency.get('name', BRAND)}**  ",
        f"{agency.get('email', '')}  ",
        f"{agency.get('phone', '')}  ",
        f"{agency.get('address', '')}  ",
        f"Tax ID: {agency.get('tax_id', '')}",
        "",
        "---",
        "",
        f"**Billed to**  ",
        f"{client.get('company') or client.get('name', '—')}  ",
        f"{client.get('name', '')} · {client.get('email', '')}  ",
        f"{client.get('location', '')}",
        "",
        f"**Issue date:** {invoice.get('issue_date', '—')}  ",
        f"**Due date:** {invoice.get('due_date', '—')} ({invoice.get('terms', 'Net 14')})  ",
        f"**Status:** {invoice.get('status', 'draft')}",
        "",
        "---",
        "",
        "| Description | Qty | Rate | Amount |",
        "|---|---:|---:|---:|",
    ]
    for item in invoice.get("items", []):
        qty = float(item.get("qty", 1) or 0)
        rate = float(item.get("rate", 0) or 0)
        unit = f' {item.get("unit")}' if item.get("unit") else ""
        lines.append(
            f"| {item.get('desc', '—')} | {qty:g}{unit} | {money(rate, currency, 2)} | {money(qty * rate, currency, 2)} |"
        )
    lines += [
        "",
        f"**Subtotal** {money(invoice_subtotal(invoice), currency, 2)}  ",
    ]
    if invoice_discount(invoice):
        lines.append(f"**Discount** −{money(invoice_discount(invoice), currency, 2)}  ")
    if invoice_tax(invoice):
        lines.append(f"**Tax ({float(invoice.get('tax_rate', 0)) * 100:.1f}%)** {money(invoice_tax(invoice), currency, 2)}  ")
    lines += [
        f"## Total due: {money(invoice_total(invoice), currency, 2)}",
        "",
        f"Paid to date: {money(invoice_paid(invoice), currency, 2)} · **Balance: {money(invoice_balance(invoice), currency, 2)}**",
    ]
    if invoice.get("notes"):
        lines += ["", f"_{invoice['notes']}_"]
    lines += [
        "",
        "---",
        "",
        f"Pay to {agency.get('name', BRAND)} · {agency.get('email', '')} · Payment terms {invoice.get('terms', 'Net 14')}.",
    ]
    return "\n".join(lines)


def invoice_html(invoice: dict, client: dict | None, settings: dict) -> str:
    """Print-ready HTML — open it, hit Ctrl+P, send a PDF. No dependencies."""
    agency = _agency(settings)
    client = client or {}
    currency = invoice.get("currency", "USD")
    rows = []
    for item in invoice.get("items", []):
        qty = float(item.get("qty", 1) or 0)
        rate = float(item.get("rate", 0) or 0)
        unit = f' {item.get("unit")}' if item.get("unit") else ""
        rows.append(
            f"<tr><td>{item.get('desc','—')}</td><td class='num'>{qty:g}{unit}</td>"
            f"<td class='num'>{money(rate, currency, 2)}</td><td class='num'>{money(qty * rate, currency, 2)}</td></tr>"
        )
    extras = ""
    if invoice_discount(invoice):
        extras += f"<tr><td class='lab'>Discount</td><td class='num'>−{money(invoice_discount(invoice), currency, 2)}</td></tr>"
    if invoice_tax(invoice):
        extras += (f"<tr><td class='lab'>Tax {float(invoice.get('tax_rate', 0)) * 100:.1f}%</td>"
                   f"<td class='num'>{money(invoice_tax(invoice), currency, 2)}</td></tr>")
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Invoice {invoice.get('id','')}</title>
<style>
  :root {{ --gold:#B8860B; --ink:#0A0D11; }}
  * {{ box-sizing: border-box; }}
  body {{ font-family: 'Helvetica Neue', Arial, sans-serif; color: #14181d; margin: 0; padding: 48px; background:#fff; }}
  .head {{ display:flex; justify-content:space-between; align-items:flex-start; border-bottom:3px solid var(--gold); padding-bottom:18px; }}
  .brand {{ font-size:22px; font-weight:800; letter-spacing:.22em; }}
  .muted {{ color:#6b7480; font-size:12px; line-height:1.5; }}
  h1 {{ font-size:34px; margin:26px 0 4px; letter-spacing:-.02em; }}
  .meta {{ display:flex; gap:48px; margin:18px 0 26px; font-size:13px; }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; }}
  th {{ text-align:left; text-transform:uppercase; letter-spacing:.1em; font-size:10px; color:#6b7480; border-bottom:1px solid #d8dde3; padding:8px 6px; }}
  td {{ padding:10px 6px; border-bottom:1px solid #eef1f4; }}
  .num {{ text-align:right; font-variant-numeric: tabular-nums; }}
  .lab {{ text-align:right; color:#6b7480; border:none; }}
  .total {{ margin-top:14px; text-align:right; font-size:24px; font-weight:800; }}
  .foot {{ margin-top:40px; border-top:1px solid #e6eaee; padding-top:14px; font-size:11px; color:#6b7480; }}
  @media print {{ body {{ padding:24px; }} }}
</style></head>
<body>
  <div class="head">
    <div>
      <div class="brand">{agency.get('name', BRAND).upper()}</div>
      <div class="muted">{agency.get('address','')}<br>{agency.get('email','')} · {agency.get('phone','')}<br>Tax ID {agency.get('tax_id','')}</div>
    </div>
    <div class="muted" style="text-align:right">
      <div class="brand" style="font-size:14px;letter-spacing:.18em">INVOICE</div>
      <div>{invoice.get('id','')}</div>
    </div>
  </div>
  <h1>{money(invoice_total(invoice), currency, 2)}</h1>
  <div class="muted">{invoice.get('status','draft').upper()} · Balance due {money(invoice_balance(invoice), currency, 2)}</div>
  <div class="meta">
    <div><b>Billed to</b><br>{client.get('company') or client.get('name','—')}<br>{client.get('name','')}<br>{client.get('email','')}</div>
    <div><b>Issued</b><br>{invoice.get('issue_date','—')}</div>
    <div><b>Due</b><br>{invoice.get('due_date','—')}<br>{invoice.get('terms','Net 14')}</div>
  </div>
  <table>
    <thead><tr><th>Description</th><th class="num">Qty</th><th class="num">Rate</th><th class="num">Amount</th></tr></thead>
    <tbody>{''.join(rows)}</tbody>
    <tfoot>
      <tr><td colspan="3" class="lab">Subtotal</td><td class="num">{money(invoice_subtotal(invoice), currency, 2)}</td></tr>
      {'<tr><td colspan="2"></td>' + extras + '</tr>' if extras else ''}
      <tr><td colspan="3" class="lab"><b>Total</b></td><td class="num"><b>{money(invoice_total(invoice), currency, 2)}</b></td></tr>
      <tr><td colspan="3" class="lab">Paid</td><td class="num">{money(invoice_paid(invoice), currency, 2)}</td></tr>
      <tr><td colspan="3" class="lab"><b>Balance due</b></td><td class="num"><b>{money(invoice_balance(invoice), currency, 2)}</b></td></tr>
    </tfoot>
  </table>
  <div class="total">Balance {money(invoice_balance(invoice), currency, 2)}</div>
  <div class="foot">{invoice.get('notes','')}<br>Pay to {agency.get('name', BRAND)} · {agency.get('email','')} · {invoice.get('terms','Net 14')}. Thank you.</div>
</body></html>"""
