import {withCurrency} from '@/lib/display-currency';
import { list, num, obj, strings, text, words, type Row } from '@/lib/guided-flow';

const labels: Record<string, string> = {
  purchased_equipment: 'Individual equipment prices · purchase-only factor basis',
  unit_capital: 'Equipment systems priced together',
  installed_equipment: 'Equipment priced with installation',
  module_estimate: 'Equipment module estimates',
  unspecified: 'Equipment with unspecified price scope',
};
const format = (value: unknown) => {
  const amount = num(value);
  return amount === null ? 'Not available' : new Intl.NumberFormat('en-GB', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(amount);
};

/** Display Python's scope subtotals; never infer or calculate installation. */
export function EquipmentCostBreakdown({ summary, installation }: { summary: unknown; installation?: unknown }) {
  const amounts = list(obj(summary).amounts).filter((row) => list(row.components).length > 0);
  if (!amounts.length) return null;
  const packages = amounts.some((row) => list(row.components).some((part) => part.cost_scope !== 'purchased_equipment'));
  return (
    <details className="gf-card-block" aria-label="Equipment cost calculation details">
      <summary>How equipment cost is counted</summary>
      <p>All listed equipment is included in one equipment cost. The breakdown below explains which prices CAPEX uses when applying additional factors.</p>
      {amounts.map((basis: Row, index) => (
        <div key={index}>
          <p className="gf-muted">{text(basis.currency)} {text(basis.period)} · priced items only</p>
          <ul className="gf-lines">
            {list(basis.components).map((part) => (
              <li key={text(part.cost_scope)} className="gf-line">
                <div className="gf-line-main">
                  <div>
                    <strong>{labels[text(part.cost_scope)] || words(part.cost_scope)}</strong>
                    {strings(part.equipment_tags).length > 0 && <small>{strings(part.equipment_tags).join(', ')}</small>}
                  </div>
                  <div className="gf-line-value"><strong>{withCurrency(format(part.amount),basis.currency)}</strong><small>{text(basis.currency)}</small></div>
                </div>
              </li>
            ))}
            <li className="gf-line"><div className="gf-line-main"><strong>Equipment cost</strong><div className="gf-line-value"><strong>{withCurrency(format(basis.amount),basis.currency)}</strong><small>{text(basis.currency)}</small></div></div></li>
          </ul>
        </div>
      ))}
      {packages && <p className="gf-note">Systems priced together are equipment too. Their source prices are not split into purchase and installation. They are included once in equipment cost; CAPEX does not add another installation factor to these prices.</p>}
      <p className="gf-muted">For purchase-only equipment, CAPEX applies the chosen method’s installation and project allowances. This equipment estimate is not total project CAPEX.</p>
      {obj(installation).status === "embedded" && <p className="gf-note"><strong>Installation treatment: </strong>This CAPEX method includes installation within its direct-cost allowances; it is not a separately priced equipment charge.</p>}
    </details>
  );
}
