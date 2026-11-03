# وزن الفلترة · Wazn Screen

فلترة شرعية لأسهم EGX33 كمكتبة Python وHTTP API وMCP server. مفتوحة المصدر عشان أي حد يراجع المنطق بنفسه.

> ⚠️ أداة بيانات وتحليل، مش استشارة استثمارية ولا فتوى شرعية. القرار النهائي لصاحبه.

## اللي بتعمله

- **قائمة شرعية نقطة-في-الزمن**: snapshot لأعضاء مؤشر `EGX_SHARIAH` عند تاريخ معيّن (fail-closed لو مفيش snapshot أو قديم).
- **فلترة مالية AAOIFI** (معيار 21): نسب الدين والنقد الربوي والدخل غير المتوافق.
- **حساب التطهير**: نصيب الدخل غير المتوافق في توزيعات نقدية.

نفس المنطق المستخدم في `wazn-engine` (private)، مفصول هنا عشان يتدقّق مستقل.

## التثبيت

```bash
pip install wazn-screen               # المكتبة الأساسية
pip install "wazn-screen[api]"        # + HTTP API
pip install "wazn-screen[mcp]"        # + MCP server
```

## الاستخدام كمكتبة

```python
from datetime import date
from decimal import Decimal
from wazn_screen import load_default_universe, screen, Financials

u = load_default_universe()
print(u.can_buy("ETEL", "LocalSecurity_IN", date(2026, 11, 3)))
# Decision(allowed=True, reasons=())

print(u.can_buy("TBIL", "Tbills", date(2026, 11, 3)))
# Decision(allowed=False, reasons=('TBIL is not an EGX33 constituent...', 'TBIL security class Tbills is banned'))

r = screen(Financials(
    symbol="ACME",
    interest_bearing_debt=Decimal("100"),
    interest_bearing_cash_and_investments=Decimal("50"),
    non_compliant_income=Decimal("2"),
    total_income=Decimal("1000"),
    market_cap=Decimal("1000"),
))
print(r.passed, r.failures)
```

## CLI

```bash
wazn-screen symbol ETEL                   # يراجع الرمز في آخر snapshot
wazn-screen universe --date 2026-11-03    # يطبع أعضاء المؤشر في اليوم ده
```

## HTTP API

```bash
wazn-screen-api --host 0.0.0.0 --port 8787
# GET /universe?on=2026-11-03
# GET /can-buy/ETEL?security_class=LocalSecurity_IN&on=2026-11-03
# POST /screen            {financials...}
# POST /purification      {dividends_received, non_compliant_income, total_income}
```

## MCP server

يشتغل على stdio:

```json
{
  "mcpServers": {
    "wazn-screen": {
      "command": "uvx",
      "args": ["--from", "wazn-screen", "wazn-screen-mcp"]
    }
  }
}
```

Tools: `can_buy`, `list_universe`, `screen_financials`, `purification_amount`.

## قاعدة البيانات

قائمة الأعضاء في `src/wazn_screen/data/egx33.yaml`. كل مراجعة نصف سنوية من البورصة = snapshot جديد؛ ما تعدّلش القديم (point-in-time integrity).

## العتبات (AAOIFI #21)

| النسبة | الحد |
| --- | --- |
| الدين الربوي ÷ القيمة السوقية | < 30% |
| النقد والاستثمارات الربوية ÷ القيمة السوقية | < 30% |
| الدخل غير المتوافق ÷ إجمالي الدخل | < 5% |

تغيير العتبات = قرار فقهي، ما يتعملش في كود صامت.

## المساهمة

PRs مرحّب بيها على: snapshots جديدة من البورصة، فلترة مالية موثّقة بالمصدر، معالجة لحالات حافّة.

---

**English TL;DR**: `wazn-screen` is the public, auditable Sharia-screening layer for the Wazn project. It bundles a point-in-time EGX_SHARIAH universe, AAOIFI financial ratios (Standard #21), and purification math; ships as a Python library, HTTP API, and MCP server. Mirrors the logic in the private `wazn-engine` so anyone can audit the rules independently.
